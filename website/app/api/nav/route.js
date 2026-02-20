/**
 * AMFI Real-Time NAV API Route
 * Fetches latest NAV data from AMFI India and returns parsed JSON.
 * 
 * GET /api/nav
 *   Returns: { schemes: { [schemeName]: { code, nav, date, isin } }, lastUpdated }
 * 
 * GET /api/nav?search=axis+large+cap
 *   Returns: filtered results matching the search query
 */

// Cache the parsed data in memory (refreshes every 30 min)
let cachedData = null;
let cacheTime = 0;
const CACHE_DURATION = 30 * 60 * 1000; // 30 minutes

async function fetchAMFIData() {
    const now = Date.now();
    if (cachedData && now - cacheTime < CACHE_DURATION) {
        return cachedData;
    }

    const res = await fetch("https://www.amfiindia.com/spages/NAVAll.txt", {
        cache: "no-store", // Skip Next.js cache (response is >2MB); we use our own in-memory cache
    });

    if (!res.ok) {
        throw new Error(`AMFI API returned ${res.status}`);
    }

    const text = await res.text();
    const lines = text.split("\n");

    const schemes = {};
    let currentAMC = "";

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        // Header line
        if (trimmed.startsWith("Scheme Code;")) continue;

        // Category header (e.g., "Open Ended Schemes(Debt Scheme...)")
        if (trimmed.startsWith("Open Ended") || trimmed.startsWith("Close Ended") || trimmed.startsWith("Interval Fund")) continue;

        // AMC name line (no semicolons)
        if (!trimmed.includes(";")) {
            currentAMC = trimmed;
            continue;
        }

        // Data line: Code;ISIN1;ISIN2;Name;NAV;Date
        const parts = trimmed.split(";");
        if (parts.length >= 6) {
            const code = parts[0].trim();
            const isin = parts[1].trim();
            const name = parts[3].trim();
            const nav = parseFloat(parts[4].trim());
            const dateStr = parts[5].trim();

            if (name && !isNaN(nav)) {
                // Create a normalized key for matching
                const normalizedName = name.toLowerCase()
                    .replace(/\s+/g, " ")
                    .trim();

                schemes[normalizedName] = {
                    code,
                    isin: isin || null,
                    name,       // Original name with casing
                    nav,
                    date: dateStr,
                    amc: currentAMC,
                };
            }
        }
    }

    cachedData = { schemes, count: Object.keys(schemes).length, lastUpdated: new Date().toISOString() };
    cacheTime = now;
    return cachedData;
}

export async function GET(request) {
    try {
        const data = await fetchAMFIData();
        const { searchParams } = new URL(request.url);
        const search = searchParams.get("search");

        if (search) {
            const q = search.toLowerCase();
            const filtered = {};
            for (const [key, val] of Object.entries(data.schemes)) {
                if (key.includes(q) || val.amc?.toLowerCase().includes(q)) {
                    filtered[key] = val;
                }
            }
            return Response.json({
                schemes: filtered,
                count: Object.keys(filtered).length,
                lastUpdated: data.lastUpdated,
            });
        }

        return Response.json(data);
    } catch (error) {
        return Response.json(
            { error: "Failed to fetch AMFI data", details: error.message },
            { status: 500 }
        );
    }
}
