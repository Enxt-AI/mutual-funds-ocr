import { NextResponse } from "next/server";
import { putJsonFile, getJsonFile, putFile } from "../../../lib/s3Utils";

export const dynamic = "force-dynamic";

// Max duration for serverless function (Vercel Pro: 60s, Hobby: 10s)
export const maxDuration = 60;

// Status is tracked in S3
const S3_STATUS_PREFIX = "status/";
const S3_FACTSHEETS_PREFIX = "factsheets/";

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
 * Uploads PDF to S3 under factsheets/{amc}/.
 * NOTE: On Vercel, Python extraction cannot run directly.
 *       The PDF is stored in S3 and status is set to "uploaded".
 *       Run `python gemini_extractor.py --amc <slug>` locally or via
 *       a separate compute service (ECS, Lambda, etc.) to extract.
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

        // Read the uploaded file into a buffer
        const buffer = Buffer.from(await file.arrayBuffer());
        const sizeMB = (buffer.length / 1024 / 1024).toFixed(1);

        // Upload PDF to S3 (instead of local filesystem)
        const s3PdfKey = `${S3_FACTSHEETS_PREFIX}${safeSlug}/${file.name}`;
        console.log(`[Extract] Uploading PDF to S3: ${s3PdfKey} (${sizeMB}MB)`);
        await putFile(s3PdfKey, buffer, "application/pdf");
        console.log(`[Extract] ✅ PDF uploaded to S3`);

        // Update status in S3
        await writeStatus(safeSlug, {
            status: "uploaded",
            amc: safeSlug,
            file: file.name,
            s3Key: s3PdfKey,
            sizeMB,
            uploadedAt: new Date().toISOString(),
            message: "PDF uploaded to S3. Run extraction locally or via a compute service.",
            logs: [],
        });

        return NextResponse.json({
            uploaded: true,
            amc: safeSlug,
            s3Key: s3PdfKey,
            sizeMB,
            message:
                "PDF uploaded to S3 successfully. " +
                "To extract data, run: python gemini_extractor.py --amc " + safeSlug,
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
