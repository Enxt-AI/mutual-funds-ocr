import { NextResponse } from "next/server";
import { getJsonFile } from "../../../../lib/s3Utils";

export const dynamic = "force-dynamic";

/**
 * Slugify a fund name (same logic as the website).
 */
function slugify(text) {
    if (!text) return "";
    return text
        .toLowerCase()
        .replace(/\(.*?\)/g, "")
        .replace(/[^a-z0-9\s-]/g, "")
        .replace(/\s+/g, "-")
        .replace(/-+/g, "-")
        .replace(/^-|-$/g, "")
        .slice(0, 80);
}

function cleanFundName(name) {
    if (!name) return "";
    let clean = name.trim();
    const suffixes = [
        " - Direct Plan - Growth", " - Direct Plan", " - Growth Option",
        " - Direct - Growth", " Direct Plan Growth", " Direct Growth",
        " - Direct", " Direct Plan", " Direct"
    ];
    for (const suffix of suffixes) {
        if (clean.toLowerCase().endsWith(suffix.toLowerCase())) {
            clean = clean.slice(0, -suffix.length).trim();
            break;
        }
    }
    return clean;
}

/**
 * GET /api/amcs/schemes?slug=<amc-slug>
 * Returns list of scheme names and slugs for a given AMC.
 */
export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const slug = searchParams.get("slug");

    if (!slug) {
        return NextResponse.json({ error: "slug parameter required" }, { status: 400 });
    }

    try {
        const data = await getJsonFile(`funds/${slug}.json`);
        if (!data) {
            return NextResponse.json({ schemes: [] });
        }

        const schemes = (data.schemes || []).map(s => {
            const displayName = cleanFundName(s.fund_name || "");
            const fundSlug = slugify(displayName) || slugify(s.fund_name || "");
            return {
                slug: fundSlug,
                name: displayName || s.fund_name || "",
                category: s.category || null,
            };
        }).filter(s => s.slug);

        return NextResponse.json({ schemes });
    } catch (e) {
        console.error("[Schemes] Error:", e);
        return NextResponse.json({ schemes: [] }, { status: 500 });
    }
}
