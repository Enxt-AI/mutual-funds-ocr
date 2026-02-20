import { NextResponse } from "next/server";
import { listJsonFiles, getJsonFile } from "../../../lib/s3Utils";

export const dynamic = "force-dynamic";

/**
 * GET /api/amcs
 * Returns list of extracted AMCs from S3 with scheme counts and timestamps.
 */
export async function GET() {
    try {
        const files = await listJsonFiles("funds/");
        const amcs = [];

        for (const file of files) {
            const slug = file.key.replace("funds/", "").replace(".json", "");
            if (!slug) continue;

            let schemeCount = 0;
            let amcName = "";

            try {
                const data = await getJsonFile(file.key);
                if (data) {
                    schemeCount = (data.schemes || []).length;
                    amcName = data.amc_info?.amc_name || "";
                }
            } catch { }

            amcs.push({
                slug,
                name: amcName,
                schemes: schemeCount,
                lastModified: file.lastModified?.toISOString() || new Date().toISOString(),
                sizeKB: Math.round((file.size || 0) / 1024),
            });
        }

        amcs.sort((a, b) => a.slug.localeCompare(b.slug));
        return NextResponse.json(amcs);
    } catch (e) {
        console.error("[AMCs] S3 error:", e);
        return NextResponse.json([], { status: 500 });
    }
}
