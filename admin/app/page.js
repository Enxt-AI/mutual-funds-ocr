"use client";

import { useState, useEffect, useCallback } from "react";
import styles from "./page.module.css";

function slugify(text) {
    return text
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, "")
        .replace(/\s+/g, "-")
        .replace(/-+/g, "-")
        .replace(/^-|-$/g, "")
        .slice(0, 60);
}

function formatDate(iso) {
    try {
        return new Date(iso).toLocaleDateString("en-IN", {
            day: "numeric", month: "short", year: "numeric",
            hour: "2-digit", minute: "2-digit"
        });
    } catch { return iso; }
}

const TABS = [
    { id: "factsheet", label: "Upload Factsheet", icon: "📄" },
    { id: "pipeline", label: "Scrape & Extract", icon: "🔄" },
    { id: "nse", label: "NSE Index Data", icon: "📈" },
];

export default function AdminPage() {
    const [activeTab, setActiveTab] = useState("factsheet");

    // AMC state
    const [amcs, setAmcs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState(null);

    // Upload state
    const [file, setFile] = useState(null);
    const [amcName, setAmcName] = useState("");
    const [extracting, setExtracting] = useState(false);
    const [status, setStatus] = useState(null);
    const [dragOver, setDragOver] = useState(false);

    // Pipeline state
    const [pipelineAmcs, setPipelineAmcs] = useState([]);
    const [pipelineAmcsLoading, setPipelineAmcsLoading] = useState(false);
    const [selectedAmcs, setSelectedAmcs] = useState(new Set());
    const [pipelineRunning, setPipelineRunning] = useState(false);
    const [pipelineStatus, setPipelineStatus] = useState(null);
    const [pipelineLogs, setPipelineLogs] = useState([]);
    const [pipelineEvents, setPipelineEvents] = useState([]);
    const [pipelineScrapeOnly, setPipelineScrapeOnly] = useState(false);

    // NSE processing state
    const [nseProcessing, setNseProcessing] = useState(false);
    const [nseStatus, setNseStatus] = useState(null);
    const [nseCsvFiles, setNseCsvFiles] = useState([]);

    // Fetch existing AMCs
    const fetchAmcs = useCallback(() => {
        fetch("/api/amcs")
            .then(res => res.json())
            .then(data => { setAmcs(data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    useEffect(() => { fetchAmcs(); }, [fetchAmcs]);

    // Fetch available pipeline AMCs when tab is switched to pipeline
    useEffect(() => {
        if (activeTab === "pipeline" && pipelineAmcs.length === 0 && !pipelineAmcsLoading) {
            setPipelineAmcsLoading(true);
            fetch("/api/pipeline?list=true")
                .then(res => res.json())
                .then(data => {
                    if (!data.error) {
                        const amcList = Object.entries(data).map(([slug, info]) => ({
                            slug,
                            displayName: info.display_name,
                            spider: info.spider,
                        }));
                        amcList.sort((a, b) => a.displayName.localeCompare(b.displayName));
                        setPipelineAmcs(amcList);
                    }
                })
                .catch(() => { })
                .finally(() => setPipelineAmcsLoading(false));
        }
    }, [activeTab, pipelineAmcs.length, pipelineAmcsLoading]);

    // Pipeline status polling
    useEffect(() => {
        if (!pipelineRunning) return;
        const interval = setInterval(async () => {
            try {
                const res = await fetch("/api/pipeline");
                const data = await res.json();
                setPipelineStatus(data);
                setPipelineLogs(data.logs || []);
                setPipelineEvents(data.events || []);
                if (data.status === "done" || data.status === "failed") {
                    setPipelineRunning(false);
                    fetchAmcs();
                }
            } catch { }
        }, 2500);
        return () => clearInterval(interval);
    }, [pipelineRunning, fetchAmcs]);

    // Start pipeline
    const handleStartPipeline = async () => {
        if (selectedAmcs.size === 0) return;
        setPipelineRunning(true);
        setPipelineStatus(null);
        setPipelineLogs([]);
        setPipelineEvents([]);
        try {
            const amcs = selectedAmcs.size === pipelineAmcs.length ? "all" : [...selectedAmcs];
            const res = await fetch("/api/pipeline", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ amcs, scrapeOnly: pipelineScrapeOnly }),
            });
            const data = await res.json();
            if (!res.ok) {
                setPipelineRunning(false);
                setPipelineStatus({ status: "failed", logs: [data.error || "Failed to start pipeline"] });
            }
        } catch (e) {
            setPipelineRunning(false);
            setPipelineStatus({ status: "failed", logs: [e.message] });
        }
    };

    const toggleAmc = (slug) => {
        setSelectedAmcs(prev => {
            const next = new Set(prev);
            if (next.has(slug)) next.delete(slug);
            else next.add(slug);
            return next;
        });
    };

    const selectAllAmcs = () => setSelectedAmcs(new Set(pipelineAmcs.map(a => a.slug)));
    const deselectAllAmcs = () => setSelectedAmcs(new Set());

    // Delete an AMC
    const handleDeleteAmc = async (slug) => {
        if (!window.confirm(`Are you sure you want to delete "${slug}"? This will permanently remove it from S3 storage.`)) {
            return;
        }
        setDeleting(slug);
        try {
            const res = await fetch("/api/amcs/delete", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ slug }),
            });
            const data = await res.json();
            if (res.ok && data.success) {
                setAmcs(prev => prev.filter(a => a.slug !== slug));
            } else {
                alert(data.error || "Failed to delete AMC");
            }
        } catch (e) {
            alert("Network error: " + e.message);
        } finally {
            setDeleting(null);
        }
    };

    // Handle file drop/select
    const handleFile = (f) => {
        if (f && f.name.endsWith(".pdf")) {
            setFile(f);
            if (!amcName) {
                const name = f.name
                    .replace(/\.pdf$/i, "")
                    .replace(/[-_]+/g, " ")
                    .replace(/factsheet|latest|nov|dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|\d{4}/gi, "")
                    .replace(/\s+/g, " ")
                    .trim();
                setAmcName(name);
            }
            setStatus(null);
        } else {
            setStatus({ type: "error", message: "Please select a PDF file" });
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        handleFile(e.dataTransfer.files[0]);
    };

    // Upload and extract (background with polling)
    const handleExtract = async () => {
        if (!file || !amcName.trim()) {
            setStatus({ type: "error", message: "Please select a PDF and enter an AMC name" });
            return;
        }

        const currentSlug = slugify(amcName);
        setExtracting(true);
        setStatus({ type: "info", message: "Uploading PDF..." });

        try {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("amc", currentSlug);

            const res = await fetch("/api/extract", { method: "POST", body: formData });
            const data = await res.json();

            if (!res.ok) {
                setStatus({ type: "error", message: data.error || "Upload failed" });
                setExtracting(false);
                return;
            }

            setStatus({ type: "info", message: "Extraction started... polling for updates" });

            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch(`/api/extract?amc=${currentSlug}`);
                    const statusData = await statusRes.json();

                    if (statusData.status === "extracting") {
                        setStatus({ type: "info", message: `⏳ Extracting "${currentSlug}"...`, details: statusData.logs });
                    } else if (statusData.status === "done") {
                        clearInterval(pollInterval);
                        setStatus({ type: "success", message: `✅ Extracted ${statusData.schemes} schemes from "${statusData.amc}"`, details: statusData.logs });
                        setFile(null);
                        setAmcName("");
                        setExtracting(false);
                        fetchAmcs();
                    } else if (statusData.status === "failed") {
                        clearInterval(pollInterval);
                        setStatus({ type: "error", message: `❌ Extraction failed (exit code: ${statusData.exitCode})`, details: statusData.logs });
                        setExtracting(false);
                    }
                } catch { }
            }, 3000);
        } catch (e) {
            setStatus({ type: "error", message: e.message || "Network error" });
            setExtracting(false);
        }
    };

    const slug = slugify(amcName);

    return (
        <div className={styles.layout}>
            {/* Sidebar */}
            <aside className={styles.sidebar}>
                <div className={styles.sidebarHeader}>
                    <span className={styles.sidebarLogo}>📊</span>
                    <span className={styles.sidebarTitle}>Admin</span>
                </div>
                <nav className={styles.sidebarNav}>
                    {TABS.map(tab => (
                        <button
                            key={tab.id}
                            className={`${styles.sidebarItem} ${activeTab === tab.id ? styles.sidebarItemActive : ""}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            <span className={styles.sidebarIcon}>{tab.icon}</span>
                            <span>{tab.label}</span>
                        </button>
                    ))}
                </nav>
                <div className={styles.sidebarFooter}>
                    <div className={styles.sidebarStat}>
                        <span>{amcs.length}</span> AMCs extracted
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className={styles.main}>
                {/* ========== FACTSHEET TAB ========== */}
                {activeTab === "factsheet" && (
                    <>
                        <div className={styles.pageHeader}>
                            <h1 className={styles.pageTitle}>Upload Factsheet</h1>
                            <p className={styles.pageSubtitle}>Upload AMC factsheet PDFs for automated data extraction</p>
                        </div>

                        <div className={styles.uploadCard}>
                            {/* Drop Zone */}
                            <div
                                className={`${styles.dropZone} ${dragOver ? styles.dropZoneActive : ""} ${file ? styles.dropZoneHasFile : ""}`}
                                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={handleDrop}
                                onClick={() => document.getElementById("pdf-input").click()}
                            >
                                <input
                                    id="pdf-input"
                                    type="file"
                                    accept=".pdf"
                                    style={{ display: "none" }}
                                    onChange={(e) => handleFile(e.target.files[0])}
                                />
                                {file ? (
                                    <div className={styles.fileInfo}>
                                        <span className={styles.fileIcon}>📄</span>
                                        <div>
                                            <div className={styles.fileName}>{file.name}</div>
                                            <div className={styles.fileSize}>{(file.size / 1024 / 1024).toFixed(1)} MB</div>
                                        </div>
                                        <button className={styles.removeFile} onClick={(e) => { e.stopPropagation(); setFile(null); }}>✕</button>
                                    </div>
                                ) : (
                                    <div className={styles.dropPrompt}>
                                        <span className={styles.dropIcon}>📁</span>
                                        <p>Drag & drop a PDF here, or click to browse</p>
                                        <span className={styles.dropHint}>Only .pdf files accepted</span>
                                    </div>
                                )}
                            </div>

                            {/* AMC Name */}
                            <div className={styles.inputGroup}>
                                <label className={styles.inputLabel}>AMC Name</label>
                                <input
                                    type="text"
                                    className={styles.textInput}
                                    placeholder="e.g. HDFC Mutual Fund, Axis, SBI..."
                                    value={amcName}
                                    onChange={(e) => setAmcName(e.target.value)}
                                    disabled={extracting}
                                />
                                {slug && <span className={styles.slugPreview}>Slug: <strong>{slug}</strong></span>}
                            </div>

                            {/* Extract Button */}
                            <button className={styles.extractBtn} onClick={handleExtract} disabled={extracting || !file || !amcName.trim()}>
                                {extracting ? (
                                    <><span className={styles.spinner} /> Extracting... (this may take a few minutes)</>
                                ) : (
                                    <>🚀 Upload & Extract</>
                                )}
                            </button>

                            {/* Status */}
                            {status && (
                                <div className={`${styles.statusBox} ${styles[`status_${status.type}`]}`}>
                                    <p className={styles.statusMessage}>{status.message}</p>
                                    {status.details && status.details.length > 0 && (
                                        <details className={styles.logDetails}>
                                            <summary>Extraction logs ({status.details.length} lines)</summary>
                                            <pre className={styles.logPre}>{status.details.join("\n")}</pre>
                                        </details>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Existing AMCs */}
                        <div className={styles.amcListCard}>
                            <h2 className={styles.cardTitle}>
                                Extracted AMCs
                                <span className={styles.amcCount}>{amcs.length}</span>
                            </h2>
                            {loading ? (
                                <div className={styles.loadingText}>Loading...</div>
                            ) : amcs.length === 0 ? (
                                <div className={styles.emptyText}>No extracted data yet. Upload a factsheet to get started!</div>
                            ) : (
                                <div className={styles.amcGrid}>
                                    {amcs.map((amc) => (
                                        <div key={amc.slug} className={styles.amcItem}>
                                            <div className={styles.amcItemHeader}>
                                                <span className={styles.amcSlug}>{amc.slug}</span>
                                                <div className={styles.amcHeaderRight}>
                                                    <span className={styles.amcSchemes}>{amc.schemes} schemes</span>
                                                    <button
                                                        className={styles.deleteBtn}
                                                        title={`Delete ${amc.slug}`}
                                                        disabled={deleting === amc.slug}
                                                        onClick={() => handleDeleteAmc(amc.slug)}
                                                    >
                                                        {deleting === amc.slug ? <span className={styles.deleteSpinner} /> : "🗑️"}
                                                    </button>
                                                </div>
                                            </div>
                                            {amc.name && <div className={styles.amcFullName}>{amc.name}</div>}
                                            <div className={styles.amcMeta}>
                                                <span>{amc.sizeKB} KB</span>
                                                <span>{formatDate(amc.lastModified)}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </>
                )}

                {/* ========== PIPELINE TAB ========== */}
                {activeTab === "pipeline" && (
                    <>
                        <div className={styles.pageHeader}>
                            <h1 className={styles.pageTitle}>Scrape & Extract</h1>
                            <p className={styles.pageSubtitle}>Download factsheets via Scrapy &amp; extract data with Gemini OCR</p>
                        </div>

                        <div className={styles.uploadCard}>
                            {/* Mode Toggle */}
                            <div className={styles.pipelineToggle}>
                                <label className={styles.toggleLabel}>
                                    <input
                                        type="checkbox"
                                        checked={pipelineScrapeOnly}
                                        onChange={() => setPipelineScrapeOnly(p => !p)}
                                        disabled={pipelineRunning}
                                    />
                                    <span>Skip OCR</span>
                                    <span className={styles.toggleHint}>
                                        {pipelineScrapeOnly ? "Download PDFs only — no OCR or S3 upload" : "Download → Gemini OCR → Save JSON → Upload to S3"}
                                    </span>
                                </label>
                            </div>

                            {/* AMC Selection */}
                            <div className={styles.amcSelection}>
                                <div className={styles.amcSelectionHeader}>
                                    <span className={styles.amcSelectionTitle}>
                                        Select AMCs ({selectedAmcs.size}/{pipelineAmcs.length})
                                    </span>
                                    <div className={styles.amcSelectionActions}>
                                        <button className={styles.linkBtn} onClick={selectAllAmcs} disabled={pipelineRunning}>Select All</button>
                                        <button className={styles.linkBtn} onClick={deselectAllAmcs} disabled={pipelineRunning}>Deselect All</button>
                                    </div>
                                </div>

                                {pipelineAmcsLoading ? (
                                    <div className={styles.loadingText}>Loading AMC list...</div>
                                ) : (
                                    <div className={styles.amcChecklist}>
                                        {pipelineAmcs.map(amc => {
                                            const amcEvent = pipelineEvents.filter(e => e.amc === amc.slug).slice(-1)[0];
                                            const statusEmoji = amcEvent
                                                ? amcEvent.event === "amc_done"
                                                    ? amcEvent.status === "done" || amcEvent.status === "scraped" ? "✅" : "❌"
                                                    : amcEvent.event === "amc_start" || amcEvent.event === "step_start" ? "⏳" : ""
                                                : "";
                                            return (
                                                <label key={amc.slug} className={styles.amcCheckItem}>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedAmcs.has(amc.slug)}
                                                        onChange={() => toggleAmc(amc.slug)}
                                                        disabled={pipelineRunning}
                                                    />
                                                    <span className={styles.amcCheckName}>{amc.displayName}</span>
                                                    {statusEmoji && <span className={styles.amcCheckStatus}>{statusEmoji}</span>}
                                                </label>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            {/* Run Pipeline Button */}
                            <button
                                className={styles.extractBtn}
                                style={{ background: "linear-gradient(135deg, #f59e0b, #f97316)" }}
                                disabled={pipelineRunning || selectedAmcs.size === 0}
                                onClick={handleStartPipeline}
                            >
                                {pipelineRunning ? (
                                    <><span className={styles.spinner} /> Pipeline Running...</>
                                ) : (
                                    <>🚀 {pipelineScrapeOnly ? "Download Factsheets" : "Run Full Pipeline"} ({selectedAmcs.size} AMC{selectedAmcs.size !== 1 ? "s" : ""})</>
                                )}
                            </button>

                            {/* Progress */}
                            {pipelineStatus && pipelineStatus.status !== "idle" && (
                                <div className={styles.pipelineProgress}>
                                    <div className={styles.progressHeader}>
                                        <span className={styles.progressLabel}>
                                            {pipelineStatus.status === "running" ? "⏳ Running" : pipelineStatus.status === "done" ? "✅ Completed" : "❌ Failed"}
                                        </span>
                                        {pipelineStatus.progress && pipelineStatus.progress.total > 0 && (
                                            <span className={styles.progressCount}>
                                                {(pipelineStatus.progress.done || 0) + (pipelineStatus.progress.failed || 0)} / {pipelineStatus.progress.total}
                                            </span>
                                        )}
                                    </div>
                                    {pipelineStatus.progress && pipelineStatus.progress.total > 0 && (
                                        <div className={styles.progressBar}>
                                            <div
                                                className={styles.progressBarFill}
                                                style={{
                                                    width: `${(((pipelineStatus.progress.done || 0) + (pipelineStatus.progress.failed || 0)) / pipelineStatus.progress.total) * 100}%`,
                                                }}
                                            />
                                        </div>
                                    )}
                                    {pipelineStatus.currentAmc && pipelineStatus.status === "running" && (
                                        <div className={styles.currentAmcInfo}>
                                            Processing: <strong>{pipelineStatus.currentAmc}</strong>
                                            {pipelineStatus.currentStep && (
                                                <span className={styles.stepBadge}>{pipelineStatus.currentStep}</span>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Logs */}
                            {pipelineLogs.length > 0 && (
                                <details className={styles.logDetails} open={pipelineRunning}>
                                    <summary>Pipeline logs ({pipelineLogs.length} lines)</summary>
                                    <pre className={styles.logPre}>{pipelineLogs.join("\n")}</pre>
                                </details>
                            )}
                        </div>
                    </>
                )}

                {/* ========== NSE TAB ========== */}
                {activeTab === "nse" && (
                    <>
                        <div className={styles.pageHeader}>
                            <h1 className={styles.pageTitle}>NSE Index Data</h1>
                            <p className={styles.pageSubtitle}>Upload NSE index CSVs and process them into benchmark data</p>
                        </div>

                        <div className={styles.uploadCard}>
                            {/* CSV Upload */}
                            <div
                                className={styles.dropZone}
                                style={{ marginBottom: 16 }}
                                onClick={() => document.getElementById("csv-input").click()}
                            >
                                <input
                                    id="csv-input"
                                    type="file"
                                    accept=".csv"
                                    multiple
                                    style={{ display: "none" }}
                                    onChange={(e) => {
                                        const files = Array.from(e.target.files || []);
                                        if (files.length > 0) setNseCsvFiles(prev => [...prev, ...files]);
                                        e.target.value = "";
                                    }}
                                />
                                <div className={styles.dropPrompt}>
                                    <span className={styles.dropIcon}>📁</span>
                                    <p>Click to select CSV files (NIFTY_50, SENSEX, etc.)</p>
                                    <span className={styles.dropHint}>Multiple .csv files accepted</span>
                                </div>
                            </div>

                            {/* Selected files */}
                            {nseCsvFiles.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
                                        Selected files ({nseCsvFiles.length}):
                                    </div>
                                    {nseCsvFiles.map((f, i) => (
                                        <div key={i} className={styles.csvFileItem}>
                                            <span>📄</span>
                                            <span style={{ flex: 1, color: "var(--text-primary)" }}>{f.name}</span>
                                            <span style={{ color: "var(--text-muted)", fontSize: 11 }}>{(f.size / 1024).toFixed(0)} KB</span>
                                            <button
                                                onClick={() => setNseCsvFiles(prev => prev.filter((_, j) => j !== i))}
                                                style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: 14 }}
                                            >✕</button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <button
                                className={styles.extractBtn}
                                style={{ background: "linear-gradient(135deg, #10b981, #34d399)" }}
                                disabled={nseProcessing}
                                onClick={async () => {
                                    setNseProcessing(true);
                                    setNseStatus({ type: "info", message: nseCsvFiles.length > 0 ? "Uploading CSVs & processing..." : "Processing existing data..." });
                                    try {
                                        const formData = new FormData();
                                        for (const f of nseCsvFiles) formData.append("files", f);
                                        const res = await fetch("/api/nse", { method: "POST", body: formData });
                                        const data = await res.json();
                                        if (data.success) {
                                            const uploaded = data.uploadedFiles?.length > 0 ? ` (uploaded ${data.uploadedFiles.length} files)` : "";
                                            setNseStatus({ type: "success", message: `✅ NSE index data processed${uploaded}`, details: data.logs });
                                            setNseCsvFiles([]);
                                        } else {
                                            setNseStatus({ type: "error", message: data.error || "Processing failed", details: data.logs });
                                        }
                                    } catch (e) {
                                        setNseStatus({ type: "error", message: e.message });
                                    } finally {
                                        setNseProcessing(false);
                                    }
                                }}
                            >
                                {nseProcessing ? (
                                    <><span className={styles.spinner} /> Processing...</>
                                ) : nseCsvFiles.length > 0 ? (
                                    <>📈 Upload & Process ({nseCsvFiles.length} file{nseCsvFiles.length > 1 ? "s" : ""})</>
                                ) : (
                                    <>📈 Process Existing Data</>
                                )}
                            </button>

                            {nseStatus && (
                                <div className={`${styles.statusBox} ${styles[`status_${nseStatus.type}`]}`}>
                                    <p className={styles.statusMessage}>{nseStatus.message}</p>
                                    {nseStatus.details && nseStatus.details.length > 0 && (
                                        <details className={styles.logDetails}>
                                            <summary>Logs ({nseStatus.details.length} lines)</summary>
                                            <pre className={styles.logPre}>{nseStatus.details.join("\n")}</pre>
                                        </details>
                                    )}
                                </div>
                            )}
                        </div>
                    </>
                )}
            </main>
        </div>
    );
}
