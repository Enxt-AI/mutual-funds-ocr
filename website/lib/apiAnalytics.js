/**
 * API Analytics — logs every API request to S3 for dashboard reporting.
 * Storage: api-logs/{key_id}/{YYYY-MM-DD}.json
 * Fire-and-forget — never blocks the API response.
 */

import { getJsonFile, putJsonFile } from "./s3Utils";

/**
 * Log an API request (fire-and-forget).
 *
 * @param {object} opts
 * @param {string} opts.keyId      - API key ID
 * @param {Request} opts.request   - The incoming request
 * @param {number} opts.status     - HTTP response status
 * @param {number} opts.responseSize - Response body size in bytes
 * @param {number} opts.startTime  - Performance.now() or Date.now() when request started
 */
export function logApiRequest({ keyId, request, status, responseSize, startTime }) {
    // Fire-and-forget — don't await this
    _writeLog({ keyId, request, status, responseSize, startTime }).catch(() => { });
}

async function _writeLog({ keyId, request, status, responseSize, startTime }) {
    const now = new Date();
    const dateKey = now.toISOString().slice(0, 10); // YYYY-MM-DD
    const s3Key = `api-logs/${keyId}/${dateKey}.json`;

    // Extract IP address
    const forwarded = request.headers.get("x-forwarded-for");
    const realIp = request.headers.get("x-real-ip");
    let ip = forwarded ? forwarded.split(",")[0].trim() : (realIp || "unknown");
    // Normalize IPv6 loopback to readable IPv4
    if (ip === "::1" || ip === "::ffff:127.0.0.1") ip = "127.0.0.1";
    if (ip.startsWith("::ffff:")) ip = ip.slice(7);

    // Extract URL path (strip origin)
    const url = new URL(request.url);
    const path = url.pathname + url.search;

    const entry = {
        timestamp: now.toISOString(),
        ip,
        method: request.method,
        url: path,
        status,
        response_size: responseSize || 0,
        latency_ms: Math.round(Date.now() - startTime),
    };

    // Read existing log file or create new
    let logData;
    try {
        logData = await getJsonFile(s3Key);
    } catch {
        logData = null;
    }

    if (!logData || !Array.isArray(logData.entries)) {
        logData = { key_id: keyId, date: dateKey, entries: [] };
    }

    logData.entries.push(entry);
    await putJsonFile(s3Key, logData);
}
