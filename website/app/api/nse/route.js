import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { spawn } from "child_process";

export const dynamic = "force-dynamic";

const PROJECT_ROOT = path.join(process.cwd(), "..");
const NSE_DATA_DIR = path.join(PROJECT_ROOT, "nse_data");
const NSE_SCRIPT = path.join(PROJECT_ROOT, "process_nse_data.py");

/**
 * POST /api/nse
 * Accepts optional CSV file uploads via multipart form data.
 * Saves CSVs to nse_data/, then runs process_nse_data.py.
 */
export async function POST(request) {
    try {
        // Ensure nse_data directory exists
        if (!fs.existsSync(NSE_DATA_DIR)) {
            fs.mkdirSync(NSE_DATA_DIR, { recursive: true });
        }

        // Check if there are uploaded files
        const contentType = request.headers.get("content-type") || "";
        const savedFiles = [];

        if (contentType.includes("multipart/form-data")) {
            const formData = await request.formData();
            const files = formData.getAll("files");

            for (const file of files) {
                if (!file || !file.name) continue;

                if (!file.name.endsWith(".csv")) {
                    continue; // Skip non-CSV files
                }

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

        return NextResponse.json({
            success: result.code === 0,
            uploadedFiles: savedFiles,
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
