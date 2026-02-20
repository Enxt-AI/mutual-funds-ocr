import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { spawn } from "child_process";
import { putJsonFile, getJsonFile } from "../../../lib/s3Utils";

export const dynamic = "force-dynamic";

// Paths relative to admin/ — go up one level to project root
const PROJECT_ROOT = path.join(process.cwd(), "..");
const FACTSHEETS_DIR = path.join(PROJECT_ROOT, "factsheets");
const EXTRACTED_DIR = path.join(PROJECT_ROOT, "website", "data");
const EXTRACTOR_SCRIPT = path.join(PROJECT_ROOT, "gemini_extractor.py");

// Status is tracked in S3
const S3_STATUS_PREFIX = "status/";

async function writeStatus(slug, status) {
    try {
        await putJsonFile(`${S3_STATUS_PREFIX}${slug}.json`, status);
    } catch (e) {
        console.error(`[Extract] Failed to write status to S3: ${e.message}`);
    }
}

async function readStatus(slug) {
    try {
        return await getJsonFile(`${S3_STATUS_PREFIX}${slug}.json`);
    } catch {
        return null;
    }
}

/**
 * POST /api/extract
 * Uploads PDF, saves to factsheets/{amc}/, starts extraction in background.
 * After extraction, uploads result JSON to S3.
 */
export async function POST(request) {
    try {
        const formData = await request.formData();
        const file = formData.get("file");
        const amcSlug = formData.get("amc");

        if (!file || !amcSlug) {
            return NextResponse.json(
                { error: "Missing 'file' (PDF) or 'amc' (slug) field" },
                { status: 400 }
            );
        }

        if (!file.name.endsWith(".pdf")) {
            return NextResponse.json(
                { error: "Only PDF files are accepted" },
                { status: 400 }
            );
        }

        const safeSlug = amcSlug
            .toLowerCase()
            .replace(/[^a-z0-9\s-]/g, "")
            .replace(/\s+/g, "-")
            .replace(/-+/g, "-")
            .replace(/^-|-$/g, "")
            .slice(0, 60);

        if (!safeSlug) {
            return NextResponse.json({ error: "Invalid AMC name" }, { status: 400 });
        }

        const amcDir = path.join(FACTSHEETS_DIR, safeSlug);
        if (!fs.existsSync(amcDir)) {
            fs.mkdirSync(amcDir, { recursive: true });
        }

        // Remove old PDFs (skip if locked)
        const existingPdfs = fs.readdirSync(amcDir).filter(f => f.endsWith(".pdf"));
        for (const oldPdf of existingPdfs) {
            try {
                fs.unlinkSync(path.join(amcDir, oldPdf));
            } catch (err) {
                console.warn(`[Extract] Could not remove old PDF ${oldPdf}: ${err.code || err.message}`);
            }
        }

        // Save uploaded PDF locally (needed for gemini_extractor.py)
        const buffer = Buffer.from(await file.arrayBuffer());
        const pdfPath = path.join(amcDir, file.name);
        fs.writeFileSync(pdfPath, buffer);

        const sizeMB = (buffer.length / 1024 / 1024).toFixed(1);
        console.log(`[Extract] Saved PDF: ${pdfPath} (${sizeMB}MB)`);

        await writeStatus(safeSlug, {
            status: "extracting",
            amc: safeSlug,
            file: file.name,
            sizeMB,
            startedAt: new Date().toISOString(),
            logs: [],
        });

        // Spawn extraction in background
        const logs = [];
        const proc = spawn("python", [EXTRACTOR_SCRIPT, "--amc", safeSlug], {
            cwd: PROJECT_ROOT,
            env: { ...process.env, PYTHONIOENCODING: "utf-8" },
            stdio: ["ignore", "pipe", "pipe"],
        });

        proc.stdout.on("data", (data) => {
            const line = data.toString().trim();
            if (line) {
                logs.push(line);
                console.log(`[Extract] ${line}`);
                if (logs.length % 5 === 0) {
                    writeStatus(safeSlug, {
                        status: "extracting",
                        amc: safeSlug,
                        file: file.name,
                        startedAt: new Date().toISOString(),
                        logs: logs.slice(-50),
                    });
                }
            }
        });

        proc.stderr.on("data", (data) => {
            const line = data.toString().trim();
            if (line) {
                logs.push(`[stderr] ${line}`);
                console.error(`[Extract ERR] ${line}`);
            }
        });

        proc.on("close", async (code) => {
            const outputFile = path.join(EXTRACTED_DIR, `${safeSlug}.json`);
            const success = code === 0 && fs.existsSync(outputFile);

            let schemeCount = 0;
            if (success) {
                try {
                    const data = JSON.parse(fs.readFileSync(outputFile, "utf-8"));
                    schemeCount = (data.schemes || []).length;

                    // ✅ Upload extracted JSON to S3
                    console.log(`[Extract] Uploading ${safeSlug}.json to S3...`);
                    await putJsonFile(`funds/${safeSlug}.json`, data);
                    console.log(`[Extract] ✅ Uploaded to S3: funds/${safeSlug}.json`);
                } catch (uploadErr) {
                    console.error(`[Extract] S3 upload error: ${uploadErr.message}`);
                    logs.push(`[S3] Upload error: ${uploadErr.message}`);
                }
            }

            await writeStatus(safeSlug, {
                status: success ? "done" : "failed",
                amc: safeSlug,
                file: file.name,
                schemes: schemeCount,
                exitCode: code,
                completedAt: new Date().toISOString(),
                logs: logs.slice(-50),
            });

            console.log(`[Extract] ${safeSlug}: ${success ? "SUCCESS" : "FAILED"} (exit ${code}, ${schemeCount} schemes)`);
        });

        proc.on("error", async (err) => {
            await writeStatus(safeSlug, {
                status: "failed",
                amc: safeSlug,
                error: err.message,
                completedAt: new Date().toISOString(),
                logs: logs.slice(-50),
            });
        });

        return NextResponse.json({
            started: true,
            amc: safeSlug,
            message: "Extraction started in background. Poll GET /api/extract?amc=" + safeSlug + " for status.",
        });
    } catch (e) {
        console.error("[Extract] Error:", e);
        return NextResponse.json(
            { error: e.message || "Upload failed" },
            { status: 500 }
        );
    }
}

/**
 * GET /api/extract?amc={slug}
 * Returns extraction status for a given AMC (from S3).
 */
export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const amc = searchParams.get("amc");

    if (!amc) {
        return NextResponse.json({ error: "Missing 'amc' query param" }, { status: 400 });
    }

    const status = await readStatus(amc);
    if (!status) {
        return NextResponse.json({ status: "none", amc });
    }

    return NextResponse.json(status);
}
