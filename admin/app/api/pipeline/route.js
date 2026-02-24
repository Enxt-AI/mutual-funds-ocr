import { NextResponse } from "next/server";
import path from "path";
import { spawn } from "child_process";

export const dynamic = "force-dynamic";

const PROJECT_ROOT = process.env.PROJECT_ROOT || path.join(process.cwd(), "..");
const PIPELINE_SCRIPT = path.join(PROJECT_ROOT, "pipeline.py");

// In-memory status tracking for the pipeline
let pipelineState = null;

/**
 * POST /api/pipeline
 * Start the pipeline for selected AMCs.
 * Body: { amcs: ["axis-mf", "sbi-mf", ...] } or { amcs: "all" }
 */
export async function POST(request) {
    try {
        if (pipelineState && pipelineState.status === "running") {
            return NextResponse.json(
                { error: "Pipeline is already running. Wait for it to finish or check status." },
                { status: 409 }
            );
        }

        const body = await request.json();
        const amcs = body.amcs; // array of slugs or "all"
        const scrapeOnly = body.scrapeOnly || false;
        const force = body.force || false;

        // Build command args
        const args = [PIPELINE_SCRIPT];
        if (amcs && amcs !== "all" && Array.isArray(amcs) && amcs.length > 0) {
            args.push("--amc", ...amcs);
        }
        if (scrapeOnly) {
            args.push("--scrape-only");
        }
        if (force) {
            args.push("--force");
        }

        // Initialize pipeline state
        pipelineState = {
            status: "running",
            startedAt: new Date().toISOString(),
            amcs: amcs === "all" ? "all" : amcs,
            mode: scrapeOnly ? "scrape_only" : "full",
            events: [],
            logs: [],
            currentAmc: null,
            progress: { done: 0, failed: 0, total: 0 },
        };

        // Spawn the pipeline process
        const proc = spawn("python", args, {
            cwd: PROJECT_ROOT,
            env: { ...process.env, PYTHONIOENCODING: "utf-8" },
        });

        proc.stdout.on("data", (data) => {
            const lines = data.toString("utf-8").trim().split("\n").filter(Boolean);
            for (const line of lines) {
                // Try to parse structured JSON events
                try {
                    const event = JSON.parse(line);
                    pipelineState.events.push(event);
                    console.log(`[Pipeline Event] ${event.event}`, event.amc || "", event.step || "");

                    // Update state based on event type
                    switch (event.event) {
                        case "pipeline_start":
                            pipelineState.progress.total = event.total;
                            break;
                        case "amc_start":
                            pipelineState.currentAmc = event.amc;
                            pipelineState.currentStep = "scrape";
                            pipelineState.currentIndex = event.index;
                            break;
                        case "step_start":
                            pipelineState.currentStep = event.step;
                            break;
                        case "step_done":
                            break;
                        case "amc_done":
                            if (event.status === "done" || event.status === "scraped") {
                                pipelineState.progress.done++;
                            } else {
                                pipelineState.progress.failed++;
                            }
                            break;
                        case "pipeline_done":
                            pipelineState.progress = {
                                done: event.done,
                                failed: event.failed,
                                scraped: event.scraped || 0,
                                total: event.total,
                            };
                            break;
                    }
                } catch {
                    // Not JSON — regular log line
                    pipelineState.logs.push(line);
                    console.log(`[Pipeline] ${line}`);
                }
            }
        });

        proc.stderr.on("data", (data) => {
            const lines = data.toString("utf-8").trim().split("\n").filter(Boolean);
            pipelineState.logs.push(...lines.map((l) => `[stderr] ${l}`));
            lines.forEach((l) => console.error(`[Pipeline stderr] ${l}`));
        });

        proc.on("close", (code) => {
            pipelineState.status = code === 0 ? "done" : "failed";
            pipelineState.exitCode = code;
            pipelineState.finishedAt = new Date().toISOString();
            const msg = code === 0
                ? "✅ Pipeline completed successfully"
                : `❌ Pipeline exited with code ${code}`;
            pipelineState.logs.push(msg);
            console.log(`[Pipeline] ${msg}`);
        });

        proc.on("error", (err) => {
            pipelineState.status = "failed";
            pipelineState.exitCode = -1;
            pipelineState.logs.push(`Error spawning process: ${err.message}`);
        });

        return NextResponse.json({
            success: true,
            message: "Pipeline started",
            mode: scrapeOnly ? "scrape_only" : "full",
        });
    } catch (e) {
        console.error("[Pipeline] Error:", e);
        return NextResponse.json({ error: e.message }, { status: 500 });
    }
}

/**
 * GET /api/pipeline
 * Returns the current pipeline status.
 *
 * GET /api/pipeline?list=true
 * Returns the list of available AMCs from the pipeline registry.
 */
export async function GET(request) {
    const { searchParams } = new URL(request.url);

    // List available AMCs
    if (searchParams.get("list") === "true") {
        try {
            const { execSync } = await import("child_process");
            const output = execSync(`python "${PIPELINE_SCRIPT}" --list`, {
                cwd: PROJECT_ROOT,
                encoding: "utf-8",
                timeout: 10000,
            });
            return NextResponse.json(JSON.parse(output));
        } catch (e) {
            return NextResponse.json({ error: "Failed to list AMCs: " + e.message }, { status: 500 });
        }
    }

    // Return current pipeline status
    if (!pipelineState) {
        return NextResponse.json({ status: "idle" });
    }

    return NextResponse.json({
        status: pipelineState.status,
        startedAt: pipelineState.startedAt,
        finishedAt: pipelineState.finishedAt || null,
        mode: pipelineState.mode,
        currentAmc: pipelineState.currentAmc,
        currentStep: pipelineState.currentStep,
        currentIndex: pipelineState.currentIndex || 0,
        progress: pipelineState.progress,
        events: pipelineState.events.slice(-30),   // Last 30 events
        logs: pipelineState.logs.slice(-80),       // Last 80 log lines
    });
}
