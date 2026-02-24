"use client";

import { useState, useMemo, useEffect } from "react";
import { useParams } from "next/navigation";
import indexData from "../../data/indices.json";
import { useNavData } from "../../hooks/useNavData";
import styles from "./page.module.css";

// Map fund benchmark names to available index data keys
const BENCHMARK_MAP = {
    "nifty 50": "nifty-50",
    "nifty50": "nifty-50",
    "nifty 500": "nifty-500",
    "nifty500": "nifty-500",
    "nifty next 50": "nifty-next-50",
    "nifty 100": "nifty-100",
    "bse 100": "nifty-100",
    "bse sensex": "sensex",
    "s&p bse sensex": "sensex",
    "sensex": "sensex",
    "nifty bank": "nifty-bank",
    "nifty it": "nifty-it",
    "nifty midcap": "nifty-midcap-150",
    "nifty midcap 150": "nifty-midcap-150",
    "nifty midcap 50": "nifty-midcap-150",
    "nifty smallcap": "nifty-midcap-150",
    "nifty financial": "nifty-financial-services",
    "nifty large midcap 250": "nifty-midcap-150",
};


function getBenchmarkKey(benchmarkName) {
    if (!benchmarkName) return "nifty-500";
    const name = (Array.isArray(benchmarkName) ? benchmarkName[0] : benchmarkName).toLowerCase();
    // Try exact partial matches
    for (const [pattern, key] of Object.entries(BENCHMARK_MAP)) {
        if (name.includes(pattern)) return key;
    }
    // Default fallback
    return "nifty-500";
}

function getBenchmarkData(benchmarkName) {
    const key = getBenchmarkKey(benchmarkName);
    const data = indexData[key];
    if (!data) return { points: [], name: "Benchmark", key };
    // Convert {date, val} -> {date, nav} for chart compatibility
    return {
        points: data.map(d => ({ date: d.date, nav: d.val })),
        name: key.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
        key
    };
}

const CHART_PERIODS = ["1M", "3M", "6M", "1Y", "3Y", "5Y", "MAX"];

function filterByPeriod(data, period) {
    if (!data.length) return data;
    const now = new Date(data[data.length - 1].date);
    let from = new Date(now);
    switch (period) {
        case "1M": from.setMonth(from.getMonth() - 1); break;
        case "3M": from.setMonth(from.getMonth() - 3); break;
        case "6M": from.setMonth(from.getMonth() - 6); break;
        case "1Y": from.setFullYear(from.getFullYear() - 1); break;
        case "3Y": from.setFullYear(from.getFullYear() - 3); break;
        case "5Y": from.setFullYear(from.getFullYear() - 5); break;
        default: return data;
    }
    return data.filter((d) => new Date(d.date) >= from);
}

// Simple SVG chart component
function NavChart({ data, benchmarkLabel }) {
    if (!data || !data.length) return <div className={styles.noData}>No NAV data available</div>;
    const w = 800, h = 300, padX = 50, padY = 30;
    const minNav = Math.min(...data.map((d) => d.nav));
    const maxNav = Math.max(...data.map((d) => d.nav));
    const range = maxNav - minNav || 1;

    const points = data.map((d, i) => {
        const x = padX + (i / (data.length - 1)) * (w - padX * 2);
        const y = padY + (1 - (d.nav - minNav) / range) * (h - padY * 2);
        return `${x},${y}`;
    });

    const polyline = points.join(" ");
    const areaPoints = `${padX},${h - padY} ${polyline} ${padX + ((data.length - 1) / (data.length - 1)) * (w - padX * 2)},${h - padY}`;

    const startNav = data[0].nav;
    const endNav = data[data.length - 1].nav;
    const isPositive = endNav >= startNav;
    const strokeColor = isPositive ? "#10b981" : "#ef4444";

    const yLabels = [];
    for (let i = 0; i <= 4; i++) {
        const val = minNav + (range * i) / 4;
        const y = padY + (1 - i / 4) * (h - padY * 2);
        yLabels.push({ val: val.toFixed(0), y });
    }

    const xLabels = [];
    const step = Math.floor(data.length / 5) || 1;
    for (let i = 0; i < data.length; i += step) {
        const x = padX + (i / (data.length - 1)) * (w - padX * 2);
        const d = new Date(data[i].date);
        xLabels.push({ label: d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" }), x });
    }

    return (
        <svg viewBox={`0 0 ${w} ${h}`} className={styles.chartSvg}>
            <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
                    <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
                </linearGradient>
            </defs>
            {yLabels.map((l, i) => (
                <g key={i}>
                    <line x1={padX} y1={l.y} x2={w - padX} y2={l.y} stroke="rgba(255,255,255,0.05)" />
                    <text x={padX - 8} y={l.y + 4} fill="#64748b" fontSize="11" textAnchor="end">{l.val}</text>
                </g>
            ))}
            {xLabels.map((l, i) => (
                <text key={i} x={l.x} y={h - 6} fill="#64748b" fontSize="11" textAnchor="middle">{l.label}</text>
            ))}
            <polygon points={areaPoints} fill="url(#areaGrad)" />
            <polyline points={polyline} fill="none" stroke={strokeColor} strokeWidth="2" strokeLinejoin="round" />
        </svg>
    );
}

// Risk-o-meter component
function Riskometer({ level }) {
    if (!level) return null;
    const levels = ["Low", "Moderately Low", "Moderate", "Moderately High", "High", "Very High"];
    const idx = levels.indexOf(level);
    const colors = ["#10b981", "#34d399", "#f59e0b", "#f97316", "#ef4444", "#dc2626"];
    if (idx === -1) return <span className="badge badge-blue">{level}</span>;
    return (
        <div className={styles.riskometer}>
            <div className={styles.riskMeter}>
                {levels.map((l, i) => (
                    <div key={i} className={`${styles.riskSegment} ${i <= idx ? styles.riskActive : ""}`}
                        style={{ background: i <= idx ? colors[i] : "var(--bg-secondary)" }}
                    />
                ))}
            </div>
            <span className={styles.riskLabel} style={{ color: colors[idx] }}>{level}</span>
        </div>
    );
}

// SIP Calculator
function SIPCalculator({ fund }) {
    const [monthly, setMonthly] = useState(5000);
    const [years, setYears] = useState(5);
    const rate = fund.returns?.find((r) => r.period === "5Y")?.fund_return ||
        fund.returns?.find((r) => r.period === "3Y")?.fund_return ||
        fund.returns?.find((r) => r.period === "SI")?.fund_return || 12;
    const months = years * 12;
    const r = rate / 100 / 12;
    const invested = monthly * months;
    const futureVal = monthly * ((Math.pow(1 + r, months) - 1) / r) * (1 + r);
    const gains = futureVal - invested;

    return (
        <div className={styles.calculator}>
            <div className={styles.calcInputs}>
                <div className={styles.calcField}>
                    <label>Monthly SIP (₹)</label>
                    <input type="range" min="500" max="100000" step="500" value={monthly} onChange={(e) => setMonthly(+e.target.value)} />
                    <span className={styles.calcValue}>₹{monthly.toLocaleString("en-IN")}</span>
                </div>
                <div className={styles.calcField}>
                    <label>Duration (Years)</label>
                    <input type="range" min="1" max="30" value={years} onChange={(e) => setYears(+e.target.value)} />
                    <span className={styles.calcValue}>{years} yr{years > 1 ? "s" : ""}</span>
                </div>
            </div>
            <div className={styles.calcResults}>
                <div className={styles.calcResultItem}>
                    <span className={styles.calcResultLabel}>Invested</span>
                    <span className={styles.calcResultVal}>₹{invested.toLocaleString("en-IN")}</span>
                </div>
                <div className={styles.calcResultItem}>
                    <span className={styles.calcResultLabel}>Est. Returns</span>
                    <span className={`${styles.calcResultVal} positive`}>₹{Math.round(gains).toLocaleString("en-IN")}</span>
                </div>
                <div className={`${styles.calcResultItem} ${styles.calcTotal}`}>
                    <span className={styles.calcResultLabel}>Total Value</span>
                    <span className={styles.calcResultVal}>₹{Math.round(futureVal).toLocaleString("en-IN")}</span>
                </div>
            </div>
            <div className={styles.calcNote}>*Based on {rate}% CAGR (historical return)</div>
        </div>
    );
}

// Allocation bar chart
function AllocationBar({ data, colors }) {
    if (!data || Object.keys(data).length === 0) return <div className={styles.noData}>No data available</div>;
    const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
    return (
        <div className={styles.allocBars}>
            {entries.map(([name, pct], i) => (
                <div key={name} className={styles.allocItem}>
                    <div className={styles.allocHeader}>
                        <span className={styles.allocName}>
                            <span className={styles.allocDot} style={{ background: colors[i % colors.length] }} />
                            {name}
                        </span>
                        <span className={styles.allocPct}>{pct}%</span>
                    </div>
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${Math.min(pct, 100)}%`, background: colors[i % colors.length] }} />
                    </div>
                </div>
            ))}
        </div>
    );
}

// Morningstar star rating component
function MorningstarRating({ rating }) {
    if (!rating || rating < 1 || rating > 5) return null;
    return (
        <div className={styles.starRating}>
            {[1, 2, 3, 4, 5].map((i) => (
                <span key={i} className={`${styles.star} ${i <= rating ? styles.starFilled : ""}`}>★</span>
            ))}
            <span className={styles.ratingLabel}>Morningstar</span>
        </div>
    );
}

// Safe value formatters
const safe = (val, suffix = "", prefix = "") => val != null ? `${prefix}${val}${suffix}` : "—";
const safeMoney = (val) => val != null ? `₹${Number(val).toLocaleString("en-IN")}` : "—";
const safeDate = (dateStr) => {
    if (!dateStr) return "—";
    try {
        return new Date(dateStr).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
    } catch { return dateStr; }
};

export default function FundDetailPage() {
    const params = useParams();
    const slug = params?.slug;

    const [allFunds, setAllFunds] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("/api/funds")
            .then((res) => res.json())
            .then((data) => { setAllFunds(data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    // Find fund by slug
    const fund = allFunds.find((f) => f.slug === slug);

    const [chartPeriod, setChartPeriod] = useState("1Y");
    const [holdingTab, setHoldingTab] = useState(() => {
        if (!fund) return "equity";
        const hasEquity = fund.equity_holdings && fund.equity_holdings.length > 0;
        const hasDebt = fund.debt_holdings && fund.debt_holdings.length > 0;
        return (!hasEquity && hasDebt) ? "debt" : "equity";
    });


    // Fetch live NAV from AMFI
    const { navMap } = useNavData(fund ? [fund] : []);
    const liveNav = navMap[fund?.slug];

    // Get real benchmark data for this fund
    const benchmark = useMemo(() => getBenchmarkData(fund?.benchmark), [fund?.benchmark]);
    const chartData = filterByPeriod(benchmark.points, chartPeriod);

    const sectorColors = ["#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#f97316", "#14b8a6", "#6366f1"];
    const capColors = ["#3b82f6", "#8b5cf6", "#f59e0b", "#10b981"];
    const assetColors = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6"];

    if (loading) {
        return (
            <div className={styles.detailPage}>
                <div className={styles.notFound}>
                    <h1>Loading fund data...</h1>
                </div>
            </div>
        );
    }

    if (!fund) {
        return (
            <div className={styles.detailPage}>
                <div className={styles.notFound}>
                    <h1>Fund Not Found</h1>
                    <p>The fund &quot;{slug}&quot; could not be found.</p>
                    <a href="/" className="badge badge-blue" style={{ padding: "10px 24px", fontSize: 16 }}>← Browse All Funds</a>
                </div>
            </div>
        );
    }

    const equityHoldings = fund.equity_holdings || [];
    const debtHoldings = fund.debt_holdings || [];
    const returns = fund.returns || [];
    const managers = fund.fund_managers || [];
    const riskMetrics = fund.risk_metrics || {};

    return (
        <div className={styles.detailPage}>
            {/* ===== HEADER ===== */}
            <section className={styles.header}>
                <div className={styles.headerTop}>
                    <div>
                        <div className={styles.breadcrumb}>
                            <a href="/">Mutual Funds</a> / <span>{fund.category || "Fund"}</span>
                        </div>
                        <h1 className={styles.fundTitle}>{fund.fund_name}</h1>
                        <div className={styles.fundMeta}>
                            <span className="badge badge-blue">{fund.plan_type || "Direct"} Plan</span>
                            {fund.category && <span className="badge badge-purple">{fund.category}</span>}
                            <Riskometer level={fund.risk_level} />
                            <MorningstarRating rating={fund.morningstar_rating} />
                        </div>
                    </div>
                </div>
                <div className={styles.headerCards}>
                    <div className={styles.navCard}>
                        <span className={styles.navLabel}>
                            Current NAV {liveNav && <span className={styles.liveBadge}>LIVE</span>}
                        </span>
                        <div className={styles.navRow}>
                            <span className={styles.navPrice}>
                                {liveNav?.nav != null ? `₹${Number(liveNav.nav).toFixed(2)}` : fund.nav != null ? `₹${Number(fund.nav).toFixed(2)}` : "—"}
                            </span>
                        </div>
                        <span className={styles.navDate}>
                            {liveNav ? `as on ${liveNav.date}` : fund.nav_date ? `as on ${new Date(fund.nav_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}` : ""}
                        </span>
                    </div>
                    <div className={styles.statCard}>
                        <span className={styles.statLabel}>AUM</span>
                        <span className={styles.statValue}>
                            {fund.aum_crores ? `₹${(fund.aum_crores / 1000).toFixed(1)}K Cr` : "—"}
                        </span>
                    </div>
                    <div className={styles.statCard}>
                        <span className={styles.statLabel}>Expense Ratio</span>
                        <span className={styles.statValue}>{safe(fund.expense_ratio, "%")}</span>
                    </div>
                    <div className={styles.statCard}>
                        <span className={styles.statLabel}>Fund Age</span>
                        <span className={styles.statValue}>
                            {fund.fund_age_years != null ? `${fund.fund_age_years}Y ${fund.fund_age_months || 0}M` : "—"}
                        </span>
                    </div>
                    <div className={styles.statCard}>
                        <span className={styles.statLabel}>Min SIP</span>
                        <span className={styles.statValue}>{safeMoney(fund.min_sip)}</span>
                    </div>
                </div>
            </section>

            {/* ===== BENCHMARK CHART ===== */}
            <section className={`card ${styles.section}`}>
                <div className={styles.sectionHeader}>
                    <h2 className="section-title">📈 {benchmark.name} Performance</h2>
                    <div className="pill-tabs">
                        {CHART_PERIODS.map((p) => (
                            <button key={p} className={`pill-tab ${chartPeriod === p ? "active" : ""}`} onClick={() => setChartPeriod(p)}>
                                {p}
                            </button>
                        ))}
                    </div>
                </div>
                <NavChart data={chartData} benchmarkLabel={benchmark.name} />
            </section>

            {/* ===== RETURNS TABLE ===== */}
            {returns.length > 0 && (
                <section className={`card ${styles.section}`}>
                    <h2 className="section-title">📊 Returns Comparison</h2>
                    <div className={styles.tableWrap}>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Period</th>
                                    <th>Fund Return</th>
                                    <th>Benchmark</th>
                                    {returns.some(r => r.additional_benchmark_return != null) && (
                                        <th>Addl. Benchmark</th>
                                    )}
                                    <th>vs Benchmark</th>
                                </tr>
                            </thead>
                            <tbody>
                                {returns.map((r) => {
                                    const diff = (r.fund_return != null && r.benchmark_return != null) ? r.fund_return - r.benchmark_return : null;
                                    return (
                                        <tr key={r.period}>
                                            <td style={{ fontWeight: 600 }}>{r.period}</td>
                                            <td className={r.fund_return >= 0 ? "positive" : "negative"} style={{ fontWeight: 700 }}>
                                                {safe(r.fund_return, "%")}
                                            </td>
                                            <td>{safe(r.benchmark_return, "%")}</td>
                                            {returns.some(ret => ret.additional_benchmark_return != null) && (
                                                <td>{safe(r.additional_benchmark_return, "%")}</td>
                                            )}
                                            <td className={diff != null ? (diff >= 0 ? "positive" : "negative") : ""} style={{ fontWeight: 600 }}>
                                                {diff != null ? `${diff >= 0 ? "+" : ""}${diff.toFixed(2)}%` : "—"}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </section>
            )}

            {/* ===== TWO-COLUMN: HOLDINGS + ALLOCATIONS ===== */}
            <div className={styles.twoCol}>
                {/* Holdings */}
                <section className={`card ${styles.section}`}>
                    <div className={styles.sectionHeader}>
                        <h2 className="section-title">💼 Portfolio Holdings</h2>
                        <div className="pill-tabs">
                            <button className={`pill-tab ${holdingTab === "equity" ? "active" : ""}`} onClick={() => setHoldingTab("equity")}>
                                Equity ({equityHoldings.length})
                            </button>
                            <button className={`pill-tab ${holdingTab === "debt" ? "active" : ""}`} onClick={() => setHoldingTab("debt")}>
                                Debt ({debtHoldings.length})
                            </button>
                        </div>
                    </div>
                    {holdingTab === "equity" ? (
                        equityHoldings.length > 0 ? (
                            <table className="data-table">
                                <thead>
                                    <tr><th>Stock</th><th>Sector</th><th>Weight</th></tr>
                                </thead>
                                <tbody>
                                    {equityHoldings.map((h, i) => (
                                        <tr key={i}>
                                            <td style={{ fontWeight: 600 }}>{h.name}</td>
                                            <td style={{ color: "var(--text-secondary)" }}>{h.sector || "—"}</td>
                                            <td>
                                                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                                    <div className="progress-bar" style={{ width: 80 }}>
                                                        <div className="progress-fill" style={{ width: `${(h.weight_pct || 0) * 10}%`, background: sectorColors[i % sectorColors.length] }} />
                                                    </div>
                                                    <span style={{ fontWeight: 700 }}>{h.weight_pct}%</span>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : <div className={styles.noData}>No equity holdings data</div>
                    ) : (
                        debtHoldings.length > 0 ? (
                            <table className="data-table">
                                <thead>
                                    <tr><th>Instrument</th><th>Type</th><th>Rating</th><th>Weight</th></tr>
                                </thead>
                                <tbody>
                                    {debtHoldings.map((h, i) => (
                                        <tr key={i}>
                                            <td style={{ fontWeight: 600 }}>{h.name}</td>
                                            <td style={{ color: "var(--text-secondary)" }}>{h.instrument_type || "—"}</td>
                                            <td>{h.rating ? <span className="badge badge-green">{h.rating}</span> : "—"}</td>
                                            <td style={{ fontWeight: 700 }}>{h.weight_pct}%</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : <div className={styles.noData}>No debt holdings data</div>
                    )}
                </section>

                {/* Allocations */}
                <div className={styles.allocColumn}>
                    <section className={`card ${styles.section}`}>
                        <h2 className="section-title">🏦 Asset Allocation</h2>
                        <AllocationBar data={fund.asset_allocation} colors={assetColors} />
                    </section>
                    {fund.instrument_composition && Object.keys(fund.instrument_composition).length > 0 && (
                        <section className={`card ${styles.section}`}>
                            <h2 className="section-title">🧩 Instrument Composition</h2>
                            <AllocationBar data={fund.instrument_composition} colors={sectorColors} />
                        </section>
                    )}
                    <section className={`card ${styles.section}`}>
                        <h2 className="section-title">🏢 Sector Allocation</h2>
                        <AllocationBar data={fund.sector_allocation} colors={sectorColors} />
                    </section>
                    <section className={`card ${styles.section}`}>
                        <h2 className="section-title">📐 Market Cap</h2>
                        <AllocationBar data={fund.market_cap_allocation} colors={capColors} />
                    </section>
                    {fund.composition_by_rating && Object.keys(fund.composition_by_rating).length > 0 && (
                        <section className={`card ${styles.section}`}>
                            <h2 className="section-title">📊 Rating Composition</h2>
                            <AllocationBar data={fund.composition_by_rating} colors={capColors} />
                        </section>
                    )}
                    {fund.maturity_profile && Object.keys(fund.maturity_profile).length > 0 && (
                        <section className={`card ${styles.section}`}>
                            <h2 className="section-title">📅 Maturity Profile</h2>
                            <AllocationBar data={fund.maturity_profile} colors={assetColors} />
                        </section>
                    )}
                </div>
            </div>

            {/* ===== FUND MANAGERS ===== */}
            {managers.length > 0 && (
                <section className={`card ${styles.section}`}>
                    <h2 className="section-title">👤 Fund Managers</h2>
                    <div className={styles.managerGrid}>
                        {managers.map((m, i) => (
                            <div key={i} className={styles.managerCard}>
                                <div className={styles.managerAvatar}>
                                    {m.name?.split(" ").filter(n => n.length > 0).map((n) => n[0]).join("").slice(0, 2)}
                                </div>
                                <div className={styles.managerInfo}>
                                    <h4 className={styles.managerName}>{m.name}</h4>
                                    {m.experience && <p className={styles.managerDetail}>Experience: {m.experience}</p>}
                                    {m.qualification && <p className={styles.managerDetail}>{m.qualification}</p>}
                                    {m.managing_since && (
                                        <p className={styles.managerDetail}>
                                            Managing since {(() => { try { return new Date(m.managing_since).toLocaleDateString("en-IN", { month: "short", year: "numeric" }); } catch { return m.managing_since; } })()}
                                        </p>
                                    )}
                                    {m.other_schemes_managed && (
                                        <div className={styles.schemeTags}>
                                            {(Array.isArray(m.other_schemes_managed)
                                                ? m.other_schemes_managed
                                                : String(m.other_schemes_managed).split(",").map(s => s.trim())
                                            ).filter(Boolean).slice(0, 5).map((s, j) => (
                                                <span key={j} className={styles.schemeTag}>{s}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* ===== RISK METRICS ===== */}
            {Object.keys(riskMetrics).length > 0 && Object.values(riskMetrics).some(v => v != null) && (
                <section className={`card ${styles.section}`}>
                    <h2 className="section-title">⚡ Risk Metrics</h2>
                    <div className={styles.riskGrid}>
                        {Object.entries(riskMetrics).map(([key, val]) => {
                            if (val == null) return null;
                            const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

                            // Handle nested objects like {fund: 0.99, benchmark: 1.0}
                            let displayVal;
                            if (typeof val === "object" && val !== null && !Array.isArray(val)) {
                                const parts = Object.entries(val)
                                    .map(([k, v]) => `${k.replace(/\b\w/g, c => c.toUpperCase())}: ${v}`)
                                    .join(" | ");
                                displayVal = parts;
                            } else {
                                displayVal = String(val);
                            }

                            const numVal = typeof val === "number" ? val : (typeof val === "object" && val?.fund != null ? val.fund : null);
                            const isGood = (key === "sharpe_ratio" && numVal > 1) || (key === "alpha" && numVal > 0) || (key === "sortino_ratio" && numVal > 1) || (key === "r_squared" && numVal > 0.8);
                            const isBad = key === "max_drawdown";
                            return (
                                <div key={key} className={styles.riskMetricCard}>
                                    <span className={styles.riskMetricLabel}>{label}</span>
                                    <span className={`${styles.riskMetricVal} ${isBad ? "negative" : isGood ? "positive" : ""}`}>
                                        {displayVal}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </section>
            )}

            {/* ===== SIP RETURNS (from factsheet) ===== */}
            {fund.sip_returns && fund.sip_returns.length > 0 && (
                <section className={`card ${styles.section}`}>
                    <h2 className="section-title">💰 SIP Returns</h2>
                    <div className={styles.tableWrap}>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Period</th>
                                    <th>Invested</th>
                                    <th>Market Value</th>
                                    <th>Return</th>
                                </tr>
                            </thead>
                            <tbody>
                                {fund.sip_returns.filter(s => !(s.scheme_name || "").toLowerCase().includes("benchmark")).map((s, i) => (
                                    <tr key={i}>
                                        <td style={{ fontWeight: 600 }}>{s.period}</td>
                                        <td>{s.total_invested != null ? `₹${Number(s.total_invested).toLocaleString("en-IN")}` : "—"}</td>
                                        <td>{s.market_value != null ? `₹${Number(s.market_value).toLocaleString("en-IN")}` : "—"}</td>
                                        <td className={s.return_pct >= 0 ? "positive" : "negative"} style={{ fontWeight: 700 }}>
                                            {s.return_pct != null ? `${s.return_pct}%` : "—"}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>
            )}

            {/* ===== SIP CALCULATOR ===== */}
            {returns.length > 0 && (
                <section className={`card ${styles.section}`}>
                    <h2 className="section-title">🧮 SIP Calculator</h2>
                    <SIPCalculator fund={fund} />
                </section>
            )}

            {/* ===== KEY HIGHLIGHTS ===== */}
            {fund.additional_info?.key_highlights && fund.additional_info.key_highlights.length > 0 && (
                <section className={`card ${styles.section}`}>
                    <h2 className="section-title">🌟 Key Highlights</h2>
                    <div className={styles.highlightsList}>
                        {fund.additional_info.key_highlights.map((h, i) => (
                            <div key={i} className={styles.highlightItem}>
                                <span className={styles.highlightIcon}>✦</span>
                                <span>{h}</span>
                            </div>
                        ))}
                    </div>
                    {fund.additional_info.about_the_scheme && fund.additional_info.about_the_scheme.length > 0 && (
                        <div style={{ marginTop: 16 }}>
                            <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 10 }}>About the Scheme</h3>
                            <div className={styles.highlightsList}>
                                {fund.additional_info.about_the_scheme.map((item, i) => (
                                    <div key={i} className={styles.highlightItem}>
                                        <span className={styles.highlightIcon}>•</span>
                                        <span>{item}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </section>
            )}

            {/* ===== ALLOCATION STRATEGY ===== */}
            {(fund.additional_info?.equity_allocation_strategy || fund.additional_info?.fixed_income_allocation_strategy || fund.additional_info?.commodity_allocation_strategy) && (
                <section className={`card ${styles.section}`}>
                    <h2 className="section-title">🎯 Investment Strategy</h2>
                    <div className={styles.strategyGrid}>
                        {fund.additional_info.equity_allocation_strategy && (
                            <div className={styles.strategyCard}>
                                <div className={styles.strategyLabel}>Equity Strategy</div>
                                <div className={styles.strategyText}>{fund.additional_info.equity_allocation_strategy}</div>
                            </div>
                        )}
                        {fund.additional_info.fixed_income_allocation_strategy && (
                            <div className={styles.strategyCard}>
                                <div className={styles.strategyLabel}>Fixed Income Strategy</div>
                                <div className={styles.strategyText}>{fund.additional_info.fixed_income_allocation_strategy}</div>
                            </div>
                        )}
                        {fund.additional_info.commodity_allocation_strategy && (
                            <div className={styles.strategyCard}>
                                <div className={styles.strategyLabel}>Commodity Strategy</div>
                                <div className={styles.strategyText}>{fund.additional_info.commodity_allocation_strategy}</div>
                            </div>
                        )}
                    </div>
                </section>
            )}

            {/* ===== PORTFOLIO ACTIVITY ===== */}
            {(fund.additional_info?.stocks_new_entries?.length > 0 || fund.additional_info?.stocks_total_exits?.length > 0) && (
                <section className={`card ${styles.section}`}>
                    <h2 className="section-title">📋 Portfolio Activity</h2>
                    <div className={styles.activityGrid}>
                        {fund.additional_info.stocks_new_entries?.length > 0 && (
                            <div className={styles.activityColumn}>
                                <div className={styles.activityTitle} style={{ color: "#10b981" }}>↑ New Entries</div>
                                {fund.additional_info.stocks_new_entries.map((s, i) => (
                                    <div key={i} className={styles.activityEntry}>{s}</div>
                                ))}
                            </div>
                        )}
                        {fund.additional_info.stocks_total_exits?.length > 0 && (
                            <div className={styles.activityColumn}>
                                <div className={styles.activityTitle} style={{ color: "#ef4444" }}>↓ Exits</div>
                                {fund.additional_info.stocks_total_exits.map((s, i) => (
                                    <div key={i} className={styles.activityExit}>{s}</div>
                                ))}
                            </div>
                        )}
                    </div>
                </section>
            )}

            {/* ===== PORTFOLIO STATISTICS ===== */}
            {fund.portfolio_stats && Object.values(fund.portfolio_stats).some(v => v != null) && (
                <section className={`card ${styles.section}`}>
                    <h2 className="section-title">📈 Portfolio Statistics</h2>
                    <div className={styles.statsGrid}>
                        {fund.portfolio_stats.pe_ratio != null && (
                            <div className={styles.statItem}>
                                <span className={styles.statItemLabel}>P/E Ratio</span>
                                <span className={styles.statItemValue}>{fund.portfolio_stats.pe_ratio}</span>
                            </div>
                        )}
                        {fund.portfolio_stats.pb_ratio != null && (
                            <div className={styles.statItem}>
                                <span className={styles.statItemLabel}>P/B Ratio</span>
                                <span className={styles.statItemValue}>{fund.portfolio_stats.pb_ratio}</span>
                            </div>
                        )}
                        {fund.portfolio_stats.dividend_yield != null && (
                            <div className={styles.statItem}>
                                <span className={styles.statItemLabel}>Dividend Yield</span>
                                <span className={styles.statItemValue}>{fund.portfolio_stats.dividend_yield}%</span>
                            </div>
                        )}
                        {fund.portfolio_stats.roe != null && (
                            <div className={styles.statItem}>
                                <span className={styles.statItemLabel}>ROE</span>
                                <span className={styles.statItemValue}>{fund.portfolio_stats.roe}%</span>
                            </div>
                        )}
                        {fund.portfolio_stats.roa != null && (
                            <div className={styles.statItem}>
                                <span className={styles.statItemLabel}>ROA</span>
                                <span className={styles.statItemValue}>{fund.portfolio_stats.roa}%</span>
                            </div>
                        )}
                        {fund.portfolio_stats.avg_market_cap_cr != null && (
                            <div className={styles.statItem}>
                                <span className={styles.statItemLabel}>Avg Mkt Cap</span>
                                <span className={styles.statItemValue}>₹{Number(fund.portfolio_stats.avg_market_cap_cr).toLocaleString("en-IN")} Cr</span>
                            </div>
                        )}
                        {fund.portfolio_stats.equity_style && (
                            <div className={styles.statItem}>
                                <span className={styles.statItemLabel}>Equity Style</span>
                                <span className={styles.statItemValue} style={{ fontSize: 14 }}>{fund.portfolio_stats.equity_style}</span>
                            </div>
                        )}
                    </div>
                    {(fund.additional_info?.portfolio_dividend_yield != null || fund.additional_info?.benchmark_dividend_yield != null) && (
                        <div style={{ display: "flex", gap: 16, marginTop: 12 }}>
                            {fund.additional_info.portfolio_dividend_yield != null && (
                                <div className={styles.statItem} style={{ flex: 1 }}>
                                    <span className={styles.statItemLabel}>Portfolio Div. Yield</span>
                                    <span className={styles.statItemValue}>{fund.additional_info.portfolio_dividend_yield}%</span>
                                </div>
                            )}
                            {fund.additional_info.benchmark_dividend_yield != null && (
                                <div className={styles.statItem} style={{ flex: 1 }}>
                                    <span className={styles.statItemLabel}>Benchmark Div. Yield</span>
                                    <span className={styles.statItemValue}>{fund.additional_info.benchmark_dividend_yield}%</span>
                                </div>
                            )}
                        </div>
                    )}
                </section>
            )}

            {/* ===== FUND INFO ===== */}
            <section className={`card ${styles.section}`}>
                <h2 className="section-title">ℹ️ Fund Information</h2>
                <div className={styles.infoGrid}>
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>AMC</span>
                        <span className={styles.infoValue}>{fund.amc || "—"}</span>
                    </div>
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>Benchmark</span>
                        <span className={styles.infoValue}>{fund.benchmark || "—"}</span>
                    </div>
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>Category</span>
                        <span className={styles.infoValue}>{fund.category || "—"}</span>
                    </div>
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>Scheme Type</span>
                        <span className={styles.infoValue}>{fund.scheme_type || "—"}</span>
                    </div>
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>Inception Date</span>
                        <span className={styles.infoValue}>{fund.inception_date || "—"}</span>
                    </div>
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>Plans Offered</span>
                        <span className={styles.infoValue}>{fund.plans_offered || "—"}</span>
                    </div>
                    {fund.isin && (
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>ISIN</span>
                            <span className={styles.infoValue}>{fund.isin}</span>
                        </div>
                    )}
                    {fund.amfi_code && (
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>AMFI Code</span>
                            <span className={styles.infoValue}>{fund.amfi_code}</span>
                        </div>
                    )}
                    {fund.registrar && (
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>Registrar</span>
                            <span className={styles.infoValue}>{fund.registrar}</span>
                        </div>
                    )}
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>Exit Load</span>
                        <span className={styles.infoValue}>{fund.exit_load || "—"}</span>
                    </div>
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>Min SIP</span>
                        <span className={styles.infoValue}>{fund.min_sip != null ? safeMoney(fund.min_sip) : "—"}</span>
                    </div>
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>Min Lumpsum</span>
                        <span className={styles.infoValue}>{fund.min_lumpsum != null ? (typeof fund.min_lumpsum === "number" ? safeMoney(fund.min_lumpsum) : fund.min_lumpsum) : "—"}</span>
                    </div>
                    {fund.min_additional != null && (
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>Min Additional</span>
                            <span className={styles.infoValue}>{safeMoney(fund.min_additional)}</span>
                        </div>
                    )}
                    {fund.min_redemption != null && (
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>Min Redemption</span>
                            <span className={styles.infoValue}>{safeMoney(fund.min_redemption)}</span>
                        </div>
                    )}
                    <div className={styles.infoItem}>
                        <span className={styles.infoLabel}>Monthly Avg AUM</span>
                        <span className={styles.infoValue}>{fund.monthly_avg_aum != null ? `₹${fund.monthly_avg_aum} Cr` : "—"}</span>
                    </div>
                    {(fund.turnover_ratio != null || fund.portfolio_turnover != null) && (
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>Turnover Ratio</span>
                            <span className={styles.infoValue}>{fund.turnover_ratio ?? fund.portfolio_turnover ?? "—"}</span>
                        </div>
                    )}
                    {fund.lock_in_period && (
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>Lock-in Period</span>
                            <span className={styles.infoValue}>{fund.lock_in_period}</span>
                        </div>
                    )}
                    {fund.stamp_duty && (
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>Stamp Duty</span>
                            <span className={styles.infoValue}>{fund.stamp_duty}</span>
                        </div>
                    )}
                </div>

                {/* SIP/SWP/STP Availability */}
                {(fund.sip_available != null || fund.swp_available != null || fund.stp_available != null) && (
                    <div style={{ marginTop: 16 }}>
                        <span style={{ fontWeight: 600, color: "var(--text-secondary)", fontSize: 13, display: "block", marginBottom: 10 }}>Availability</span>
                        <div className={styles.availGrid}>
                            {fund.sip_available != null && (
                                <span className={`${styles.availBadge} ${fund.sip_available ? styles.availYes : styles.availNo}`}>
                                    {fund.sip_available ? "✓" : "✗"} SIP
                                </span>
                            )}
                            {fund.swp_available != null && (
                                <span className={`${styles.availBadge} ${fund.swp_available ? styles.availYes : styles.availNo}`}>
                                    {fund.swp_available ? "✓" : "✗"} SWP
                                </span>
                            )}
                            {fund.stp_available != null && (
                                <span className={`${styles.availBadge} ${fund.stp_available ? styles.availYes : styles.availNo}`}>
                                    {fund.stp_available ? "✓" : "✗"} STP
                                </span>
                            )}
                        </div>
                    </div>
                )}

                {fund.investment_objective && (
                    <div style={{ marginTop: 16, padding: "12px 16px", background: "var(--bg-secondary)", borderRadius: 8 }}>
                        <span style={{ fontWeight: 600, color: "var(--text-secondary)", fontSize: 13 }}>Investment Objective</span>
                        <p style={{ margin: "6px 0 0", fontSize: 13, lineHeight: 1.6, color: "var(--text-primary)" }}>{fund.investment_objective}</p>
                    </div>
                )}
            </section>

            {/* ===== ADDITIONAL INFO (dynamic) ===== */}
            {fund.additional_info && Object.keys(fund.additional_info).length > 0 && (() => {
                const formatKey = (key) => key
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, c => c.toUpperCase())
                    .replace(/\bPtp\b/g, "PTP")
                    .replace(/\bIsin\b/g, "ISIN")
                    .replace(/\bNav\b/g, "NAV")
                    .replace(/\bAum\b/g, "AUM");

                const isSimple = (val) => val == null || typeof val === "string" || typeof val === "number" || typeof val === "boolean";
                const isNumericObject = (val) => typeof val === "object" && val !== null && !Array.isArray(val) && Object.values(val).every(v => typeof v === "number");
                const isFlatArray = (val) => Array.isArray(val) && val.length > 0 && typeof val[0] !== "object";
                const isTableArray = (val) => Array.isArray(val) && val.length > 0 && typeof val[0] === "object";
                const isKVObject = (val) => typeof val === "object" && val !== null && !Array.isArray(val) && Object.values(val).every(v => isSimple(v));

                const formatSimple = (val) => {
                    if (val == null) return "—";
                    if (typeof val === "boolean") return val ? "Yes" : "No";
                    if (typeof val === "number") return val.toLocaleString("en-IN");
                    return String(val);
                };

                // Categorize entries
                const simpleEntries = [];
                const numericObjects = [];
                const kvObjects = [];
                const tableArrays = [];

                for (const [key, val] of Object.entries(fund.additional_info)) {
                    if (isSimple(val) || isFlatArray(val)) {
                        simpleEntries.push([key, isFlatArray(val) ? val.join(", ") : val]);
                    } else if (isNumericObject(val)) {
                        numericObjects.push([key, val]);
                    } else if (isTableArray(val)) {
                        tableArrays.push([key, val]);
                    } else if (isKVObject(val)) {
                        kvObjects.push([key, val]);
                    }
                    // Skip deeply nested/complex structures silently
                }

                return (
                    <section className={`card ${styles.section}`}>
                        <h2 className="section-title">📋 Additional Information</h2>
                        {simpleEntries.length > 0 && (
                            <div className={styles.infoGrid}>
                                {simpleEntries.map(([key, val]) => (
                                    <div key={key} className={styles.infoItem}>
                                        <span className={styles.infoLabel}>{formatKey(key)}</span>
                                        <span className={styles.infoValue}>{formatSimple(val)}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                        {kvObjects.map(([key, obj]) => (
                            <div key={key} style={{ marginTop: 16 }}>
                                <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>{formatKey(key)}</h3>
                                <div className={styles.infoGrid}>
                                    {Object.entries(obj).map(([k, v]) => (
                                        <div key={k} className={styles.infoItem}>
                                            <span className={styles.infoLabel}>{formatKey(k)}</span>
                                            <span className={styles.infoValue}>{formatSimple(v)}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                        {numericObjects.map(([key, obj]) => (
                            <div key={key} style={{ marginTop: 16 }}>
                                <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>{formatKey(key)}</h3>
                                <AllocationBar data={obj} colors={sectorColors} />
                            </div>
                        ))}
                        {tableArrays.map(([key, arr]) => (
                            <div key={key} style={{ marginTop: 16 }}>
                                <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>{formatKey(key)}</h3>
                                <div className={styles.tableWrap}>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                {Object.keys(arr[0]).map(col => (
                                                    <th key={col}>{formatKey(col)}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {arr.map((row, i) => (
                                                <tr key={i}>
                                                    {Object.values(row).map((cell, j) => (
                                                        <td key={j}>{cell != null ? (typeof cell === "number" ? cell.toLocaleString("en-IN") : String(cell)) : "—"}</td>
                                                    ))}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ))}
                    </section>
                );
            })()}
        </div>
    );
}
