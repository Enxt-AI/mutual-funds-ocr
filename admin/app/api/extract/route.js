import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { spawn } from "child_process";

export const dynamic = "force-dynamic";

const PROJECT_ROOT = process.env.PROJECT_ROOT || path.join(process.cwd(), "..");
const FACTSHEETS_DIR = process.env.FACTSHEETS_PATH || path.join(PROJECT_ROOT, "Factsheets");
const EXTRACTOR_SCRIPT = process.env.EXTRACTOR_SCRIPT || path.join(PROJECT_ROOT, "gemini_extractor.py");
const OUTPUT_DIR = process.env.OUTPUT_PATH || path.join(PROJECT_ROOT, "website", "data");

// In-memory status tracking for active extractions
const extractionStatus = new Map();

/**
 * POST /api/extract
 * Accepts a PDF file upload and AMC slug, saves the PDF to Factsheets/<amc>/,
 * then spawns gemini_extractor.py to extract fund data.
 */
export async function POST(request) {
    try {
        const formData = await request.formData();
        const file = formData.get("file");
        const amc = formData.get("amc");

        if (!file || !amc) {
            return NextResponse.json(
                { error: "Missing file or amc parameter" },
                { status: 400 }
            );
        }

        // Create the AMC folder under Factsheets/
        const amcDir = path.join(FACTSHEETS_DIR, amc);
        if (!fs.existsSync(amcDir)) {
            fs.mkdirSync(amcDir, { recursive: true });
        }

        // Save the PDF
        const buffer = Buffer.from(await file.arrayBuffer());
        const pdfPath = path.join(amcDir, file.name || `${amc}.pdf`);
        fs.writeFileSync(pdfPath, buffer);
        console.log(`[Extract] Saved PDF: ${pdfPath} (${(buffer.length / 1024 / 1024).toFixed(1)} MB)`);

        // Initialize status
        extractionStatus.set(amc, {
            status: "extracting",
            logs: [`Saved PDF: ${file.name}`, "Starting extraction..."],
            startedAt: new Date().toISOString(),
        });

        // Spawn gemini_extractor.py in the background
        const proc = spawn("python", [EXTRACTOR_SCRIPT, "--amc", amc], {
            cwd: PROJECT_ROOT,
            env: { ...process.env, PYTHONIOENCODING: "utf-8" },
        });

        proc.stdout.on("data", (data) => {
            const lines = data.toString().trim().split("\n").filter(Boolean);
            const entry = extractionStatus.get(amc);
            if (entry) {
                entry.logs.push(...lines);
            }
            lines.forEach((line) => console.log(`[Extract:${amc}] ${line}`));
        });

        proc.stderr.on("data", (data) => {
            const lines = data.toString().trim().split("\n").filter(Boolean);
            const entry = extractionStatus.get(amc);
            if (entry) {
                entry.logs.push(...lines.map((l) => `[stderr] ${l}`));
            }
            lines.forEach((line) => console.error(`[Extract:${amc}] ${line}`));
        });

        proc.on("close", (code) => {
            const entry = extractionStatus.get(amc);
            if (entry) {
                entry.exitCode = code;
                if (code === 0) {
                    // Read the output to get scheme count
                    const outputFile = path.join(OUTPUT_DIR, `${amc}.json`);
                    let schemes = 0;
                    try {
                        if (fs.existsSync(outputFile)) {
                            const data = JSON.parse(fs.readFileSync(outputFile, "utf-8"));
                            schemes = (data.schemes || []).length;
                        }
                    } catch { }
                    entry.status = "done";
                    entry.schemes = schemes;
                    entry.logs.push(`✅ Extraction complete (${schemes} schemes)`);
                } else {
                    entry.status = "failed";
                    entry.logs.push(`❌ Process exited with code ${code}`);
                }
            }
            console.log(`[Extract:${amc}] Process exited with code ${code}`);
        });

        proc.on("error", (err) => {
            const entry = extractionStatus.get(amc);
            if (entry) {
                entry.status = "failed";
                entry.exitCode = -1;
                entry.logs.push(`Error: ${err.message}`);
            }
        });

        return NextResponse.json({
            success: true,
            message: `Extraction started for "${amc}"`,
            amc,
        });
    } catch (e) {
        console.error("[Extract] Error:", e);
        return NextResponse.json({ error: e.message }, { status: 500 });
    }
}

/**
 * GET /api/extract?amc=<slug>
 * Returns the current extraction status for the given AMC.
 */
export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const amc = searchParams.get("amc");

    if (!amc) {
        return NextResponse.json({ error: "Missing amc parameter" }, { status: 400 });
    }

    const entry = extractionStatus.get(amc);
    if (!entry) {
        // Check if there's already an output file (previously completed)
        const outputFile = path.join(OUTPUT_DIR, `${amc}.json`);
        if (fs.existsSync(outputFile)) {
            try {
                const data = JSON.parse(fs.readFileSync(outputFile, "utf-8"));
                return NextResponse.json({
                    status: "done",
                    amc,
                    schemes: (data.schemes || []).length,
                    logs: ["Previously completed extraction found"],
                });
            } catch { }
        }
        return NextResponse.json({ status: "unknown", amc, logs: [] });
    }

    return NextResponse.json({
        status: entry.status,
        amc,
        schemes: entry.schemes || 0,
        exitCode: entry.exitCode,
        logs: entry.logs.slice(-50), // Last 50 lines
    });
}
