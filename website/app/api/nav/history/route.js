/**
 * Historical NAV API Route
 * Fetches historical NAV data from mfapi.in for a given AMFI scheme code or fund name search.
 * 
 * GET /api/nav/history?code={scheme_code}
 * GET /api/nav/history?search={fund_name}  (searches mfapi.in, picks best "Direct Plan" match)
 *   Returns: { data: [{ date, nav }], meta: { scheme_code, fund_house, scheme_name } }
 */
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// In-memory cache: key -> { data, timestamp }
const cache = new Map();
const CACHE_TTL = 30 * 60 * 1000; // 30 minutes

function getCached(key) {
    const cached = cache.get(key);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) return cached.result;
    return null;
}

function setCache(key, result) {
    cache.set(key, { result, timestamp: Date.now() });
    if (cache.size > 200) {
        const oldest = cache.keys().next().value;
        cache.delete(oldest);
    }
}

async function fetchByCode(code) {
    const res = await fetch(`https://api.mfapi.in/mf/${code}`, {
        cache: "no-store",
        signal: AbortSignal.timeout(15000),
    });
    if (!res.ok) return null;
    return res.json();
}

async function searchScheme(fundName) {
    // Search mfapi.in for the fund name
    const res = await fetch(`https://api.mfapi.in/mf/search?q=${encodeURIComponent(fundName)}`, {
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
    });
    if (!res.ok) return null;
    const results = await res.json();
    if (!results || !results.length) return null;

    // Prefer "Direct Plan" matches
    const nameNorm = fundName.toLowerCase();
    const directMatches = results.filter(r =>
        r.schemeName && r.schemeName.toLowerCase().includes("direct")
    );

    // Score each match by how well it matches the fund name
    function score(schemeName) {
        const sn = schemeName.toLowerCase();
        const fundTokens = nameNorm.split(/[\s\-()]+/).filter(t => t.length > 1);
        let matched = 0;
        for (const token of fundTokens) {
            if (sn.includes(token)) matched++;
        }
        return fundTokens.length > 0 ? matched / fundTokens.length : 0;
    }

    const candidates = directMatches.length > 0 ? directMatches : results;
    let best = null;
    let bestScore = 0;
    for (const c of candidates) {
        const s = score(c.schemeName || "");
        if (s > bestScore) {
            bestScore = s;
            best = c;
        }
    }

    if (best && bestScore > 0.3 && best.schemeCode) {
        return best.schemeCode;
    }
    return null;
}

function parseNavData(json, code) {
    const points = (json.data || [])
        .map((d) => {
            const parts = d.date.split("-");
            const isoDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
            return { date: isoDate, nav: parseFloat(d.nav) };
        })
        .filter((d) => !isNaN(d.nav))
        .reverse();

    return {
        data: points,
        meta: json.meta || { scheme_code: code },
        count: points.length,
    };
}

export async function GET(request) {
    const { searchParams } = new URL(request.url);
    let code = searchParams.get("code");
    const search = searchParams.get("search");

    if (!code && !search) {
        return NextResponse.json(
            { error: "Missing 'code' or 'search' query parameter" },
            { status: 400 }
        );
    }

    try {
        // If no code, search by fund name to find the code
        if (!code && search) {
            const cacheKey = `search:${search.toLowerCase()}`;
            const cachedResult = getCached(cacheKey);
            if (cachedResult) return NextResponse.json(cachedResult);

            code = await searchScheme(search);
            if (!code) {
                return NextResponse.json({ data: [], meta: {}, count: 0, searchFailed: true });
            }
        }

        // Check cache for this code
        const cachedResult = getCached(code);
        if (cachedResult) return NextResponse.json(cachedResult);

        // Fetch historical NAV
        const json = await fetchByCode(code);
        if (!json) {
            return NextResponse.json(
                { error: `mfapi.in returned error for code ${code}` },
                { status: 502 }
            );
        }

        const result = parseNavData(json, code);
        setCache(code, result);
        if (search) setCache(`search:${search.toLowerCase()}`, result);

        return NextResponse.json(result);
    } catch (err) {
        return NextResponse.json(
            { error: "Failed to fetch historical NAV", details: err.message },
            { status: 500 }
        );
    }
}
