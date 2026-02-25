"use client";

import { useState, useMemo, useEffect } from "react";
import { useParams } from "next/navigation";
import indexData from "../../data/indices.json";
import { useNavData } from "../../hooks/useNavData";
import { getAmcLogoUrl } from "../../../lib/amcLogos";
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

/**
 * Compute risk metrics from fund NAV series and benchmark index series.
 * Both should be arrays of { date, nav } sorted oldest-first.
 * Returns object with: beta, alpha, sharpe_ratio, standard_deviation, r_squared,
 *   treynor_ratio, sortino_ratio, information_ratio, tracking_error
 */
function computeRiskMetrics(fundNavData, benchmarkData) {
    if (!fundNavData?.length || !benchmarkData?.length) return null;

    // Build date-indexed maps
    const fundMap = new Map(fundNavData.map(d => [d.date, d.nav]));
    const benchMap = new Map(benchmarkData.map(d => [d.date, d.nav]));

    // Find common dates (sorted)
    const commonDates = [...fundMap.keys()].filter(d => benchMap.has(d)).sort();
    if (commonDates.length < 30) return null; // Need at least 30 data points

    // Compute daily log returns
    const fundReturns = [];
    const benchReturns = [];
    const excessReturns = []; // fund - benchmark

    for (let i = 1; i < commonDates.length; i++) {
        const fPrev = fundMap.get(commonDates[i - 1]);
        const fCurr = fundMap.get(commonDates[i]);
        const bPrev = benchMap.get(commonDates[i - 1]);
        const bCurr = benchMap.get(commonDates[i]);

        if (fPrev > 0 && bPrev > 0) {
            const fr = Math.log(fCurr / fPrev);
            const br = Math.log(bCurr / bPrev);
            fundReturns.push(fr);
            benchReturns.push(br);
            excessReturns.push(fr - br);
        }
    }

    if (fundReturns.length < 20) return null;

    const n = fundReturns.length;
    const mean = arr => arr.reduce((s, v) => s + v, 0) / arr.length;
    const variance = arr => { const m = mean(arr); return arr.reduce((s, v) => s + (v - m) ** 2, 0) / (arr.length - 1); };

    const fundMean = mean(fundReturns);
    const benchMean = mean(benchReturns);
    const fundVar = variance(fundReturns);
    const benchVar = variance(benchReturns);
    const fundStd = Math.sqrt(fundVar);

    // Covariance
    let cov = 0;
    for (let i = 0; i < n; i++) {
        cov += (fundReturns[i] - fundMean) * (benchReturns[i] - benchMean);
    }
    cov /= (n - 1);

    // Beta = Cov(fund, bench) / Var(bench)
    const beta = benchVar > 0 ? cov / benchVar : null;

    // Annualized values (252 trading days)
    const annualFundReturn = fundMean * 252;
    const annualBenchReturn = benchMean * 252;
    const annualStdDev = fundStd * Math.sqrt(252);

    // Risk-free rate (India 1Y T-bill ≈ 6.5%)
    const rf = 0.065;

    // Alpha (Jensen's) = Fund Return - [Rf + Beta * (Bench Return - Rf)]
    const alpha = beta != null ? annualFundReturn - (rf + beta * (annualBenchReturn - rf)) : null;

    // Sharpe Ratio = (Fund Return - Rf) / StdDev
    const sharpe = annualStdDev > 0 ? (annualFundReturn - rf) / annualStdDev : null;

    // Correlation & R²
    const benchStd = Math.sqrt(benchVar);
    const correlation = (fundStd > 0 && benchStd > 0) ? cov / (fundStd * benchStd) : null;
    const rSquared = correlation != null ? correlation ** 2 : null;

    // Treynor Ratio = (Fund Return - Rf) / Beta
    const treynor = beta != null && beta !== 0 ? (annualFundReturn - rf) / beta : null;

    // Sortino Ratio - uses downside deviation
    const dailyRf = rf / 252;
    const downsideReturns = fundReturns.filter(r => r < dailyRf).map(r => (r - dailyRf) ** 2);
    const downsideDev = downsideReturns.length > 0 ? Math.sqrt(downsideReturns.reduce((s, v) => s + v, 0) / downsideReturns.length) * Math.sqrt(252) : null;
    const sortino = downsideDev != null && downsideDev > 0 ? (annualFundReturn - rf) / downsideDev : null;

    // Tracking Error = StdDev of excess returns (annualized)
    const trackingError = Math.sqrt(variance(excessReturns)) * Math.sqrt(252);

    // Information Ratio = (Fund Return - Bench Return) / Tracking Error
    const infoRatio = trackingError > 0 ? (annualFundReturn - annualBenchReturn) / trackingError : null;

    return {
        beta: beta != null ? +beta.toFixed(2) : null,
        alpha: alpha != null ? +(alpha * 100).toFixed(2) : null, // as percentage
        sharpe_ratio: sharpe != null ? +sharpe.toFixed(2) : null,
        standard_deviation: annualStdDev > 0 ? +(annualStdDev * 100).toFixed(2) : null, // as percentage
        r_squared: rSquared != null ? +rSquared.toFixed(4) : null,
        treynor_ratio: treynor != null ? +treynor.toFixed(2) : null,
        sortino_ratio: sortino != null ? +sortino.toFixed(2) : null,
        information_ratio: infoRatio != null ? +infoRatio.toFixed(2) : null,
        tracking_error: trackingError > 0 ? +(trackingError * 100).toFixed(2) : null, // as percentage
    };
}

// Dual-line SVG chart: Fund NAV vs Benchmark (both normalized to base 100)
function NavChart({ data, fundNavData, benchmarkLabel, fundLabel }) {
    const hasBenchmark = data && data.length > 0;
    const hasFundNav = fundNavData && fundNavData.length > 0;
    if (!hasBenchmark && !hasFundNav) return <div className={styles.noData}>No chart data available</div>;

    const w = 800, h = 320, padX = 50, padY = 30, padBottom = 45;

    // Normalize both datasets to base 100 and align date ranges
    function normalize(points) {
        if (!points || !points.length) return [];
        const base = points[0].nav;
        if (!base) return points;
        return points.map(p => ({ date: p.date, nav: (p.nav / base) * 100 }));
    }

    const normBench = normalize(data || []);
    const normFund = normalize(fundNavData || []);

    // Find overlapping date range if both exist
    let benchFiltered = normBench;
    let fundFiltered = normFund;

    if (hasBenchmark && hasFundNav) {
        const benchDates = new Set(normBench.map(d => d.date));
        const fundDates = new Set(normFund.map(d => d.date));
        // Find common start date
        const allBenchDates = normBench.map(d => d.date).sort();
        const allFundDates = normFund.map(d => d.date).sort();
        const startDate = allBenchDates[0] > allFundDates[0] ? allBenchDates[0] : allFundDates[0];
        benchFiltered = normBench.filter(d => d.date >= startDate);
        fundFiltered = normFund.filter(d => d.date >= startDate);
        // Re-normalize after filtering
        if (benchFiltered.length > 0) {
            const base = benchFiltered[0].nav;
            benchFiltered = benchFiltered.map(p => ({ date: p.date, nav: (p.nav / base) * 100 }));
        }
        if (fundFiltered.length > 0) {
            const base = fundFiltered[0].nav;
            fundFiltered = fundFiltered.map(p => ({ date: p.date, nav: (p.nav / base) * 100 }));
        }
    }

    // Compute global Y range
    const allNavs = [...benchFiltered.map(d => d.nav), ...fundFiltered.map(d => d.nav)];
    const minNav = Math.min(...allNavs);
    const maxNav = Math.max(...allNavs);
    const range = maxNav - minNav || 1;

    function toPolyline(pts) {
        if (!pts.length) return "";
        return pts.map((d, i) => {
            const x = padX + (i / Math.max(pts.length - 1, 1)) * (w - padX * 2);
            const y = padY + (1 - (d.nav - minNav) / range) * (h - padY - padBottom);
            return `${x},${y}`;
        }).join(" ");
    }

    const benchPolyline = toPolyline(benchFiltered);
    const fundPolyline = toPolyline(fundFiltered);

    // Area under fund line
    const primaryData = hasFundNav ? fundFiltered : benchFiltered;
    const primaryPoly = hasFundNav ? fundPolyline : benchPolyline;
    const endX = padX + ((primaryData.length - 1) / Math.max(primaryData.length - 1, 1)) * (w - padX * 2);
    const areaPoints = primaryData.length > 0 ? `${padX},${h - padBottom} ${primaryPoly} ${endX},${h - padBottom}` : "";

    // Y labels
    const yLabels = [];
    for (let i = 0; i <= 4; i++) {
        const val = minNav + (range * i) / 4;
        const y = padY + (1 - i / 4) * (h - padY - padBottom);
        yLabels.push({ val: val.toFixed(0), y });
    }

    // X labels from primary dataset
    const xData = primaryData.length > 0 ? primaryData : benchFiltered;
    const xLabels = [];
    const step = Math.floor(xData.length / 5) || 1;
    for (let i = 0; i < xData.length; i += step) {
        const x = padX + (i / Math.max(xData.length - 1, 1)) * (w - padX * 2);
        const d = new Date(xData[i].date);
        xLabels.push({ label: d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" }), x });
    }

    return (
        <div>
            <svg viewBox={`0 0 ${w} ${h}`} className={styles.chartSvg}>
                <defs>
                    <linearGradient id="fundAreaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity="0.15" />
                        <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
                    </linearGradient>
                </defs>
                {yLabels.map((l, i) => (
                    <g key={i}>
                        <line x1={padX} y1={l.y} x2={w - padX} y2={l.y} stroke="rgba(255,255,255,0.05)" />
                        <text x={padX - 8} y={l.y + 4} fill="#64748b" fontSize="11" textAnchor="end">{l.val}</text>
                    </g>
                ))}
                {xLabels.map((l, i) => (
                    <text key={i} x={l.x} y={h - 10} fill="#64748b" fontSize="11" textAnchor="middle">{l.label}</text>
                ))}
                {/* Area fill under fund line */}
                {hasFundNav && areaPoints && <polygon points={areaPoints} fill="url(#fundAreaGrad)" />}
                {/* Benchmark line (blue, dashed) */}
                {hasBenchmark && (
                    <polyline points={benchPolyline} fill="none" stroke="#3b82f6" strokeWidth="1.8"
                        strokeDasharray={hasFundNav ? "6,3" : "0"} strokeLinejoin="round" opacity={hasFundNav ? 0.7 : 1} />
                )}
                {/* Fund NAV line (green, solid) */}
                {hasFundNav && (
                    <polyline points={fundPolyline} fill="none" stroke="#10b981" strokeWidth="2.2" strokeLinejoin="round" />
                )}
            </svg>
            {/* Legend */}
            <div className={styles.chartLegend}>
                {hasFundNav && (
                    <div className={styles.legendItem}>
                        <span className={styles.legendDot} style={{ background: "#10b981" }} />
                        <span>{fundLabel || "Fund NAV"}</span>
                    </div>
                )}
                {hasBenchmark && (
                    <div className={styles.legendItem}>
                        <span className={styles.legendDot} style={{ background: "#3b82f6" }} />
                        <span>{benchmarkLabel || "Benchmark"}</span>
                    </div>
                )}
                <div className={styles.legendItem} style={{ color: "var(--text-muted)", fontSize: 11 }}>
                    Normalized to base 100
                </div>
            </div>
        </div>
    );
}

// Risk-o-meter gauge component (semicircular speedometer)
function Riskometer({ level, size = "small" }) {
    if (!level) return null;
    const levels = ["Low", "Moderately Low", "Moderate", "Moderately High", "High", "Very High"];
    const idx = levels.indexOf(level);
    const colors = ["#10b981", "#34d399", "#f59e0b", "#f97316", "#ef4444", "#dc2626"];
    if (idx === -1) return <span className="badge badge-blue">{level}</span>;

    const isLarge = size === "large";
    const w = isLarge ? 200 : 100;
    const h = isLarge ? 120 : 60;
    const cx = w / 2;
    const cy = isLarge ? 100 : 52;
    const r = isLarge ? 80 : 40;
    const strokeW = isLarge ? 14 : 8;
    const segments = 6;
    const gap = 3; // degrees gap between segments
    const totalArc = 180 - (segments - 1) * gap;
    const segArc = totalArc / segments;

    // Build arc segments
    const arcs = [];
    for (let i = 0; i < segments; i++) {
        const startAngle = 180 + i * (segArc + gap);
        const endAngle = startAngle + segArc;
        const startRad = (startAngle * Math.PI) / 180;
        const endRad = (endAngle * Math.PI) / 180;
        const x1 = cx + r * Math.cos(startRad);
        const y1 = cy + r * Math.sin(startRad);
        const x2 = cx + r * Math.cos(endRad);
        const y2 = cy + r * Math.sin(endRad);
        arcs.push(
            <path
                key={i}
                d={`M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`}
                fill="none"
                stroke={i <= idx ? colors[i] : "var(--bg-secondary)"}
                strokeWidth={strokeW}
                strokeLinecap="round"
                opacity={i <= idx ? 1 : 0.3}
            />
        );
    }

    // Needle angle: point to middle of active segment
    const needleAngle = 180 + idx * (segArc + gap) + segArc / 2;
    const needleRad = (needleAngle * Math.PI) / 180;
    const needleLen = r - (isLarge ? 20 : 10);
    const nx = cx + needleLen * Math.cos(needleRad);
    const ny = cy + needleLen * Math.sin(needleRad);

    return (
        <div className={`${styles.riskometer} ${isLarge ? styles.riskometerLarge : ""}`}>
            <svg viewBox={`0 0 ${w} ${h}`} className={styles.riskGauge} style={{ width: w, height: h }}>
                {arcs}
                {/* Needle */}
                <line x1={cx} y1={cy} x2={nx} y2={ny}
                    stroke={colors[idx]} strokeWidth={isLarge ? 2.5 : 1.5} strokeLinecap="round" />
                {/* Center dot */}
                <circle cx={cx} cy={cy} r={isLarge ? 5 : 3} fill={colors[idx]} />
            </svg>
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

    // Fetch historical NAV for this fund from mfapi.in
    const [fundNavHistory, setFundNavHistory] = useState([]);
    useEffect(() => {
        if (!fund) return;
        // Try AMFI code first, then fall back to searching by fund name
        const code = liveNav?.code;
        const url = code
            ? `/api/nav/history?code=${code}`
            : `/api/nav/history?search=${encodeURIComponent(fund.fund_name)}`;

        fetch(url)
            .then(res => res.json())
            .then(data => {
                if (data.data && data.data.length > 0) {
                    setFundNavHistory(data.data);
                }
            })
            .catch(() => { });
    }, [liveNav?.code, fund?.fund_name]);

    // Get real benchmark data for this fund
    const benchmark = useMemo(() => getBenchmarkData(fund?.benchmark), [fund?.benchmark]);
    const chartData = filterByPeriod(benchmark.points, chartPeriod);
    const fundChartData = filterByPeriod(fundNavHistory, chartPeriod);

    // Compute risk metrics from historical data (fallback for OCR-extracted metrics)
    const calculatedMetrics = useMemo(
        () => computeRiskMetrics(fundNavHistory, benchmark.points),
        [fundNavHistory, benchmark.points]
    );

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
                        {fund.amc && (
                            <div className={styles.fundAmcHeader}>
                                {(() => {
                                    const logoUrl = getAmcLogoUrl(fund.amc_slug);
                                    return logoUrl ? (
                                        <img src={logoUrl} alt={fund.amc} className={styles.fundAmcHeaderLogo} />
                                    ) : null;
                                })()}
                                <span className={styles.fundAmcHeaderName}>{fund.amc}</span>
                            </div>
                        )}
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

            {/* ===== ALPHA SUMMARY BANNER ===== */}
            {returns.length > 0 && (() => {
                const r1Y = returns.find(r => r.period === "1Y");
                const r3Y = returns.find(r => r.period === "3Y");
                const alpha1Y = (r1Y?.fund_return != null && r1Y?.benchmark_return != null) ? r1Y.fund_return - r1Y.benchmark_return : null;
                const alpha3Y = (r3Y?.fund_return != null && r3Y?.benchmark_return != null) ? r3Y.fund_return - r3Y.benchmark_return : null;
                if (alpha1Y == null && alpha3Y == null) return null;
                return (
                    <section className={`card ${styles.section} ${styles.alphaBanner}`}>
                        <div className={styles.alphaBannerHeader}>
                            <h2 className="section-title">⚡ Benchmark Comparison</h2>
                            <span className={styles.alphaBenchName}>
                                vs {fund.benchmark || benchmark.name}
                            </span>
                        </div>
                        <div className={styles.alphaCards}>
                            {alpha1Y != null && (
                                <div className={`${styles.alphaCard} ${alpha1Y >= 0 ? styles.alphaPositive : styles.alphaNegative}`}>
                                    <span className={styles.alphaLabel}>1 Year Alpha</span>
                                    <span className={styles.alphaValue}>
                                        {alpha1Y >= 0 ? "▲" : "▼"} {alpha1Y >= 0 ? "+" : ""}{alpha1Y.toFixed(2)}%
                                    </span>
                                    <span className={styles.alphaDetail}>
                                        Fund {safe(r1Y.fund_return, "%")} vs Benchmark {safe(r1Y.benchmark_return, "%")}
                                    </span>
                                </div>
                            )}
                            {alpha3Y != null && (
                                <div className={`${styles.alphaCard} ${alpha3Y >= 0 ? styles.alphaPositive : styles.alphaNegative}`}>
                                    <span className={styles.alphaLabel}>3 Year Alpha</span>
                                    <span className={styles.alphaValue}>
                                        {alpha3Y >= 0 ? "▲" : "▼"} {alpha3Y >= 0 ? "+" : ""}{alpha3Y.toFixed(2)}%
                                    </span>
                                    <span className={styles.alphaDetail}>
                                        Fund {safe(r3Y.fund_return, "%")} vs Benchmark {safe(r3Y.benchmark_return, "%")}
                                    </span>
                                </div>
                            )}
                        </div>
                    </section>
                );
            })()}

            {/* ===== FUND vs BENCHMARK CHART ===== */}
            <section className={`card ${styles.section}`}>
                <div className={styles.sectionHeader}>
                    <h2 className="section-title">📈 Fund vs Benchmark</h2>
                    <div className="pill-tabs">
                        {CHART_PERIODS.map((p) => (
                            <button key={p} className={`pill-tab ${chartPeriod === p ? "active" : ""}`} onClick={() => setChartPeriod(p)}>
                                {p}
                            </button>
                        ))}
                    </div>
                </div>
                <NavChart data={chartData} fundNavData={fundChartData} benchmarkLabel={benchmark.name} fundLabel={fund.fund_name} />
            </section>

            {/* ===== RETURNS TABLE ===== */}
            {returns.length > 0 && (() => {
                const maxReturn = Math.max(...returns.map(r => Math.max(Math.abs(r.fund_return || 0), Math.abs(r.benchmark_return || 0))));
                const barScale = maxReturn > 0 ? 100 / maxReturn : 1;
                return (
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
                                        <th>Alpha</th>
                                        <th style={{ minWidth: 160 }}>Comparison</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {returns.map((r) => {
                                        const diff = (r.fund_return != null && r.benchmark_return != null) ? r.fund_return - r.benchmark_return : null;
                                        const fundW = r.fund_return != null ? Math.abs(r.fund_return) * barScale : 0;
                                        const benchW = r.benchmark_return != null ? Math.abs(r.benchmark_return) * barScale : 0;
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
                                                <td>
                                                    <div className={styles.comparisonBars}>
                                                        <div className={styles.compBarRow}>
                                                            <div className={styles.compBarFund} style={{ width: `${Math.max(fundW, 2)}%` }} />
                                                        </div>
                                                        <div className={styles.compBarRow}>
                                                            <div className={styles.compBarBench} style={{ width: `${Math.max(benchW, 2)}%` }} />
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </section>
                );
            })()}

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
            {(() => {
                // Merge OCR-extracted risk metrics with calculated ones
                const ocrMetrics = riskMetrics || {};
                const hasOcr = Object.keys(ocrMetrics).length > 0 && Object.values(ocrMetrics).some(v => v != null);
                const hasCalc = calculatedMetrics != null;
                if (!hasOcr && !hasCalc) return null;

                // Order of display
                const metricOrder = ["beta", "alpha", "sharpe_ratio", "standard_deviation", "r_squared",
                    "treynor_ratio", "sortino_ratio", "information_ratio", "tracking_error", "max_drawdown"];

                // Build merged entries: OCR takes priority, calculated fills gaps
                const merged = {};
                for (const key of metricOrder) {
                    const ocrVal = ocrMetrics[key];
                    const calcVal = hasCalc ? calculatedMetrics[key] : null;
                    if (ocrVal != null) {
                        merged[key] = { val: ocrVal, source: "factsheet" };
                    } else if (calcVal != null) {
                        merged[key] = { val: calcVal, source: "calculated" };
                    }
                }
                // Also include any OCR-only keys not in our standard list
                for (const key of Object.keys(ocrMetrics)) {
                    if (!merged[key] && ocrMetrics[key] != null) {
                        merged[key] = { val: ocrMetrics[key], source: "factsheet" };
                    }
                }

                if (Object.keys(merged).length === 0) return null;

                return (
                    <section className={`card ${styles.section}`}>
                        <h2 className="section-title">⚡ Risk Metrics</h2>
                        <div className={styles.riskGrid}>
                            {Object.entries(merged).map(([key, { val, source }]) => {
                                const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

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
                                const suffix = key === "standard_deviation" || key === "tracking_error" || key === "alpha" ? "%" : "";

                                return (
                                    <div key={key} className={styles.riskMetricCard}>
                                        <span className={styles.riskMetricLabel}>
                                            {label}
                                            {source === "calculated" && (
                                                <span className={styles.calcBadge} title="Computed from historical NAV data">Calc</span>
                                            )}
                                        </span>
                                        <span className={`${styles.riskMetricVal} ${isBad ? "negative" : isGood ? "positive" : ""}`}>
                                            {displayVal}{suffix}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </section>
                );
            })()}

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
