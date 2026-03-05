import { NextResponse } from "next/server";
import { listJsonFiles, getJsonFile } from "../../../../lib/s3Utils";
import { validateApiKey, isFundAccessible, apiErrorResponse } from "../../../../lib/apiKeyAuth";
import { logApiRequest } from "../../../../lib/apiAnalytics";

export const dynamic = "force-dynamic";

// ─── In-memory cache (60s TTL) ───
let _cache = null;
let _cacheTime = 0;
const CACHE_TTL = 60 * 1000;

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

function normalizePeriod(period) {
    if (!period) return null;
    const p = period.toString().trim().toUpperCase();
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
        if (planType === "direct" || planType === "") {
            if (r.fund_return != null) entry.fund_return = r.fund_return;
            if (r.benchmark_return != null) entry.benchmark_return = r.benchmark_return;
        } else if (planType === "regular") {
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

function amcNameFromSlug(slug) {
    return slug.replace(/-/g, " ").replace(/\b(mf|amc)\b/gi, "").replace(/\b\w/g, c => c.toUpperCase()).trim();
}

async function buildFundsList() {
    if (_cache && Date.now() - _cacheTime < CACHE_TTL) {
        return _cache;
    }

    const s3Files = await listJsonFiles("funds/");
    if (s3Files.length === 0) return [];

    const fetchPromises = s3Files.map(f => getJsonFile(f.key).catch(() => null));
    const allData = await Promise.all(fetchPromises);

    const amcDataList = [];
    for (let i = 0; i < s3Files.length; i++) {
        if (allData[i]) {
            amcDataList.push({
                slug: s3Files[i].key.replace("funds/", "").replace(".json", ""),
                data: allData[i],
            });
        }
    }

    const allFunds = [];

    for (const { slug: amcSlug, data } of amcDataList) {
        const amcName = data.amc_info?.amc_name || amcNameFromSlug(amcSlug);
        const schemes = data.schemes || [];

        for (const scheme of schemes) {
            const displayName = cleanFundName(scheme.fund_name || "");
            const slug = slugify(displayName) || slugify(scheme.fund_name || "");
            if (!slug) continue;

            const mergedReturns = mergeReturns(scheme.returns);

            allFunds.push({
                ...scheme,
                fund_name: displayName || scheme.fund_name,
                slug,
                amc: amcName,
                amc_slug: amcSlug,
                returns: mergedReturns,
                risk_level: typeof scheme.risk_level === "object" && scheme.risk_level !== null
                    ? (scheme.risk_level.scheme_risk || scheme.risk_level.benchmark_risk || null)
                    : scheme.risk_level,
            });
        }
    }

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

    _cache = allFunds;
    _cacheTime = Date.now();
    return allFunds;
}

function fundSummary(fund) {
    return {
        fund_name: fund.fund_name,
        slug: fund.slug,
        amc: fund.amc,
        amc_slug: fund.amc_slug,
        category: fund.category || null,
        fund_type: fund.fund_type || null,
        scheme_type: fund.scheme_type || null,
        plan_type: fund.plan_type || null,
        option: fund.option || null,
        nav: fund.nav || null,
        nav_date: fund.nav_date || null,
        aum_crores: fund.aum_crores || null,
        expense_ratio: fund.expense_ratio || null,
        benchmark: fund.benchmark || null,
        risk_level: fund.risk_level || null,
        inception_date: fund.inception_date || null,
        returns: fund.returns || [],
    };
}

/**
 * GET /api/v1/funds?api_key=<key>[&amc=<slug>][&category=<cat>][&search=<term>]
 */
export async function GET(request) {
    const startTime = Date.now();

    const auth = await validateApiKey(request);
    if (!auth.valid) {
        return apiErrorResponse(auth.error);
    }

    try {
        const allFunds = await buildFundsList();
        const { searchParams } = new URL(request.url);

        let accessible = allFunds.filter(f => isFundAccessible(auth.keyData, f));

        const amcFilter = searchParams.get("amc");
        if (amcFilter) {
            accessible = accessible.filter(f =>
                f.amc_slug === amcFilter || f.amc.toLowerCase().includes(amcFilter.toLowerCase())
            );
        }

        const categoryFilter = searchParams.get("category");
        if (categoryFilter) {
            accessible = accessible.filter(f =>
                f.category && f.category.toLowerCase().includes(categoryFilter.toLowerCase())
            );
        }

        const search = searchParams.get("search");
        if (search) {
            const term = search.toLowerCase();
            accessible = accessible.filter(f =>
                f.fund_name.toLowerCase().includes(term) ||
                f.amc.toLowerCase().includes(term) ||
                (f.category && f.category.toLowerCase().includes(term))
            );
        }

        const responseBody = {
            success: true,
            data: accessible.map(fundSummary),
            meta: {
                total: accessible.length,
                api_key_name: auth.keyData.name,
            },
        };

        const jsonStr = JSON.stringify(responseBody);

        // Log analytics (fire-and-forget)
        logApiRequest({
            keyId: auth.keyData.id,
            request,
            status: 200,
            responseSize: jsonStr.length,
            startTime,
        });

        return new NextResponse(jsonStr, {
            status: 200,
            headers: { "Content-Type": "application/json" },
        });
    } catch (e) {
        console.error("[Public API] Funds list error:", e);
        logApiRequest({
            keyId: auth.keyData?.id || "unknown",
            request,
            status: 500,
            responseSize: 0,
            startTime,
        });
        return NextResponse.json(
            {
                success: false,
                error: { code: "INTERNAL_ERROR", message: "Failed to fetch funds." },
            },
            { status: 500 }
        );
    }
}
