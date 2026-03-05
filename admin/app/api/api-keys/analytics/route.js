import { NextResponse } from "next/server";
import { S3Client, ListObjectsV2Command, GetObjectCommand } from "@aws-sdk/client-s3";

export const dynamic = "force-dynamic";

const s3 = new S3Client({
    region: process.env.AWS_REGION || "ap-south-1",
    credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    },
});
const BUCKET = process.env.S3_BUCKET_NAME;

async function getS3Json(key) {
    try {
        const resp = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
        const body = await resp.Body.transformToString();
        return JSON.parse(body);
    } catch {
        return null;
    }
}

/**
 * GET /api/api-keys/analytics?key_id=<id>&days=<7>
 * Returns logs, summary stats, and rate data for a specific API key.
 */
export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const keyId = searchParams.get("key_id");
    const days = Math.min(parseInt(searchParams.get("days")) || 7, 30);

    if (!keyId) {
        return NextResponse.json({ error: "key_id is required" }, { status: 400 });
    }

    try {
        // Generate date keys for the requested range
        const dateKeys = [];
        for (let i = 0; i < days; i++) {
            const d = new Date();
            d.setDate(d.getDate() - i);
            dateKeys.push(d.toISOString().slice(0, 10));
        }

        // Fetch log files for the key
        const prefix = `api-logs/${keyId}/`;
        const allEntries = [];

        // Fetch all date files in parallel
        const fetchPromises = dateKeys.map(async (dateKey) => {
            const data = await getS3Json(`${prefix}${dateKey}.json`);
            if (data && Array.isArray(data.entries)) {
                return data.entries;
            }
            return [];
        });

        const results = await Promise.all(fetchPromises);
        for (const entries of results) {
            allEntries.push(...entries);
        }

        // Sort by timestamp descending (most recent first)
        allEntries.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        // Build summary
        const totalRequests = allEntries.length;
        const avgLatency = totalRequests > 0
            ? Math.round(allEntries.reduce((sum, e) => sum + (e.latency_ms || 0), 0) / totalRequests)
            : 0;
        const errorCount = allEntries.filter(e => e.status >= 400).length;
        const errorRate = totalRequests > 0 ? Math.round((errorCount / totalRequests) * 100 * 10) / 10 : 0;
        const uniqueIps = new Set(allEntries.map(e => e.ip)).size;
        const totalResponseBytes = allEntries.reduce((sum, e) => sum + (e.response_size || 0), 0);

        // Top endpoints
        const endpointCounts = {};
        for (const e of allEntries) {
            // Strip query params for grouping
            const path = (e.url || "").split("?")[0];
            endpointCounts[path] = (endpointCounts[path] || 0) + 1;
        }
        const topEndpoints = Object.entries(endpointCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([path, count]) => ({ path, count }));

        // Status code breakdown
        const statusCounts = {};
        for (const e of allEntries) {
            const group = `${Math.floor(e.status / 100)}xx`;
            statusCounts[group] = (statusCounts[group] || 0) + 1;
        }

        // Build rate data — requests per hour for last 24h (for the chart)
        const now = new Date();
        const hoursBack = 24;
        const rateData = [];
        for (let h = hoursBack - 1; h >= 0; h--) {
            const hourStart = new Date(now);
            hourStart.setHours(hourStart.getHours() - h, 0, 0, 0);
            const hourEnd = new Date(hourStart);
            hourEnd.setHours(hourEnd.getHours() + 1);

            const count = allEntries.filter(e => {
                const t = new Date(e.timestamp);
                return t >= hourStart && t < hourEnd;
            }).length;

            rateData.push({
                hour: hourStart.toISOString(),
                label: hourStart.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false }),
                count,
            });
        }

        return NextResponse.json({
            success: true,
            summary: {
                total_requests: totalRequests,
                avg_latency_ms: avgLatency,
                error_rate: errorRate,
                error_count: errorCount,
                unique_ips: uniqueIps,
                total_response_bytes: totalResponseBytes,
                top_endpoints: topEndpoints,
                status_codes: statusCounts,
            },
            rate_data: rateData,
            logs: allEntries.slice(0, 500), // Cap at 500 most recent
        });
    } catch (e) {
        console.error("[Analytics] Error:", e);
        return NextResponse.json({ error: "Failed to fetch analytics" }, { status: 500 });
    }
}
