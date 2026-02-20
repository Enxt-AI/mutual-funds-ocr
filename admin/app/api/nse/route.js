import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { spawn } from "child_process";
import { putJsonFile } from "../../../lib/s3Utils";

export const dynamic = "force-dynamic";

const PROJECT_ROOT = path.join(process.cwd(), "..");
const NSE_DATA_DIR = path.join(PROJECT_ROOT, "nse_data");
const NSE_SCRIPT = path.join(PROJECT_ROOT, "process_nse_data.py");
const INDICES_OUTPUT = path.join(PROJECT_ROOT, "website", "app", "data", "indices.json");

/**
 * POST /api/nse
 * Accepts optional CSV file uploads via multipart form data.
 * Saves CSVs to nse_data/, runs process_nse_data.py, then uploads to S3.
 */
export async function POST(request) {
    try {
        if (!fs.existsSync(NSE_DATA_DIR)) {
            fs.mkdirSync(NSE_DATA_DIR, { recursive: true });
        }

        const contentType = request.headers.get("content-type") || "";
        const savedFiles = [];

        if (contentType.includes("multipart/form-data")) {
            const formData = await request.formData();
            const files = formData.getAll("files");

            for (const file of files) {
                if (!file || !file.name) continue;
                if (!file.name.endsWith(".csv")) continue;

                const buffer = Buffer.from(await file.arrayBuffer());
                const filePath = path.join(NSE_DATA_DIR, file.name);
                fs.writeFileSync(filePath, buffer);
                savedFiles.push(file.name);
            }
        }

        // Run processing script
        const result = await new Promise((resolve, reject) => {
            const logs = [];
            const proc = spawn("python", [NSE_SCRIPT], {
                cwd: PROJECT_ROOT,
                env: { ...process.env, PYTHONIOENCODING: "utf-8" },
            });

            proc.stdout.on("data", (data) => {
                const line = data.toString().trim();
                if (line) {
                    logs.push(line);
                    console.log(`[NSE] ${line}`);
                }
            });

            proc.stderr.on("data", (data) => {
                const line = data.toString().trim();
                if (line) {
                    logs.push(`[stderr] ${line}`);
                    console.error(`[NSE ERR] ${line}`);
                }
            });

            proc.on("close", (code) => resolve({ code, logs }));
            proc.on("error", (err) => reject(err));

            setTimeout(() => { proc.kill(); reject(new Error("Timed out")); }, 120000);
        });

        // Upload indices.json to S3 if processing succeeded
        let s3Uploaded = false;
        if (result.code === 0 && fs.existsSync(INDICES_OUTPUT)) {
            try {
                const indicesData = JSON.parse(fs.readFileSync(INDICES_OUTPUT, "utf-8"));
                await putJsonFile("indices/indices.json", indicesData);
                console.log("[NSE] ✅ Uploaded indices.json to S3");
                s3Uploaded = true;
                result.logs.push("[S3] ✅ Uploaded indices.json to S3");
            } catch (e) {
                console.error(`[NSE] S3 upload error: ${e.message}`);
                result.logs.push(`[S3] Upload error: ${e.message}`);
            }
        }

        return NextResponse.json({
            success: result.code === 0,
            uploadedFiles: savedFiles,
            s3Uploaded,
            exitCode: result.code,
            logs: result.logs,
        });
    } catch (e) {
        return NextResponse.json({ success: false, error: e.message }, { status: 500 });
    }
}

/**
 * GET /api/nse
 * Lists existing CSV files in nse_data/
 */
export async function GET() {
    try {
        if (!fs.existsSync(NSE_DATA_DIR)) {
            return NextResponse.json({ files: [] });
        }

        const files = fs.readdirSync(NSE_DATA_DIR)
            .filter(f => f.endsWith(".csv"))
            .map(f => {
                const stats = fs.statSync(path.join(NSE_DATA_DIR, f));
                return { name: f, sizeKB: Math.round(stats.size / 1024), lastModified: stats.mtime.toISOString() };
            });

        return NextResponse.json({ files });
    } catch (e) {
        return NextResponse.json({ files: [] }, { status: 500 });
    }
}
