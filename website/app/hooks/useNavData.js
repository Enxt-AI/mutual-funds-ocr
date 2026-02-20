"use client";

import { useState, useEffect } from "react";

/**
 * Hook to fetch real-time NAV from AMFI via our API route.
 * Matches AMFI scheme names to our fund names using fuzzy matching.
 * 
 * @param {Array} funds - Array of fund objects from funds.json
 * @returns {{ navMap: Object, loading: boolean, lastUpdated: string }}
 *   navMap: { [slug]: { nav, date, schemeName } }
 */
export function useNavData(funds) {
    const [navMap, setNavMap] = useState({});
    const [loading, setLoading] = useState(true);
    const [lastUpdated, setLastUpdated] = useState(null);

    useEffect(() => {
        if (!funds || funds.length === 0) return;

        async function fetchNav() {
            try {
                // Extract unique AMC-like prefixes from fund names to keep responses small
                // e.g., "360 ONE FOCUSED FUND" → search for "360 one"
                const amcPrefixes = new Set();
                for (const f of funds) {
                    if (f.fund_name) {
                        // Use first 2 words as AMC identifier (covers "360 ONE", "Axis", "SBI", etc.)
                        const prefix = f.fund_name.split(/\s+/).slice(0, 2).join(" ").toLowerCase();
                        amcPrefixes.add(prefix);
                    }
                }

                // Fetch NAV data for each AMC in parallel
                const allSchemes = {};
                let latestUpdate = null;

                const fetches = [...amcPrefixes].map(async (prefix) => {
                    const res = await fetch(`/api/nav?search=${encodeURIComponent(prefix)}`);
                    if (!res.ok) return;
                    const data = await res.json();
                    Object.assign(allSchemes, data.schemes);
                    if (data.lastUpdated) latestUpdate = data.lastUpdated;
                });

                await Promise.all(fetches);
                const data = { schemes: allSchemes, lastUpdated: latestUpdate };

                const map = {};

                for (const fund of funds) {
                    if (!fund.fund_name || !fund.slug) continue;

                    // Normalize fund name for matching
                    const fundNameNorm = fund.fund_name
                        .toLowerCase()
                        .replace(/\s+/g, " ")
                        .trim();

                    // Strategy 1: Exact match
                    if (data.schemes[fundNameNorm]) {
                        const s = data.schemes[fundNameNorm];
                        map[fund.slug] = { nav: s.nav, date: s.date, schemeName: s.name, code: s.code };
                        continue;
                    }

                    // Strategy 2: Find best fuzzy match
                    // Extract key parts of fund name for matching
                    let bestMatch = null;
                    let bestScore = 0;

                    for (const [amfiKey, amfiVal] of Object.entries(data.schemes)) {
                        const score = similarityScore(fundNameNorm, amfiKey);
                        if (score > bestScore && score > 0.6) {
                            bestScore = score;
                            bestMatch = amfiVal;
                        }
                    }

                    if (bestMatch) {
                        map[fund.slug] = {
                            nav: bestMatch.nav,
                            date: bestMatch.date,
                            schemeName: bestMatch.name,
                            code: bestMatch.code,
                            matchScore: bestScore,
                        };
                    }
                }

                setNavMap(map);
                setLastUpdated(data.lastUpdated);
            } catch (err) {
                console.error("Failed to fetch AMFI NAV:", err);
            } finally {
                setLoading(false);
            }
        }

        fetchNav();
    }, [funds]);

    return { navMap, loading, lastUpdated };
}

/**
 * Simple similarity score between two strings.
 * Uses token overlap (Jaccard-like).
 */
function similarityScore(a, b) {
    const tokensA = new Set(a.split(/[\s\-\(\)]+/).filter(t => t.length > 1));
    const tokensB = new Set(b.split(/[\s\-\(\)]+/).filter(t => t.length > 1));

    // Intersection
    let overlap = 0;
    for (const t of tokensA) {
        if (tokensB.has(t)) overlap++;
    }

    // Jaccard similarity
    const union = new Set([...tokensA, ...tokensB]).size;
    if (union === 0) return 0;

    return overlap / union;
}
