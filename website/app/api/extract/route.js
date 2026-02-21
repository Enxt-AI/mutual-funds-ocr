import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { spawn } from "child_process";

export const dynamic = "force-dynamic";

// Paths — env vars for Docker, fallback for local dev
const PROJECT_ROOT = process.env.PROJECT_ROOT || path.join(process.cwd(), "..");
const FACTSHEETS_DIR = process.env.FACTSHEETS_PATH || path.join(PROJECT_ROOT, "factsheets");
const EXTRACTED_DIR = process.env.OUTPUT_PATH || path.join(PROJECT_ROOT, "extracted_data");
const EXTRACTOR_SCRIPT = process.env.EXTRACTOR_SCRIPT || path.join(PROJECT_ROOT, "gemini_extractor.py");
const STATUS_DIR = path.join(EXTRACTED_DIR, ".status");

function getStatusFile(slug) {
    return path.join(STATUS_DIR, `${slug}.json`);
}

function writeStatus(slug, status) {
    if (!fs.existsSync(STATUS_DIR)) {
        fs.mkdirSync(STATUS_DIR, { recursive: true });
    }
    fs.writeFileSync(getStatusFile(slug), JSON.stringify(status, null, 2));
}

function readStatus(slug) {
    const f = getStatusFile(slug);
    if (!fs.existsSync(f)) return null;
    try { return JSON.parse(fs.readFileSync(f, "utf-8")); } catch { return null; }
}

/**
 * POST /api/extract
 * Uploads PDF, saves to factsheets/{amc}/, starts extraction in background.
 * Returns immediately with { started: true }.
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

        // Sanitize AMC slug
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

        // Note: no "already in progress" guard — users can re-upload freely.
        // The Python extractor uses per-page checkpoints to resume from where it left off.

        // Create AMC folder
        const amcDir = path.join(FACTSHEETS_DIR, safeSlug);
        if (!fs.existsSync(amcDir)) {
            fs.mkdirSync(amcDir, { recursive: true });
        }

        // Remove old PDFs
        const existingPdfs = fs.readdirSync(amcDir).filter(f => f.endsWith(".pdf"));
        for (const oldPdf of existingPdfs) {
            fs.unlinkSync(path.join(amcDir, oldPdf));
        }

        // Save uploaded PDF
        const buffer = Buffer.from(await file.arrayBuffer());
        const pdfPath = path.join(amcDir, file.name);
        fs.writeFileSync(pdfPath, buffer);

        const sizeMB = (buffer.length / 1024 / 1024).toFixed(1);
        console.log(`[Extract] Saved PDF: ${pdfPath} (${sizeMB}MB)`);

        // Write initial status
        writeStatus(safeSlug, {
            status: "extracting",
            amc: safeSlug,
            file: file.name,
            sizeMB,
            startedAt: new Date().toISOString(),
            logs: [],
        });

        // Spawn extraction in background (fire-and-forget)
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
                // Update status periodically (every 5 log lines)
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

        proc.on("close", (code) => {
            const outputFile = path.join(EXTRACTED_DIR, `${safeSlug}.json`);
            const success = code === 0 && fs.existsSync(outputFile);

            let schemeCount = 0;
            if (success) {
                try {
                    const data = JSON.parse(fs.readFileSync(outputFile, "utf-8"));
                    schemeCount = (data.schemes || []).length;
                } catch { }
            }

            writeStatus(safeSlug, {
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

        proc.on("error", (err) => {
            writeStatus(safeSlug, {
                status: "failed",
                amc: safeSlug,
                error: err.message,
                completedAt: new Date().toISOString(),
                logs: logs.slice(-50),
            });
        });

        // Return immediately
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
 * Returns extraction status for a given AMC.
 */
export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const amc = searchParams.get("amc");

    if (!amc) {
        return NextResponse.json({ error: "Missing 'amc' query param" }, { status: 400 });
    }

    const status = readStatus(amc);
    if (!status) {
        return NextResponse.json({ status: "none", amc });
    }

    return NextResponse.json(status);
}
