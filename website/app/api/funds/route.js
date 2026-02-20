import { NextResponse } from "next/server";
import { listJsonFiles, getJsonFile } from "../../../lib/s3Utils";

export const dynamic = "force-dynamic"; // Never cache — always read fresh data

// ─── In-memory cache (60s TTL) to avoid hitting S3 on every request ───
let _cache = null;
let _cacheTime = 0;
const CACHE_TTL = 60 * 1000; // 60 seconds

/**
 * Slugify a fund name for URL routing.
 */
function slugify(text) {
    if (!text) return "";
    return text
        .toLowerCase()
        .replace(/\(.*?\)/g, "")          // Remove parenthesized text
        .replace(/[^a-z0-9\s-]/g, "")     // Remove special chars
        .replace(/\s+/g, "-")             // Spaces to hyphens
        .replace(/-+/g, "-")              // Collapse multiple hyphens
        .replace(/^-|-$/g, "")            // Trim leading/trailing hyphens
        .slice(0, 80);
}

/**
 * Normalize period strings (e.g., "Since Inception" → "SI", "1 Year" → "1Y").
 */
function normalizePeriod(period) {
    if (!period) return null;
    const p = period.toString().trim().toUpperCase();

    // Already normalized
    if (/^\d{1,2}[YM]$/.test(p) || p === "SI" || p === "YTD") return p;

    const map = {
        "1 MONTH": "1M", "3 MONTHS": "3M", "6 MONTHS": "6M",
        "1 YEAR": "1Y", "2 YEARS": "2Y", "3 YEARS": "3Y",
        "5 YEARS": "5Y", "7 YEARS": "7Y", "10 YEARS": "10Y",
        "SINCE INCEPTION": "SI", "SINCE LAUNCH": "SI",
    };

    for (const [key, val] of Object.entries(map)) {
        if (p.includes(key)) return val;
    }

    const match = p.match(/^(\d{1,2})\s*(YEAR|YR|MONTH|MO)/);
    if (match) {
        const unit = match[2].startsWith("Y") ? "Y" : "M";
        return `${match[1]}${unit}`;
    }

    return p;
}

/**
 * Merge returns from multiple plan types, preferring Direct Plan.
 */
function mergeReturns(returns) {
    if (!returns || !Array.isArray(returns)) return [];

    const byPeriod = {};
    for (const r of returns) {
        const period = normalizePeriod(r.period);
        if (!period) continue;

        const planType = (r.plan_type || "").toLowerCase().trim();

        if (!byPeriod[period]) {
            byPeriod[period] = { period, fund_return: null, benchmark_return: null };
        }
        const entry = byPeriod[period];

        // Direct plan data takes priority
        if (planType === "direct") {
            if (r.fund_return != null) entry.fund_return = r.fund_return;
            if (r.benchmark_return != null) entry.benchmark_return = r.benchmark_return;
        } else if (planType === "direct" || planType === "") {
            if (r.fund_return != null) entry.fund_return = r.fund_return;
            if (r.benchmark_return != null) entry.benchmark_return = r.benchmark_return;
        } else if (planType === "regular") {
            // Use regular only if no direct return exists yet
            if (entry.fund_return == null && r.fund_return != null) {
                entry.fund_return = r.fund_return;
            }
        }
    }

    const order = { "1M": 0, "3M": 1, "6M": 2, "1Y": 3, "2Y": 4, "3Y": 5, "5Y": 6, "7Y": 7, "10Y": 8, "SI": 9 };
    return Object.values(byPeriod)
        .filter(r => r.fund_return != null || r.benchmark_return != null)
        .sort((a, b) => (order[a.period] ?? 99) - (order[b.period] ?? 99));
}

/**
 * Clean up fund name for display (remove Direct/Growth/Plan suffixes).
 */
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
 * Check if a scheme should be included (skip explicitly Regular/IDCW plans).
 */
function shouldInclude(scheme) {
    const name = (scheme.fund_name || "").toLowerCase();
    const plan = (scheme.plan_type || "").toLowerCase();
    const option = (scheme.option || "").toLowerCase();

    const isDirect = name.includes("direct") || plan === "direct";
    const isRegular = name.includes("regular") || plan === "regular";
    const isGrowth = name.includes("growth") || option === "growth";
    const isIdcw = name.includes("idcw") || name.includes("dividend") || ["idcw", "dividend"].includes(option);

    if (isRegular && !isDirect) return false;
    if (isIdcw && !isGrowth) return false;
    return true;
}

/**
 * Normalize an AMC slug into a readable AMC name.
 */
function amcNameFromSlug(slug) {
    return slug
        .replace(/-/g, " ")
        .replace(/\b(mf|amc)\b/gi, "")
        .replace(/\b\w/g, c => c.toUpperCase())
        .trim();
}

export async function GET() {
    try {
        // Return cached data if fresh enough
        if (_cache && Date.now() - _cacheTime < CACHE_TTL) {
            return NextResponse.json(_cache);
        }

        const s3Files = await listJsonFiles("funds/");
        if (s3Files.length === 0) {
            return NextResponse.json([]);
        }

        const allFunds = [];

        // Fetch all AMC JSONs from S3 in parallel
        const fetchPromises = s3Files.map(f => getJsonFile(f.key).catch(() => null));
        const allData = await Promise.all(fetchPromises);

        for (let i = 0; i < s3Files.length; i++) {
            const data = allData[i];
            if (!data) continue;

            const amcSlug = s3Files[i].key.replace("funds/", "").replace(".json", "");
            const amcName = data.amc_info?.amc_name || amcNameFromSlug(amcSlug);
            const schemes = data.schemes || [];

            for (const scheme of schemes) {
                const displayName = cleanFundName(scheme.fund_name || "");
                const slug = slugify(displayName) || slugify(scheme.fund_name || "");
                if (!slug) continue;

                // Merge returns from separate plan_type rows
                const mergedReturns = mergeReturns(scheme.returns);

                // Pass through EVERYTHING from the extracted data, plus computed fields
                allFunds.push({
                    // Pass through all original fields
                    ...scheme,
                    // Override/add computed fields
                    fund_name: displayName || scheme.fund_name,
                    slug,
                    amc: amcName,
                    amc_slug: amcSlug,
                    returns: mergedReturns,
                    // Normalize risk_level
                    risk_level: typeof scheme.risk_level === "object" && scheme.risk_level !== null
                        ? (scheme.risk_level.scheme_risk || scheme.risk_level.benchmark_risk || null)
                        : scheme.risk_level,
                });
            }
        }

        // Make slugs unique — append plan_type/option when duplicates exist
        const slugCount = {};
        for (const fund of allFunds) {
            slugCount[fund.slug] = (slugCount[fund.slug] || 0) + 1;
        }
        for (const fund of allFunds) {
            if (slugCount[fund.slug] > 1) {
                const planType = (fund.plan_type || "").toLowerCase().replace(/\s+/g, "-");
                const option = (fund.option || "").toLowerCase().replace(/\s+/g, "-");
                const suffix = [planType, option].filter(Boolean).join("-");
                if (suffix) {
                    fund.slug = `${fund.slug}-${suffix}`;
                    fund.fund_name = `${fund.fund_name} (${[fund.plan_type, fund.option].filter(Boolean).join(" - ")})`;
                }
            }
        }

        // Cache the result
        _cache = allFunds;
        _cacheTime = Date.now();

        return NextResponse.json(allFunds);
    } catch (e) {
        console.error("Error loading funds from S3:", e);
        return NextResponse.json([], { status: 500 });
    }
}
