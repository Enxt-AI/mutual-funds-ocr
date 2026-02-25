"use client";

import { useState, useMemo, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useNavData } from "./hooks/useNavData";
import { getAmcLogoUrl, getAmcInitial } from "../lib/amcLogos";
import styles from "./page.module.css";

function getRiskColor(risk) {
  if (!risk) return "#64748b";
  if (risk === "Low") return "#10b981";
  if (risk === "Moderately Low") return "#34d399";
  if (risk === "Moderate") return "#f59e0b";
  if (risk === "Moderately High") return "#f97316";
  return "#ef4444";
}

function getReturn(fund, period) {
  const r = fund.returns?.find((r) => r.period === period);
  return r?.fund_return;
}

function formatAUM(crores) {
  if (!crores) return "—";
  if (crores >= 1000) return `₹${(crores / 1000).toFixed(1)}K Cr`;
  return `₹${crores.toFixed(0)} Cr`;
}

const categoryGroups = ["All", "Equity", "Hybrid", "Debt", "Index", "ETF"];

function HomeContent() {
  const [allFunds, setAllFunds] = useState([]);
  const [dataLoading, setDataLoading] = useState(true);
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") === "compare" ? "compare" : "explore");

  useEffect(() => {
    fetch("/api/funds")
      .then((res) => res.json())
      .then((data) => { setAllFunds(data); setDataLoading(false); })
      .catch(() => setDataLoading(false));
  }, []);

  const funds = useMemo(() => allFunds.filter((f) => f.fund_name), [allFunds]);

  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("All");
  const { navMap, loading: navLoading, lastUpdated } = useNavData(funds);

  // Compare state
  const [compareList, setCompareList] = useState([]);
  const [compareSearch, setCompareSearch] = useState("");

  // AMC expand/collapse state
  const [expandedAmcs, setExpandedAmcs] = useState(new Set());

  const toggleAmc = (amcName) => {
    setExpandedAmcs((prev) => {
      const next = new Set(prev);
      if (next.has(amcName)) {
        next.delete(amcName);
      } else {
        next.add(amcName);
      }
      return next;
    });
  };

  const filtered = useMemo(() => {
    let result = funds;
    if (activeFilter !== "All") {
      result = result.filter((f) => f.category?.toLowerCase().includes(activeFilter.toLowerCase()));
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((f) =>
        f.fund_name?.toLowerCase().includes(q) ||
        f.category?.toLowerCase().includes(q) ||
        f.amc?.toLowerCase().includes(q)
      );
    }
    return result;
  }, [search, activeFilter, funds]);

  // Group filtered funds by AMC name, sorted alphabetically
  const amcGroups = useMemo(() => {
    const groups = new Map();
    for (const fund of filtered) {
      const amcName = fund.amc || "Unknown AMC";
      if (!groups.has(amcName)) {
        groups.set(amcName, []);
      }
      groups.get(amcName).push(fund);
    }
    // Sort by AMC name alphabetically
    const sorted = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    return sorted;
  }, [filtered]);

  // Compare search results
  const compareResults = useMemo(() => {
    if (!compareSearch.trim()) return [];
    const q = compareSearch.toLowerCase();
    return funds
      .filter((f) =>
        (f.fund_name?.toLowerCase().includes(q) || f.amc?.toLowerCase().includes(q)) &&
        !compareList.find((c) => c.slug === f.slug)
      )
      .slice(0, 8);
  }, [compareSearch, funds, compareList]);

  const addToCompare = (fund) => {
    if (compareList.length >= 4) return;
    if (compareList.find((c) => c.slug === fund.slug)) return;
    setCompareList([...compareList, fund]);
    setCompareSearch("");
  };

  const removeFromCompare = (slug) => {
    setCompareList(compareList.filter((f) => f.slug !== slug));
  };

  const totalAUM = funds.reduce((sum, f) => sum + (f.aum_crores || 0), 0);
  const amcCount = new Set(funds.map(f => f.amc).filter(Boolean)).size;

  return (
    <div className={styles.container}>
      {/* Hero */}
      <div className={styles.hero}>
        <h1 className={styles.heroTitle}>
          Explore <span className={styles.heroAccent}>Mutual Funds</span>
        </h1>
        <p className={styles.heroSub}>
          Analyze performance, holdings & risk metrics — powered by real AMC factsheet data
        </p>
        <div className={styles.heroStats}>
          <div className={styles.heroStat}>
            <span className={styles.heroStatNum}>{amcCount}</span>
            <span className={styles.heroStatLabel}>AMC{amcCount !== 1 ? "s" : ""}</span>
          </div>
          <div className={styles.heroStatDivider} />
          <div className={styles.heroStat}>
            <span className={styles.heroStatNum}>{funds.length}</span>
            <span className={styles.heroStatLabel}>Schemes</span>
          </div>
          <div className={styles.heroStatDivider} />
          <div className={styles.heroStat}>
            <span className={styles.heroStatNum}>{formatAUM(totalAUM)}</span>
            <span className={styles.heroStatLabel}>Total AUM</span>
          </div>
        </div>
      </div>

      {/* Tab Switcher */}

      {/* ========== EXPLORE TAB ========== */}
      {activeTab === "explore" && (
        <>
          <div className={styles.searchBar}>
            <span className={styles.searchIcon}>🔍</span>
            <input
              type="text"
              placeholder="Search funds by name, AMC, or category..."
              className={styles.searchInput}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className={styles.filterRow}>
            {categoryGroups.map((cat) => (
              <button
                key={cat}
                className={`${styles.filterPill} ${activeFilter === cat ? styles.filterActive : ""}`}
                onClick={() => setActiveFilter(cat)}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className={styles.resultCount}>
            Showing {filtered.length} schemes across {amcGroups.length} fund house{amcGroups.length !== 1 ? "s" : ""}
          </div>

          {/* AMC Grouped Accordion */}
          <div className={styles.amcList}>
            {amcGroups.map(([amcName, amcFunds]) => {
              const isExpanded = expandedAmcs.has(amcName);
              const amcTotalAUM = amcFunds.reduce((sum, f) => sum + (f.aum_crores || 0), 0);
              const categories = [...new Set(amcFunds.map(f => f.category).filter(Boolean))];
              const amcSlug = amcFunds[0]?.amc_slug;
              const logoUrl = getAmcLogoUrl(amcSlug);

              return (
                <div key={amcName} className={`${styles.amcGroup} ${isExpanded ? styles.amcGroupExpanded : ""}`}>
                  {/* AMC Header */}
                  <button className={styles.amcHeader} onClick={() => toggleAmc(amcName)}>
                    <div className={styles.amcHeaderLeft}>
                      <div className={`${styles.amcIcon} ${logoUrl ? styles.amcIconWithLogo : ""}`}>
                        {logoUrl ? (
                          <img src={logoUrl} alt={amcName} className={styles.amcLogo} />
                        ) : (
                          getAmcInitial(amcName)
                        )}
                      </div>
                      <div className={styles.amcInfo}>
                        <h3 className={styles.amcName}>{amcName}</h3>
                        <div className={styles.amcCategories}>
                          {categories.slice(0, 3).map((cat) => (
                            <span key={cat} className={styles.amcCategoryTag}>{cat}</span>
                          ))}
                          {categories.length > 3 && (
                            <span className={styles.amcCategoryTag}>+{categories.length - 3} more</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className={styles.amcHeaderRight}>
                      <div className={styles.amcStat}>
                        <span className={styles.amcStatNum}>{amcFunds.length}</span>
                        <span className={styles.amcStatLabel}>Scheme{amcFunds.length !== 1 ? "s" : ""}</span>
                      </div>
                      <div className={styles.amcStatDivider} />
                      <div className={styles.amcStat}>
                        <span className={styles.amcStatNum}>{formatAUM(amcTotalAUM)}</span>
                        <span className={styles.amcStatLabel}>AUM</span>
                      </div>
                      <span className={`${styles.amcChevron} ${isExpanded ? styles.amcChevronOpen : ""}`}>
                        ▾
                      </span>
                    </div>
                  </button>

                  {/* Expanded Schemes */}
                  {isExpanded && (
                    <div className={styles.amcSchemes}>
                      <div className={styles.fundGrid}>
                        {amcFunds.map((fund, idx) => (
                          <Link href={`/fund/${fund.slug}`} key={idx} className={styles.fundCard}>
                            <div className={styles.fundCardHeader}>
                              <div className={styles.fundAmcWithLogo}>
                                {(() => {
                                  const cardLogoUrl = getAmcLogoUrl(fund.amc_slug);
                                  return cardLogoUrl ? (
                                    <img src={cardLogoUrl} alt={fund.amc} className={styles.fundCardLogo} />
                                  ) : null;
                                })()}
                                <span className={styles.fundAmc}>{fund.amc || "—"}</span>
                              </div>
                              <span className={styles.fundRisk} style={{ color: getRiskColor(fund.risk_level) }}>
                                {fund.risk_level || "—"}
                              </span>
                            </div>
                            <h3 className={styles.fundName}>{fund.fund_name}</h3>
                            <div className={styles.fundCategory}>{fund.category || "—"}</div>
                            <div className={styles.fundMetrics}>
                              <div className={styles.metric}>
                                <span className={styles.metricLabel}>
                                  NAV {navMap[fund.slug] && <span className={styles.liveDot}>●</span>}
                                </span>
                                <span className={styles.metricValue}>
                                  {navMap[fund.slug]?.nav != null
                                    ? `₹${Number(navMap[fund.slug].nav).toFixed(2)}`
                                    : fund.nav != null ? `₹${Number(fund.nav).toFixed(2)}` : "—"}
                                </span>
                              </div>
                              <div className={styles.metric}>
                                <span className={styles.metricLabel}>AUM</span>
                                <span className={styles.metricValue}>{formatAUM(fund.aum_crores)}</span>
                              </div>
                              <div className={styles.metric}>
                                <span className={styles.metricLabel}>Expense</span>
                                <span className={styles.metricValue}>
                                  {fund.expense_ratio != null ? `${fund.expense_ratio}%` : "—"}
                                </span>
                              </div>
                            </div>
                            <div className={styles.fundReturns}>
                              {["1Y", "3Y", "5Y"].map((period) => {
                                const ret = getReturn(fund, period);
                                return (
                                  <div key={period} className={styles.returnItem}>
                                    <span className={styles.returnPeriod}>{period}</span>
                                    <span className={`${styles.returnVal} ${ret != null && ret >= 0 ? "positive" : ret != null && ret < 0 ? "negative" : ""}`}>
                                      {ret != null ? `${ret}%` : "—"}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ========== COMPARE TAB ========== */}
      {activeTab === "compare" && (
        <div className={styles.compareSection}>
          {/* Fund Selector */}
          <div className={styles.compareSelector}>
            <h2 className={styles.compareSelectorTitle}>
              Select Funds to Compare
              <span className={styles.compareLimit}>{compareList.length} / 4</span>
            </h2>

            {/* Selected Funds Pills */}
            {compareList.length > 0 && (
              <div className={styles.selectedFunds}>
                {compareList.map((fund) => (
                  <div key={fund.slug} className={styles.selectedPill}>
                    <span className={styles.selectedPillName}>{fund.fund_name}</span>
                    <button className={styles.selectedPillRemove} onClick={() => removeFromCompare(fund.slug)}>✕</button>
                  </div>
                ))}
              </div>
            )}

            {/* Search to add */}
            {compareList.length < 4 && (
              <div className={styles.compareSearchBox}>
                <span className={styles.searchIcon}>🔍</span>
                <input
                  type="text"
                  placeholder="Search to add a fund..."
                  className={styles.searchInput}
                  value={compareSearch}
                  onChange={(e) => setCompareSearch(e.target.value)}
                />
              </div>
            )}

            {/* Search results dropdown */}
            {compareResults.length > 0 && (
              <div className={styles.compareDropdown}>
                {compareResults.map((fund) => (
                  <button key={fund.slug} className={styles.compareDropdownItem} onClick={() => addToCompare(fund)}>
                    <div>
                      <div className={styles.compareDropdownName}>{fund.fund_name}</div>
                      <div className={styles.compareDropdownMeta}>{fund.amc} • {fund.category || "—"}</div>
                    </div>
                    <span className={styles.compareDropdownAdd}>+ Add</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Comparison Table */}
          {compareList.length >= 2 ? (
            <div className={styles.compareTableWrap}>
              <table className={styles.compareTable}>
                <thead>
                  <tr>
                    <th className={styles.compareRowLabel}></th>
                    {compareList.map((fund) => (
                      <th key={fund.slug} className={styles.compareFundHeader}>
                        <Link href={`/fund/${fund.slug}`} className={styles.compareFundLink}>
                          <span className={styles.compareFundAmc}>{fund.amc}</span>
                          <span className={styles.compareFundName}>{fund.fund_name}</span>
                        </Link>
                        <button className={styles.compareRemoveBtn} onClick={() => removeFromCompare(fund.slug)}>✕</button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className={styles.compareRowLabel}>Category</td>
                    {compareList.map((f) => <td key={f.slug} className={styles.compareCell}>{f.category || "—"}</td>)}
                  </tr>
                  <tr>
                    <td className={styles.compareRowLabel}>Risk</td>
                    {compareList.map((f) => (
                      <td key={f.slug} className={styles.compareCell}>
                        <span style={{ color: getRiskColor(f.risk_level) }}>{f.risk_level || "—"}</span>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className={styles.compareRowLabel}>NAV</td>
                    {compareList.map((f) => (
                      <td key={f.slug} className={styles.compareCell}>
                        {navMap[f.slug]?.nav != null
                          ? `₹${Number(navMap[f.slug].nav).toFixed(2)}`
                          : f.nav != null ? `₹${Number(f.nav).toFixed(2)}` : "—"}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className={styles.compareRowLabel}>AUM</td>
                    {compareList.map((f) => <td key={f.slug} className={styles.compareCell}>{formatAUM(f.aum_crores)}</td>)}
                  </tr>
                  <tr>
                    <td className={styles.compareRowLabel}>Expense Ratio</td>
                    {compareList.map((f) => (
                      <td key={f.slug} className={styles.compareCell}>
                        {f.expense_ratio != null ? `${f.expense_ratio}%` : "—"}
                      </td>
                    ))}
                  </tr>

                  {/* Returns Section */}
                  <tr className={styles.compareSectionRow}>
                    <td colSpan={compareList.length + 1} className={styles.compareSectionLabel}>Returns</td>
                  </tr>
                  {["1M", "3M", "6M", "1Y", "3Y", "5Y", "SI"].map((period) => {
                    const vals = compareList.map((f) => getReturn(f, period));
                    if (vals.every((v) => v == null)) return null;
                    const best = Math.max(...vals.filter((v) => v != null));
                    return (
                      <tr key={period}>
                        <td className={styles.compareRowLabel}>{period}</td>
                        {compareList.map((f, i) => {
                          const ret = vals[i];
                          const isBest = ret != null && ret === best && vals.filter(v => v === best).length === 1;
                          return (
                            <td key={f.slug} className={`${styles.compareCell} ${isBest ? styles.compareBest : ""}`}>
                              <span className={ret != null && ret >= 0 ? styles.returnPositive : ret != null && ret < 0 ? styles.returnNegative : ""}>
                                {ret != null ? `${ret}%` : "—"}
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}

                  {/* Holdings Section */}
                  <tr className={styles.compareSectionRow}>
                    <td colSpan={compareList.length + 1} className={styles.compareSectionLabel}>Top Holdings</td>
                  </tr>
                  {[0, 1, 2, 3, 4].map((idx) => {
                    const holdings = compareList.map((f) => f.holdings?.[idx]);
                    if (holdings.every((h) => !h)) return null;
                    return (
                      <tr key={`holding-${idx}`}>
                        <td className={styles.compareRowLabel}>#{idx + 1}</td>
                        {compareList.map((f) => {
                          const h = f.holdings?.[idx];
                          return (
                            <td key={f.slug} className={styles.compareCell}>
                              {h ? (
                                <div className={styles.holdingCell}>
                                  <span className={styles.holdingName}>{h.stock_name || h.name}</span>
                                  {h.percentage != null && <span className={styles.holdingPct}>{h.percentage}%</span>}
                                </div>
                              ) : "—"}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : compareList.length === 1 ? (
            <div className={styles.compareEmpty}>
              <span className={styles.compareEmptyIcon}>➕</span>
              <p>Add one more fund to start comparing</p>
            </div>
          ) : (
            <div className={styles.compareEmpty}>
              <span className={styles.compareEmptyIcon}>⚖️</span>
              <h3>Compare Mutual Funds</h3>
              <p>Search and select 2–4 funds above to see a side-by-side comparison</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  return (
    <Suspense>
      <HomeContent />
    </Suspense>
  );
}
