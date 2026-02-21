import { NextResponse } from "next/server";
import { deleteFile } from "../../../../lib/s3Utils";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

// WEBSITE_DATA_DIR env var (set in Docker), fallback to local dev path
const OUTPUT_DIR = process.env.WEBSITE_DATA_DIR || path.join(process.cwd(), "..", "website", "data");
const CHECKPOINT_DIR = path.join(OUTPUT_DIR, ".checkpoints");

/**
 * DELETE /api/amcs/delete
 * Deletes an AMC's data from both S3 and local filesystem.
 * Body: { slug: "amc-slug" }
 */
export async function DELETE(request) {
    try {
        const { slug } = await request.json();

        if (!slug || typeof slug !== "string") {
            return NextResponse.json(
                { error: "Missing or invalid slug parameter" },
                { status: 400 }
            );
        }

        // ── 1. Delete from S3 ──
        const fundKey = `funds/${slug}.json`;
        const statusKey = `status/${slug}.json`;

        console.log(`[Delete AMC] Deleting S3 objects: ${fundKey}, ${statusKey}`);

        await Promise.all([
            deleteFile(fundKey),
            deleteFile(statusKey).catch(() => {
                console.log(`[Delete AMC] No status file found for: ${statusKey}`);
            }),
        ]);

        // ── 2. Delete local files (so re-extraction doesn't skip) ──
        const localOutput = path.join(OUTPUT_DIR, `${slug}.json`);
        const localCheckpoint = path.join(CHECKPOINT_DIR, `${slug}_pages.json`);

        for (const filePath of [localOutput, localCheckpoint]) {
            try {
                if (fs.existsSync(filePath)) {
                    fs.unlinkSync(filePath);
                    console.log(`[Delete AMC] Deleted local file: ${filePath}`);
                }
            } catch (e) {
                console.warn(`[Delete AMC] Could not delete ${filePath}: ${e.message}`);
            }
        }

        console.log(`[Delete AMC] Successfully deleted: ${slug}`);

        return NextResponse.json({
            success: true,
            slug,
            message: `Deleted "${slug}" from S3 and local files`,
        });
    } catch (e) {
        console.error("[Delete AMC] Error:", e);
        return NextResponse.json({ error: e.message || "Delete failed" }, { status: 500 });
    }
}
