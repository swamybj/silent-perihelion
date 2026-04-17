/**
 * OptiGreeks — Options Trading Analysis Platform
 * Frontend Application Logic
 */

const API_BASE = window.location.origin + "/api";

// ── Plotly Theme ──────────────────────────────────────────────────────────
const PLOTLY_LAYOUT = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(13,18,40,0.4)",
    font: { family: "Inter, sans-serif", color: "#9aa5b4", size: 11 },
    margin: { t: 36, r: 20, b: 40, l: 55 },
    xaxis: {
        gridcolor: "rgba(255,255,255,0.04)",
        linecolor: "rgba(255,255,255,0.06)",
        zerolinecolor: "rgba(255,255,255,0.08)",
    },
    yaxis: {
        gridcolor: "rgba(255,255,255,0.04)",
        linecolor: "rgba(255,255,255,0.06)",
        zerolinecolor: "rgba(255,255,255,0.08)",
    },
    legend: { orientation: "h", y: -0.15, font: { size: 10 } },
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

// ── State ─────────────────────────────────────────────────────────────────
let tickers = [];
let strategies = [];
let appConfig = {};

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
    initTabs();
    initSliders();
    updateClock();
    setInterval(updateClock, 1000);

    await Promise.all([
        loadConfig(),
        loadTickers(),
        loadStrategies(),
    ]);

    populateTickerSelects();
    populateStrategySelects();
    populateYearsSelects();
    loadMarketOverview();
    loadTickerList();
});

function updateClock() {
    const el = document.getElementById("header-time");
    if (el) el.textContent = new Date().toLocaleString();
}

// ── Tab Navigation ────────────────────────────────────────────────────────
function initTabs() {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
        });
    });
}

// ── Sliders ───────────────────────────────────────────────────────────────
function initSliders() {
    const setupSlider = (sliderId, displayId) => {
        const slider = document.getElementById(sliderId);
        const display = document.getElementById(displayId);
        if (slider && display) {
            slider.addEventListener("input", () => {
                display.textContent = (slider.value / 100).toFixed(2);
            });
        }
    };
    setupSlider("strat-delta", "strat-delta-display");
    setupSlider("bt-delta", "bt-delta-display");
}

// ── API Helpers ───────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${path}`, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error(`API Error [${path}]:`, e);
        throw e;
    }
}

async function loadConfig() {
    try {
        appConfig = await apiFetch("/config");
        const rateEl = document.getElementById("header-rate");
        if (rateEl) rateEl.textContent = `Risk-Free Rate: ${appConfig.risk_free_rate}%`;
    } catch (e) {
        console.warn("Failed to load config:", e);
    }
}

async function loadTickers() {
    try {
        tickers = await apiFetch("/tickers");
    } catch (e) {
        console.warn("Failed to load tickers:", e);
        tickers = [];
    }
}

async function loadStrategies() {
    try {
        strategies = await apiFetch("/strategies");
    } catch (e) {
        console.warn("Failed to load strategies:", e);
        strategies = [];
    }
}

function populateTickerSelects() {
    const selects = ["dash-ticker-select", "strat-ticker", "bt-ticker", "dist-ticker", "ta-ticker", "edu-ticker"];
    selects.forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        const current = el.value;
        el.innerHTML = '<option value="">Select a ticker...</option>';
        tickers.forEach((t) => {
            const opt = document.createElement("option");
            opt.value = t.key;
            opt.textContent = `${t.key} — ${t.name}${t.section_1256 ? " §1256" : ""}`;
            el.appendChild(opt);
        });
        if (current) el.value = current;
    });
}

function populateStrategySelects() {
    const selects = ["strat-type", "bt-strategy", "edu-strategy"];
    selects.forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = "";
        strategies.forEach((s) => {
            const opt = document.createElement("option");
            opt.value = s.key;
            opt.textContent = s.name;
            el.appendChild(opt);
        });
    });
}

function populateYearsSelects() {
    const years = (appConfig.backtest_years_options || [1, 2, 3, 5, 7, 10]);
    const defaultYears = appConfig.backtest_default_years || 2;
    ["bt-years", "dist-years"].forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = "";
        years.forEach((y) => {
            const opt = document.createElement("option");
            opt.value = y;
            opt.textContent = `${y} Year${y > 1 ? "s" : ""}`;
            if (y === defaultYears) opt.selected = true;
            el.appendChild(opt);
        });
    });
}

// ── Strategy Logic Helpers ──────────────────────────────────────────────
function getStrategyRecommendation(type, val1, val2 = null) {
    if (type === 'RSI') {
        if (val1 > 70) return "Bearish: RSI Overbought (Suggest Bear Call Spread / Long Put)";
        if (val1 < 30) return "Bullish: RSI Oversold (Suggest Bull Put Spread / Long Call)";
        return "Neutral: Neutral RSI (Consider Iron Condor or Calendar Call/Put Spread)";
    }
    if (type === 'MACD') {
        if (val1 > 0) return "Bullish: Positive MACD (Suggest Bull Call Spread / Calendar Call Spread)";
        if (val1 < 0) return "Bearish: Negative MACD (Suggest Bear Put Spread / Calendar Put Spread)";
        return "Neutral: MACD Flat (Suggest Iron Condor / Butterfly)";
    }
    if (type === 'IV') {
        if (val2 > 75) return "High IV: Sell Premium (Iron Condor / Credit Spreads)";
        if (val2 < 25) return "Low IV: Buy Vol (Straddle / Strangle / Calendar Call/Put Spread)";
        return "Medium IV: Balanced Neutral Strategies (Iron Butterfly)";
    }
    if (type === 'SMA') {
        if (val1 > val2) return "Bullish Trend: Price Above SMA (Favor Bullish Spreads)";
        if (val1 < val2) return "Bearish Trend: Price Below SMA (Favor Bearish Spreads)";
        return "Neutral Trend";
    }
    return "";
}

// ═══ DASHBOARD ═══════════════════════════════════════════════════════════

async function loadMarketOverview() {
    const container = document.getElementById("market-cards");
    container.innerHTML = '<div class="loading-overlay"><div class="spinner spinner-lg"></div><div>Loading market data...</div></div>';

    const cards = [];
    for (const t of tickers) {
        try {
            const data = await apiFetch(`/market-data/${t.key}`);
            cards.push(data);
        } catch {
            cards.push({ symbol: t.key, name: t.name, current_price: null, error: true });
        }
    }

    container.innerHTML = cards.map((d) => {
        if (d.error || d.current_price === null) {
            return `
                <div class="market-card" onclick="selectDashTicker('${d.symbol}')">
                    <div class="market-card-symbol">${d.symbol}</div>
                    <div class="market-card-name">${d.name || ""}</div>
                    <div class="market-card-price" style="color: var(--text-muted)">—</div>
                </div>`;
        }
        const isUp = d.change >= 0;
        const badge1256 = d.section_1256 ? '<span class="badge badge-1256">§1256</span>' : '';
        return `
            <div class="market-card" onclick="selectDashTicker('${d.ticker_key}')">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:2px;">
                    <span class="market-card-symbol">${d.ticker_key}</span>
                    ${badge1256}
                </div>
                <div class="market-card-name">${d.name}</div>
                <div class="market-card-price">$${d.current_price.toLocaleString()}</div>
                <div class="market-card-change ${isUp ? "up" : "down"}">
                    ${isUp ? "▲" : "▼"} ${Math.abs(d.change).toFixed(2)} (${d.change_pct >= 0 ? "+" : ""}${d.change_pct.toFixed(2)}%)
                </div>
            </div>`;
    }).join("");
}

function selectDashTicker(key) {
    document.getElementById("dash-ticker-select").value = key;
    loadRecommendations();
}

async function loadRecommendations() {
    const ticker = document.getElementById("dash-ticker-select").value;
    if (!ticker) return;

    const container = document.getElementById("recommendations-container");
    container.innerHTML = '<div class="loading-overlay"><div class="spinner spinner-lg"></div><div>Analyzing market conditions...</div></div>';

    try {
        const data = await apiFetch(`/strategy/recommend/${ticker}`);

        const signalClass = data.composite_signal.signal.includes("BULL") ? "bullish"
            : data.composite_signal.signal.includes("BEAR") ? "bearish" : "neutral";

        let html = `
            <div class="signal-bar ${signalClass} mb-16">
                <strong>${data.symbol}</strong> @ $${data.current_price.toLocaleString()} &nbsp;|&nbsp;
                Signal: <span class="badge badge-${signalClass}">${data.composite_signal.signal}</span> &nbsp;|&nbsp;
                Score: ${data.composite_signal.score} &nbsp;|&nbsp;
                IV Percentile: ${data.iv_percentile}% &nbsp;|&nbsp;
                Hist. Vol: ${data.historical_vol}%
            </div>

            <div class="mb-16">
                <h4 class="mb-12">Signal Details</h4>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                    ${data.composite_signal.details.map((d) => {
                        const cls = d.includes("Bullish") ? "bullish" : d.includes("Bearish") ? "bearish" : "neutral";
                        return `<span class="badge badge-${cls}">${d}</span>`;
                    }).join("")}
                </div>
            </div>

            <h4 class="mb-12">Recommended Strategies</h4>
            <div class="grid-auto">`;

        data.recommendations.forEach((rec) => {
            html += `
                <div class="strategy-card" onclick="loadStrategyFromRec('${ticker}', '${rec.strategy}')">
                    <div class="strategy-card-header">
                        <span class="strategy-card-name">${rec.name}</span>
                        <span class="badge badge-${rec.confidence.toLowerCase()}">${rec.confidence}</span>
                    </div>
                    <div class="strategy-card-desc">${rec.description}</div>
                    <div class="strategy-card-reason">💡 ${rec.reason}</div>
                </div>`;
        });

        html += "</div>";
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-text" style="color: var(--loss)">Error: ${e.message}</div></div>`;
    }
}

function loadStrategyFromRec(ticker, strategy) {
    document.getElementById("strat-ticker").value = ticker;
    document.getElementById("strat-type").value = strategy;
    document.querySelector('[data-tab="strategy"]').click();
}

// ═══ STRATEGY BUILDER ════════════════════════════════════════════════════

async function analyzeStrategy() {
    const ticker = document.getElementById("strat-ticker").value;
    const stratType = document.getElementById("strat-type").value;
    if (!ticker || !stratType) return alert("Please select a ticker and strategy type.");

    const btn = document.getElementById("strat-analyze-btn");
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Analyzing...';

    const container = document.getElementById("strategy-results");
    container.innerHTML = '<div class="loading-overlay"><div class="spinner spinner-lg"></div><div>Calculating Greeks & payoff...</div></div>';

    try {
        const body = {
            ticker_key: ticker,
            strategy_type: stratType,
            front_dte: parseInt(document.getElementById("strat-front-dte").value) || 30,
            delta_target: parseInt(document.getElementById("strat-delta").value) / 100,
        };

        const backDte = document.getElementById("strat-back-dte").value;
        if (backDte) body.back_dte = parseInt(backDte);

        const strike = document.getElementById("strat-strike").value;
        if (strike) body.strike = parseFloat(strike);

        const iv = document.getElementById("strat-iv").value;
        if (iv) body.volatility = parseFloat(iv);

        const data = await apiFetch("/strategy/analyze", {
            method: "POST",
            body: JSON.stringify(body),
        });

        renderStrategyResults(data);
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-text" style="color:var(--loss)">Error: ${e.message}</div></div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = "🔍 Analyze Strategy";
    }
}

function renderStrategyResults(data) {
    const container = document.getElementById("strategy-results");

    const isCredit = data.is_credit;
    const premiumLabel = isCredit ? "Credit Received" : "Debit Paid";
    const premiumColor = isCredit ? "profit" : "loss";

    let html = `
        <div class="grid-4 mb-20">
            <div class="card metric">
                <div class="metric-value ${premiumColor}">$${Math.abs(data.net_premium).toFixed(2)}</div>
                <div class="metric-label">${premiumLabel}</div>
            </div>
            <div class="card metric">
                <div class="metric-value profit">$${data.max_profit.toFixed(2)}</div>
                <div class="metric-label">Max Profit</div>
            </div>
            <div class="card metric">
                <div class="metric-value loss">$${Math.abs(data.max_loss).toFixed(2)}</div>
                <div class="metric-label">Max Loss</div>
            </div>
            <div class="card metric">
                <div class="metric-value neutral">${data.breakevens.map(b => "$" + b.toFixed(0)).join(", ") || "N/A"}</div>
                <div class="metric-label">Breakeven</div>
            </div>
        </div>

        <div class="grid-2 mb-20">
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">📊</span> Payoff at Expiration</div>
                </div>
                <div class="chart-container" id="payoff-chart"></div>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">🎛️</span> Position Details</div>
                </div>

                <h4 class="mb-12">Legs</h4>
                ${data.legs.map(leg => `
                    <div class="leg-row">
                        <span class="leg-action ${leg.action}">${leg.action}</span>
                        <span>${leg.type.toUpperCase()}</span>
                        <span class="mono">K=${leg.strike.toFixed(0)}</span>
                        <span class="mono">${leg.dte} DTE</span>
                        <span class="mono" style="margin-left:auto">$${leg.premium.toFixed(2)}</span>
                    </div>
                `).join("")}

                <h4 class="mt-16 mb-12">Aggregate Greeks</h4>
                <div class="greeks-row">
                    <div class="greek-chip">
                        <span class="greek-chip-label">Delta</span>
                        <span class="greek-chip-value">${data.aggregate_greeks.delta.toFixed(4)}</span>
                    </div>
                    <div class="greek-chip">
                        <span class="greek-chip-label">Gamma</span>
                        <span class="greek-chip-value">${data.aggregate_greeks.gamma.toFixed(4)}</span>
                    </div>
                    <div class="greek-chip">
                        <span class="greek-chip-label">Theta</span>
                        <span class="greek-chip-value">${data.aggregate_greeks.theta.toFixed(4)}</span>
                    </div>
                    <div class="greek-chip">
                        <span class="greek-chip-label">Vega</span>
                        <span class="greek-chip-value">${data.aggregate_greeks.vega.toFixed(4)}</span>
                    </div>
                </div>

                <div class="mt-16">
                    <div style="display:flex; gap:8px; flex-wrap:wrap">
                        ${data.section_1256 ? '<span class="badge badge-1256">§1256 Eligible</span>' : ''}
                        <span class="badge badge-neutral">${data.strategy_info?.name || data.strategy_type}</span>
                    </div>
                    <div style="font-size:0.75rem; color:var(--text-muted); margin-top:8px">${data.tax_treatment}</div>
                </div>
            </div>
        </div>

        <div class="card mb-20">
            <div class="card-header">
                <div class="card-title"><span class="icon">🚪</span> Exit Strategy & Risk Management</div>
            </div>
            <div class="grid-2">
                <div class="exit-box">
                    <div class="exit-box-title">📈 Profit Target</div>
                    <div class="exit-box-item">${data.exit_strategy.profit_target}</div>
                </div>
                <div class="exit-box" style="border-left-color: var(--loss);">
                    <div class="exit-box-title" style="color: var(--loss);">📉 Stop Loss</div>
                    <div class="exit-box-item">${data.exit_strategy.stop_loss}</div>
                </div>
                <div class="exit-box" style="border-left-color: var(--accent-orange);">
                    <div class="exit-box-title" style="color: var(--accent-orange);">⏰ Time Exit</div>
                    <div class="exit-box-item">${data.exit_strategy.time_exit}</div>
                </div>
                <div class="exit-box" style="border-left-color: var(--accent-cyan);">
                    <div class="exit-box-title" style="color: var(--accent-cyan);">📅 Holding Period</div>
                    <div class="exit-box-item">${data.exit_strategy.holding_period}</div>
                </div>
            </div>
        </div>`;

    container.innerHTML = html;

    // Draw payoff chart
    const payoff = data.payoff_diagram;
    const colors = payoff.payoffs.map(v => v >= 0 ? "#00e676" : "#ff5252");

    Plotly.newPlot("payoff-chart", [{
        x: payoff.prices,
        y: payoff.payoffs,
        type: "scatter",
        mode: "lines",
        fill: "tozeroy",
        line: { color: "#3b82f6", width: 2 },
        fillcolor: "rgba(59,130,246,0.08)",
        name: "Payoff",
    }, {
        x: [data.underlying_price],
        y: [0],
        type: "scatter",
        mode: "markers+text",
        marker: { size: 10, color: "#f59e0b", symbol: "diamond" },
        text: [`Current: $${data.underlying_price}`],
        textposition: "top center",
        textfont: { size: 10, color: "#f59e0b" },
        name: "Current Price",
    }], {
        ...PLOTLY_LAYOUT,
        title: { text: "Profit/Loss at Expiration", font: { size: 13, color: "#e8eaed" } },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, title: "Underlying Price", type: "linear" },
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "P&L ($)" },
        shapes: [{
            type: "line", x0: payoff.prices[0], x1: payoff.prices[payoff.prices.length - 1],
            y0: 0, y1: 0, line: { color: "rgba(255,255,255,0.15)", width: 1, dash: "dot" },
        }],
    }, PLOTLY_CONFIG);
}

// ═══ BACKTEST ═════════════════════════════════════════════════════════════

async function runBacktest() {
    const ticker = document.getElementById("bt-ticker").value;
    const strategy = document.getElementById("bt-strategy").value;
    if (!ticker || !strategy) return alert("Select a ticker and strategy.");

    const btn = document.getElementById("bt-run-btn");
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Running backtest...';

    const container = document.getElementById("backtest-results");
    container.innerHTML = '<div class="loading-overlay"><div class="spinner spinner-lg"></div><div>Running historical simulation...</div></div>';

    try {
        const body = {
            ticker_key: ticker,
            strategy_type: strategy,
            years: parseInt(document.getElementById("bt-years").value) || 2,
            delta_target: parseInt(document.getElementById("bt-delta").value) / 100,
            front_dte: parseInt(document.getElementById("bt-front-dte").value) || 30,
            entry_interval: parseInt(document.getElementById("bt-interval").value) || 5,
            profit_target_pct: parseFloat(document.getElementById("bt-profit-target").value) || 50,
            stop_loss_pct: parseFloat(document.getElementById("bt-stop-loss").value) || 200,
        };

        const data = await apiFetch("/backtest", { method: "POST", body: JSON.stringify(body) });
        renderBacktestResults(data);
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-text" style="color:var(--loss)">Error: ${e.message}</div></div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = "🚀 Run Backtest";
    }
}

function renderBacktestResults(data) {
    const container = document.getElementById("backtest-results");

    if (data.total_trades === 0) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-text">No trades generated. Try different parameters.</div></div>`;
        return;
    }

    const pnlColor = data.total_pnl >= 0 ? "profit" : "loss";

    let html = `
        <div class="grid-4 mb-20">
            <div class="card metric">
                <div class="metric-value neutral">${data.total_trades}</div>
                <div class="metric-label">Total Trades</div>
            </div>
            <div class="card metric">
                <div class="metric-value profit">${data.win_rate}%</div>
                <div class="metric-label">Win Rate</div>
            </div>
            <div class="card metric">
                <div class="metric-value ${pnlColor}">$${data.total_pnl.toFixed(2)}</div>
                <div class="metric-label">Total P&L</div>
            </div>
            <div class="card metric">
                <div class="metric-value loss">$${data.max_drawdown.toFixed(2)}</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
        </div>

        <div class="grid-4 mb-20">
            <div class="card metric">
                <div class="metric-value neutral">$${data.average_pnl.toFixed(2)}</div>
                <div class="metric-label">Avg P&L / Trade</div>
            </div>
            <div class="card metric">
                <div class="metric-value profit">$${data.best_trade.toFixed(2)}</div>
                <div class="metric-label">Best Trade</div>
            </div>
            <div class="card metric">
                <div class="metric-value loss">$${data.worst_trade.toFixed(2)}</div>
                <div class="metric-label">Worst Trade</div>
            </div>
            <div class="card metric">
                <div class="metric-value neutral">${data.avg_holding_days} days</div>
                <div class="metric-label">Avg Hold</div>
            </div>
        </div>

        <div class="grid-3 mb-20">
            <div class="card metric">
                <div class="metric-value profit">${data.profit_target_exits}</div>
                <div class="metric-label">Profit Target Exits</div>
            </div>
            <div class="card metric">
                <div class="metric-value loss">${data.stop_loss_exits}</div>
                <div class="metric-label">Stop Loss Exits</div>
            </div>
            <div class="card metric">
                <div class="metric-value neutral">${data.expiration_exits}</div>
                <div class="metric-label">Expiration Exits</div>
            </div>
        </div>

        <div class="grid-2 mb-20">
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">📈</span> Equity Curve</div>
                </div>
                <div class="chart-container" id="equity-chart"></div>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">📊</span> P&L Distribution</div>
                </div>
                <div class="chart-container" id="pnl-dist-chart"></div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <div class="card-title"><span class="icon">📋</span> Trade Log (${data.trades.length} trades)</div>
            </div>
            <div style="overflow-x: auto;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>#</th><th>Entry</th><th>Exit</th><th>Entry $</th><th>Exit $</th>
                            <th>P&L</th><th>Days</th><th>Exit Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.trades.slice(0, 50).map((t, i) => `
                            <tr>
                                <td>${i + 1}</td>
                                <td class="mono">${t.entry_date}</td>
                                <td class="mono">${t.exit_date}</td>
                                <td class="mono">$${t.entry_price.toFixed(0)}</td>
                                <td class="mono">$${t.exit_price.toFixed(0)}</td>
                                <td class="mono" style="color: ${t.pnl >= 0 ? 'var(--profit)' : 'var(--loss)'}">
                                    ${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}
                                </td>
                                <td class="mono">${t.holding_days}</td>
                                <td><span class="badge badge-${
                                    t.exit_reason === 'profit_target' ? 'bullish' :
                                    t.exit_reason === 'stop_loss' ? 'bearish' : 'neutral'
                                }">${t.exit_reason.replace('_', ' ')}</span></td>
                            </tr>`).join("")}
                    </tbody>
                </table>
                ${data.trades.length > 50 ? `<div style="padding:12px; text-align:center; color:var(--text-muted); font-size:0.78rem">Showing 50 of ${data.trades.length} trades</div>` : ""}
            </div>
        </div>`;

    container.innerHTML = html;

    // Equity curve chart
    Plotly.newPlot("equity-chart", [{
        x: data.equity_dates,
        y: data.equity_curve,
        type: "scatter",
        mode: "lines",
        fill: "tozeroy",
        line: { color: data.total_pnl >= 0 ? "#00e676" : "#ff5252", width: 2 },
        fillcolor: data.total_pnl >= 0 ? "rgba(0,230,118,0.06)" : "rgba(255,82,82,0.06)",
        name: "Cumulative P&L",
    }], {
        ...PLOTLY_LAYOUT,
        title: { text: "Cumulative P&L", font: { size: 13, color: "#e8eaed" } },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, title: "Date", type: "date" },
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "P&L ($)" },
    }, PLOTLY_CONFIG);

    // P&L distribution chart
    const pnls = data.pnl_distribution.values;
    Plotly.newPlot("pnl-dist-chart", [{
        x: pnls,
        type: "histogram",
        marker: {
            color: pnls.map(v => v >= 0 ? "rgba(0,230,118,0.6)" : "rgba(255,82,82,0.6)"),
        },
        nbinsx: 20,
        name: "P&L",
    }], {
        ...PLOTLY_LAYOUT,
        title: { text: "P&L Distribution", font: { size: 13, color: "#e8eaed" } },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, title: "P&L ($)", type: "linear" },
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "Frequency" },
        bargap: 0.05,
    }, PLOTLY_CONFIG);
}

// ═══ DISTRIBUTION ═════════════════════════════════════════════════════════

async function loadDistribution() {
    const ticker = document.getElementById("dist-ticker").value;
    const years = document.getElementById("dist-years").value;
    if (!ticker) return alert("Select a ticker.");

    const container = document.getElementById("distribution-results");
    container.innerHTML = '<div class="loading-overlay"><div class="spinner spinner-lg"></div><div>Analyzing price distribution...</div></div>';

    try {
        const data = await apiFetch(`/distribution/${ticker}?years=${years}`);
        renderDistribution(data);
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-text" style="color:var(--loss)">Error: ${e.message}</div></div>`;
    }
}

function renderDistribution(data) {
    const container = document.getElementById("distribution-results");
    const s = data.statistics;
    const p = data.probabilities;
    const ex = data.extremes;

    let html = `
        <div class="grid-4 mb-20">
            <div class="card metric">
                <div class="metric-value neutral">${s.total_days}</div>
                <div class="metric-label">Trading Days</div>
            </div>
            <div class="card metric">
                <div class="metric-value ${s.mean_daily_return >= 0 ? 'profit' : 'loss'}">${s.mean_daily_return.toFixed(4)}%</div>
                <div class="metric-label">Mean Daily Return</div>
            </div>
            <div class="card metric">
                <div class="metric-value neutral">${s.annualized_vol.toFixed(1)}%</div>
                <div class="metric-label">Annualized Volatility</div>
            </div>
            <div class="card metric">
                <div class="metric-value neutral">${s.excess_kurtosis.toFixed(2)}</div>
                <div class="metric-label">Excess Kurtosis ${s.fat_tails === "Yes" ? "⚠️" : ""}</div>
            </div>
        </div>

        <div class="grid-2 mb-20">
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">📊</span> Daily Return Distribution (-5% to +5%)</div>
                </div>
                <div class="chart-container" id="dist-histogram-chart"></div>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">📈</span> Weekly Return Distribution</div>
                </div>
                <div class="chart-container" id="weekly-dist-chart"></div>
            </div>
        </div>

        <div class="grid-3 mb-20">
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">🎯</span> Directional Probability</div>
                </div>
                <div style="padding: 8px 0;">
                    <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:12px;">
                        <span style="color:var(--profit)">▲ Up: ${p.up_day}%</span>
                        <span style="color:var(--loss)">▼ Down: ${p.down_day}%</span>
                    </div>
                    <div style="height:8px; background:var(--bg-tertiary); border-radius:4px; overflow:hidden; display:flex;">
                        <div style="width:${p.up_day}%; background:var(--profit); height:100%;"></div>
                        <div style="width:${p.down_day}%; background:var(--loss); height:100%;"></div>
                    </div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">📐</span> Move Probabilities</div>
                </div>
                <table class="data-table">
                    <thead><tr><th>Move</th><th>Up</th><th>Down</th></tr></thead>
                    <tbody>
                        <tr><td>> 1%</td><td class="mono" style="color:var(--profit)">${p.up_more_than_1pct}%</td><td class="mono" style="color:var(--loss)">${p.down_more_than_1pct}%</td></tr>
                        <tr><td>> 2%</td><td class="mono" style="color:var(--profit)">${p.up_more_than_2pct}%</td><td class="mono" style="color:var(--loss)">${p.down_more_than_2pct}%</td></tr>
                        <tr><td>> 3%</td><td class="mono" style="color:var(--profit)">${p.up_more_than_3pct}%</td><td class="mono" style="color:var(--loss)">${p.down_more_than_3pct}%</td></tr>
                    </tbody>
                </table>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">🔥</span> Extremes</div>
                </div>
                <table class="data-table">
                    <tbody>
                        <tr><td>Max Daily Gain</td><td class="mono" style="color:var(--profit)">+${ex.max_daily_gain}%</td></tr>
                        <tr><td>Max Daily Loss</td><td class="mono" style="color:var(--loss)">${ex.max_daily_loss}%</td></tr>
                        <tr><td>Max Weekly Gain</td><td class="mono" style="color:var(--profit)">+${ex.max_weekly_gain || "N/A"}%</td></tr>
                        <tr><td>Max Weekly Loss</td><td class="mono" style="color:var(--loss)">${ex.max_weekly_loss || "N/A"}%</td></tr>
                        <tr><td>Skewness</td><td class="mono">${s.skewness}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <div class="card-title"><span class="icon">📋</span> Frequency Table (Daily -5% to +5%)</div>
            </div>
            <div style="overflow-x: auto;">
                <table class="data-table">
                    <thead><tr><th>Range</th><th>Count</th><th>Frequency</th><th>Bar</th></tr></thead>
                    <tbody>
                        ${data.daily.histogram.map(b => `
                            <tr>
                                <td class="mono">${b.label}</td>
                                <td class="mono">${b.count}</td>
                                <td class="mono">${b.frequency_pct}%</td>
                                <td><div style="height:6px; width:${Math.min(b.frequency_pct * 4, 100)}%; background: ${b.center >= 0 ? 'var(--profit)' : 'var(--loss)'}; border-radius:3px;"></div></td>
                            </tr>`).join("")}
                    </tbody>
                </table>
            </div>
        </div>`;

    container.innerHTML = html;

    // Daily histogram with normal fit overlay
    const d = data.daily;
    Plotly.newPlot("dist-histogram-chart", [{
        x: d.bin_centers,
        y: d.counts,
        type: "bar",
        marker: {
            color: d.bin_centers.map(v => v >= 0 ? "rgba(0,230,118,0.5)" : "rgba(255,82,82,0.5)"),
        },
        name: "Actual",
    }, {
        x: d.bin_centers,
        y: d.normal_fit,
        type: "scatter",
        mode: "lines",
        line: { color: "#3b82f6", width: 2, dash: "dot" },
        name: "Normal Distribution Fit",
    }], {
        ...PLOTLY_LAYOUT,
        title: { text: "Daily Return Distribution", font: { size: 13, color: "#e8eaed" } },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, title: "Daily Return (%)", type: "linear" },
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "Frequency" },
        bargap: 0.05,
    }, PLOTLY_CONFIG);

    // Weekly histogram
    const w = data.weekly;
    Plotly.newPlot("weekly-dist-chart", [{
        x: w.bin_centers,
        y: w.counts,
        type: "bar",
        marker: {
            color: w.bin_centers.map(v => v >= 0 ? "rgba(6,214,160,0.5)" : "rgba(236,72,153,0.5)"),
        },
        name: "Weekly Returns",
    }], {
        ...PLOTLY_LAYOUT,
        title: { text: "Weekly Return Distribution", font: { size: 13, color: "#e8eaed" } },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, title: "Weekly Return (%)", type: "linear" },
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "Frequency" },
        bargap: 0.05,
    }, PLOTLY_CONFIG);
}

// ═══ TECHNICAL ANALYSIS ══════════════════════════════════════════════════

async function loadTechnicalAnalysis() {
    const ticker = document.getElementById("ta-ticker").value;
    if (!ticker) return alert("Select a ticker.");

    const container = document.getElementById("ta-results");
    container.innerHTML = '<div class="loading-overlay"><div class="spinner spinner-lg"></div><div>Running technical analysis...</div></div>';

    try {
        const data = await apiFetch(`/technical-analysis/${ticker}`);
        renderTechnicalAnalysis(data);
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-text" style="color:var(--loss)">Error: ${e.message}</div></div>`;
    }
}

function renderTechnicalAnalysis(data) {
    const container = document.getElementById("ta-results");
    const signalClass = data.composite_signal.signal.includes("BULL") ? "bullish"
        : data.composite_signal.signal.includes("BEAR") ? "bearish" : "neutral";

    let html = `
        <div class="signal-bar ${signalClass} mb-16">
            <strong>${data.name || data.symbol}</strong> @ $${data.current_price.toLocaleString()} &nbsp;|&nbsp;
            Signal: <span class="badge badge-${signalClass}">${data.composite_signal.signal}</span> &nbsp;|&nbsp;
            Score: ${data.composite_signal.score}
        </div>

        <div class="grid-4 mb-20">
            <div class="card metric" title="${getStrategyRecommendation('RSI', data.rsi?.value)}">
                <div class="metric-value neutral">${data.rsi?.value || "—"}</div>
                <div class="metric-label">RSI (14) <span class="badge badge-${
                    data.rsi?.signal === "overbought" ? "bearish" :
                    data.rsi?.signal === "oversold" ? "bullish" : "neutral"
                }" style="margin-left:4px">${data.rsi?.signal || ""}</span></div>
                <div style="font-size:0.65rem; color:var(--text-muted); margin-top:4px;">💡 Strategy Tip: ${getStrategyRecommendation('RSI', data.rsi?.value).split(':')[0]}</div>
            </div>
            <div class="card metric">
                <div class="metric-value neutral">${data.atr?.value || "—"}</div>
                <div class="metric-label">ATR (14) — ${data.atr?.pct_of_price || "—"}% of price</div>
            </div>
            <div class="card metric" title="${getStrategyRecommendation('MACD', data.macd?.macd)}">
                <div class="metric-value ${data.macd?.signal_name === "bullish" ? "profit" : data.macd?.signal_name === "bearish" ? "loss" : "neutral"}">${data.macd?.macd || "—"}</div>
                <div class="metric-label">MACD <span class="badge badge-${
                    data.macd?.signal_name === "bullish" ? "bullish" : "bearish"
                }" style="margin-left:4px">${data.macd?.signal_name || ""}</span></div>
                <div style="font-size:0.65rem; color:var(--text-muted); margin-top:4px;">💡 Strategy Tip: ${getStrategyRecommendation('MACD', data.macd?.macd).split(':')[0]}</div>
            </div>
            <div class="card metric">
                <div class="metric-value neutral">${data.bollinger?.bandwidth || "—"}%</div>
                <div class="metric-label">Bollinger Bandwidth</div>
            </div>
        </div>

        <div class="grid-4 mb-20">
            <div class="card metric" title="${getStrategyRecommendation('IV', data.historical_iv?.current?.iv_30d, data.historical_iv?.percentile_30d)}">
                <div class="metric-value" style="color:var(--accent-cyan)">${data.historical_iv?.current?.iv_30d || "—"}%</div>
                <div class="metric-label">IV 30-Day</div>
                <div style="font-size:0.65rem; color:var(--text-muted); margin-top:4px;">💡 Strategy Tip: ${getStrategyRecommendation('IV', 0, data.historical_iv?.percentile_30d).split(':')[0]}</div>
            </div>
            <div class="card metric">
                <div class="metric-value" style="color:var(--accent-purple)">${data.historical_iv?.current?.iv_60d || "—"}%</div>
                <div class="metric-label">IV 60-Day</div>
            </div>
            <div class="card metric">
                <div class="metric-value" style="color:var(--accent-orange)">${data.historical_iv?.current?.iv_90d || "—"}%</div>
                <div class="metric-label">IV 90-Day</div>
            </div>
            <div class="card metric">
                <div class="metric-value neutral">${data.historical_iv?.percentile_30d != null ? data.historical_iv.percentile_30d + '%' : '—'}</div>
                <div class="metric-label">IV Percentile (30d)</div>
            </div>
        </div>

        <div class="grid-2 mb-20">
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">📊</span> Price Chart with SMA Overlays</div>
                </div>
                <div class="chart-container" id="ta-price-chart"></div>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">📉</span> RSI</div>
                </div>
                <div class="chart-container" id="ta-rsi-chart" style="min-height:200px"></div>
                <div class="card-header mt-16">
                    <div class="card-title"><span class="icon">📈</span> MACD</div>
                </div>
                <div class="chart-container" id="ta-macd-chart" style="min-height:200px"></div>
            </div>
        </div>

        <div class="card mb-20">
            <div class="card-header">
                <div class="card-title"><span class="icon">📉</span> Historical Implied Volatility (30 / 60 / 90 Day)</div>
            </div>
            <div class="chart-container" id="ta-iv-chart"></div>
        </div>

        <div class="grid-2 mb-20">
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">🎚️</span> SMA Levels</div>
                </div>
                <table class="data-table">
                    <thead><tr><th>Indicator</th><th>Value</th><th>Signal</th></tr></thead>
                    <tbody>
                        ${Object.keys(data.sma).filter(k => !k.includes("signal")).map(k => {
                            const sigKey = k + "_signal";
                            const sig = data.sma[sigKey] || "—";
                            return `<tr>
                                <td>${k.toUpperCase().replace("_", " ")}</td>
                                <td class="mono">$${data.sma[k] ? data.sma[k].toFixed(2) : "—"}</td>
                                <td><span class="badge badge-${sig === "above" ? "bullish" : sig === "below" ? "bearish" : "neutral"}">${sig}</span></td>
                            </tr>`;
                        }).join("")}
                        <tr><td>Bollinger Upper</td><td class="mono">$${data.bollinger?.upper || "—"}</td><td></td></tr>
                        <tr><td>Bollinger Lower</td><td class="mono">$${data.bollinger?.lower || "—"}</td><td></td></tr>
                    </tbody>
                </table>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span class="icon">📐</span> Fibonacci Levels (${data.fibonacci?.direction || ""})</div>
                </div>
                <table class="data-table">
                    <thead><tr><th>Level</th><th>Price</th></tr></thead>
                    <tbody>
                        ${data.fibonacci?.levels ? Object.entries(data.fibonacci.levels).map(([k, v]) =>
                            `<tr><td>${k}</td><td class="mono">$${v}</td></tr>`
                        ).join("") : "<tr><td colspan='2'>N/A</td></tr>"}
                        <tr style="border-top:2px solid var(--border)"><td>Swing High</td><td class="mono" style="color:var(--profit)">$${data.fibonacci?.swing_high || "—"}</td></tr>
                        <tr><td>Swing Low</td><td class="mono" style="color:var(--loss)">$${data.fibonacci?.swing_low || "—"}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <div class="card-title"><span class="icon">🔍</span> Signal Details</div>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:8px;">
                ${data.composite_signal.details.map(d => {
                    const cls = d.includes("Bullish") ? "bullish" : d.includes("Bearish") ? "bearish" : "neutral";
                    return `<span class="badge badge-${cls}">${d}</span>`;
                }).join("")}
            </div>
        </div>`;

    container.innerHTML = html;

    // ── Price chart with SMA overlays ──
    const ph = data.price_history;
    const priceTraces = [
        {
            x: ph.dates, y: ph.close, type: "scatter", mode: "lines",
            line: { color: "#e8eaed", width: 1.5 }, name: "Close",
            hovertemplate: "Date: %{x}<br>Price: $%{y:.2f}<extra></extra>",
        }
    ];

    const smaColors = { sma_20: "#3b82f6", sma_50: "#f59e0b", sma_200: "#ec4899" };
    ["sma_20", "sma_50", "sma_200"].forEach(key => {
        if (ph[key]) {
            priceTraces.push({
                x: ph.dates, y: ph[key], type: "scatter", mode: "lines",
                line: { color: smaColors[key], width: 1, dash: "dot" },
                name: key.toUpperCase().replace("_", " "),
                hovertemplate: `%{fullData.name}: $%{y:.2f}<br>Tip: ${key === 'sma_50' ? 'Trend Trigger' : 'Support/Resistance'}<extra></extra>`,
            });
        }
    });

    // Add Fibonacci levels as horizontal lines
    const fibShapes = [];
    if (data.fibonacci?.levels) {
        const fibColors = ["#8b5cf6", "#06d6a0", "#3b82f6", "#f59e0b", "#ec4899", "#ff5252", "#8b5cf6"];
        Object.values(data.fibonacci.levels).forEach((v, i) => {
            fibShapes.push({
                type: "line", x0: ph.dates[0], x1: ph.dates[ph.dates.length - 1],
                y0: v, y1: v, line: { color: fibColors[i % fibColors.length], width: 0.5, dash: "dash" },
            });
        });
    }

    Plotly.newPlot("ta-price-chart", priceTraces, {
        ...PLOTLY_LAYOUT,
        title: { text: `${data.name || data.symbol} — Price & SMA`, font: { size: 13, color: "#e8eaed" } },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, type: "date" },
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "Price ($)" },
        shapes: fibShapes,
    }, PLOTLY_CONFIG);

    // ── RSI chart ──
    const rsiDates = ph.dates.slice(ph.dates.length - data.rsi_history.length);
    Plotly.newPlot("ta-rsi-chart", [{
        x: rsiDates, y: data.rsi_history, type: "scatter", mode: "lines",
        line: { color: "#8b5cf6", width: 1.5 }, name: "RSI",
        customdata: data.rsi_history.map(v => getStrategyRecommendation('RSI', v)),
        hovertemplate: "Value: %{y:.2f}<br><b>%{customdata}</b><extra></extra>",
    }], {
        ...PLOTLY_LAYOUT,
        margin: { t: 10, r: 20, b: 30, l: 45 },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, type: "date" },
        yaxis: { ...PLOTLY_LAYOUT.yaxis, range: [0, 100] },
        shapes: [
            { type: "line", x0: rsiDates[0], x1: rsiDates[rsiDates.length - 1], y0: 70, y1: 70, line: { color: "rgba(255,82,82,0.3)", width: 1, dash: "dash" } },
            { type: "line", x0: rsiDates[0], x1: rsiDates[rsiDates.length - 1], y0: 30, y1: 30, line: { color: "rgba(0,230,118,0.3)", width: 1, dash: "dash" } },
        ],
    }, PLOTLY_CONFIG);

    // ── MACD chart ──
    const mh = data.macd_history;
    const macdDates = ph.dates.slice(ph.dates.length - mh.macd.length);
    Plotly.newPlot("ta-macd-chart", [
        { 
            x: macdDates, y: mh.macd, type: "scatter", mode: "lines", line: { color: "#3b82f6", width: 1.5 }, name: "MACD",
            customdata: mh.macd.map(v => getStrategyRecommendation('MACD', v)),
            hovertemplate: "MACD: %{y:.4f}<br><b>%{customdata}</b><extra></extra>",
        },
        { x: macdDates, y: mh.signal, type: "scatter", mode: "lines", line: { color: "#f59e0b", width: 1 }, name: "Signal" },
        {
            x: macdDates, y: mh.histogram, type: "bar",
            marker: { color: mh.histogram.map(v => v >= 0 ? "rgba(0,230,118,0.4)" : "rgba(255,82,82,0.4)") },
            name: "Histogram",
        },
    ], {
        ...PLOTLY_LAYOUT,
        margin: { t: 10, r: 20, b: 30, l: 45 },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, type: "date" },
    }, PLOTLY_CONFIG);

    // ── Historical IV chart (30/60/90 day) ──
    if (data.historical_iv?.history) {
        const ivH = data.historical_iv.history;
        const ivTraces = [];
        const ivConfig = [
            { key: "iv_30d", name: "30-Day IV", color: "#06d6a0", width: 2 },
            { key: "iv_60d", name: "60-Day IV", color: "#8b5cf6", width: 1.5 },
            { key: "iv_90d", name: "90-Day IV", color: "#f59e0b", width: 1.5 },
        ];
        
        // Use a 1-year window of IV 30d for percentile calc if possible, or just use the chart data range
        const ivValues = ivH.iv_30d || [];
        
        ivConfig.forEach(cfg => {
            if (ivH[cfg.key]) {
                const vals = ivH[cfg.key];
                const ivDates = ph.dates.slice(ph.dates.length - vals.length);
                
                ivTraces.push({
                    x: ivDates,
                    y: vals,
                    type: "scatter",
                    mode: "lines",
                    line: { color: cfg.color, width: cfg.width },
                    name: cfg.name,
                    customdata: vals.map((v, i) => {
                        // For IV percentile tip, we'll estimate percentile based on the chart's history
                        const history = ivH.iv_30d || [];
                        const lessThan = history.filter(h => h < v).length;
                        const pct = (lessThan / history.length) * 100;
                        return getStrategyRecommendation('IV', v, pct);
                    }),
                    hovertemplate: "%{fullData.name}: %{y:.2f}%<br><b>%{customdata}</b><extra></extra>",
                });
            }
        });

        Plotly.newPlot("ta-iv-chart", ivTraces, {
            ...PLOTLY_LAYOUT,
            title: { text: "Historical Implied Volatility (Annualized %)", font: { size: 13, color: "#e8eaed" } },
            xaxis: { ...PLOTLY_LAYOUT.xaxis, type: "date" },
            yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "Implied Volatility (%)", rangemode: "tozero" },
        }, PLOTLY_CONFIG);
    }
}

// ═══ EDUCATION HUB ═══════════════════════════════════════════════════════

async function renderEducationHub() {
    const stratKey = document.getElementById("edu-strategy").value;
    const tickerKey = document.getElementById("edu-ticker").value;
    const container = document.getElementById("education-results");

    if (!stratKey) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📚</div><div class="empty-state-text">Select a strategy to view its guide</div></div>`;
        return;
    }

    const strat = strategies.find(s => s.key === stratKey);
    const edu = strat?.education || {};

    let html = `
        <div class="card mb-20">
            <div class="card-header">
                <div class="card-title"><span class="icon">📖</span> Strategy Mechanics: ${strat.name}</div>
            </div>
            <div class="mb-16" style="color:var(--text-secondary); font-size:0.9rem;">
                ${strat.description} This is a <strong>${strat.direction}</strong> strategy.
            </div>
            <div class="grid-2">
                <div class="exit-box" style="border-left-color: var(--accent-cyan)">
                    <div class="exit-box-title" style="color:var(--accent-cyan)">Entry Criteria</div>
                    <div class="exit-box-item">${edu.entry_criteria || "Data unavailable."}</div>
                    <div class="exit-box-item"><strong>Best Environment:</strong> ${strat.best_when}</div>
                </div>
                <div class="exit-box" style="border-left-color: var(--accent-orange)">
                    <div class="exit-box-title" style="color:var(--accent-orange)">Greeks & Edge</div>
                    <div class="exit-box-item">${edu.greeks_impact || "Data unavailable."}</div>
                    <div class="exit-box-item"><strong>Win Probability:</strong> ${edu.win_probability || "Data unavailable."}</div>
                </div>
            </div>
        </div>
    `;

    if (tickerKey) {
        container.innerHTML = html + `<div class="loading-overlay"><div class="spinner"></div><div>Simulating live setup on ${tickerKey}...</div></div>`;
        try {
            const [data, recData] = await Promise.all([
                apiFetch("/strategy/analyze", {
                    method: "POST",
                    body: JSON.stringify({
                        ticker_key: tickerKey,
                        strategy_type: stratKey,
                        front_dte: 30, // Default theoretical setup
                        delta_target: 0.16
                    })
                }),
                apiFetch(`/strategy/recommend/${tickerKey}`).catch(() => null)
            ]);

            // Build indicator summary if available
            let indicatorHtml = '';
            if (recData && recData.composite_signal) {
                indicatorHtml = `
                <div class="card mb-20" style="background: rgba(13, 18, 40, 0.4); border-style: dashed;">
                    <div class="card-header" style="border-bottom:none; margin-bottom:0; padding-bottom:8px;">
                        <div class="card-title" style="font-size:0.85rem;"><span class="icon">🔍</span> Current Technical Context for ${tickerKey}</div>
                    </div>
                    <div class="grid-4" style="padding:0 20px 20px;">
                        <div>
                            <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase;">IV Percentile</div>
                            <div style="font-family:'JetBrains Mono'; font-weight:700; color:var(--accent-orange);">${recData.iv_percentile}%</div>
                        </div>
                        <div>
                            <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase;">Signal</div>
                            <div><span class="badge badge-${recData.composite_signal.signal.includes('BULL') ? 'bullish' : recData.composite_signal.signal.includes('BEAR') ? 'bearish' : 'neutral'}">${recData.composite_signal.signal}</span></div>
                        </div>
                        <div>
                            <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase;">RSI (14)</div>
                            <div style="font-family:'JetBrains Mono'; font-weight:700;">${recData.composite_signal.details.find(d => d.includes('RSI')) || 'N/A'}</div>
                        </div>
                        <div>
                            <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase;">MACD</div>
                            <div style="font-family:'JetBrains Mono'; font-weight:700;">${recData.composite_signal.details.find(d => d.includes('MACD')) || 'N/A'}</div>
                        </div>
                    </div>
                </div>`;
            }

            html += indicatorHtml + `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><span class="icon">📈</span> Live Simulation — ${strat.name} on ${tickerKey} @ $${data.underlying_price}</div>
                    </div>
                    <div class="mb-12" style="font-size:0.8rem; color:var(--text-muted)">
                        Showing theoretical payoff for a standard 30-DTE entry. The solid blue line shows profit/loss exactly at expiration. The dotted orange line shows the T+0 (Today's) value curve before time decay and volatility crush take effect.
                    </div>
                    <div class="chart-container" id="edu-payoff-chart" style="min-height:350px"></div>
                </div>
            `;
            container.innerHTML = html;

            // Plotly Payoff (T+0 vs Expiration)
            const payoffData = data.payoff_diagram;
            const traces = [
                {
                    x: payoffData.prices, y: payoffData.payoffs, type: "scatter", mode: "lines",
                    line: { color: "#3b82f6", width: 3 }, name: "At Expiration",
                    fill: "tozeroy", fillcolor: "rgba(59, 130, 246, 0.1)"
                }
            ];

            if (payoffData.payoffs_t0) {
                traces.push({
                    x: payoffData.prices, y: payoffData.payoffs_t0, type: "scatter", mode: "lines",
                    line: { color: "#f59e0b", width: 2, dash: "dot" }, name: "T+0 (Today)"
                });
            }

            const currentPriceLine = {
                type: "line", x0: data.underlying_price, x1: data.underlying_price,
                y0: data.max_loss, y1: data.max_profit,
                line: { color: "rgba(255,255,255,0.3)", width: 1, dash: "dash" }
            };

            Plotly.newPlot("edu-payoff-chart", traces, {
                ...PLOTLY_LAYOUT,
                title: { text: "Projected Move & Payoff Simulation", font: { size: 13, color: "#e8eaed" } },
                xaxis: { ...PLOTLY_LAYOUT.xaxis, title: "Underlying Price ($)", type: "linear" },
                yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "Profit/Loss ($)" },
                shapes: [
                    { type: "line", x0: payoffData.prices[0], x1: payoffData.prices[payoffData.prices.length-1], y0: 0, y1: 0, line: { color: "#78909c", width: 1 } },
                    currentPriceLine
                ],
                annotations: [{
                    x: data.underlying_price, y: data.max_profit * 0.9,
                    text: "Current Price", showarrow: false, font: { size: 10, color: "#9aa5b4" },
                    xanchor: "left", xshift: 5
                }]
            }, PLOTLY_CONFIG);

        } catch (e) {
            container.innerHTML = html + `<div class="empty-state"><div class="empty-state-text" style="color:var(--loss)">Simulation Error: ${e.message}</div></div>`;
        }
    } else {
        html += `<div class="empty-state"><div class="empty-state-text">Select a ticker to see a live projected move simulation.</div></div>`;
        container.innerHTML = html;
    }
}

// ═══ TICKER MANAGER ══════════════════════════════════════════════════════

async function loadTickerList() {
    const container = document.getElementById("ticker-list");
    try {
        const data = await apiFetch("/tickers");
        if (data.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">No tickers configured.</div></div>';
            return;
        }
        container.innerHTML = data.map(t => `
            <div class="ticker-item">
                <div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span class="ticker-symbol">${t.key}</span>
                        ${t.section_1256 ? '<span class="badge badge-1256">§1256</span>' : ''}
                    </div>
                    <div class="ticker-name">${t.name} (${t.symbol})</div>
                </div>
                <button class="btn btn-outline btn-sm" onclick="removeTicker('${t.key}')">Remove</button>
            </div>
        `).join("");
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-text" style="color:var(--loss)">Error: ${e.message}</div></div>`;
    }
}

async function addTicker() {
    const symbol = document.getElementById("add-ticker-symbol").value.trim().toUpperCase();
    const name = document.getElementById("add-ticker-name").value.trim();
    if (!symbol) return alert("Enter a ticker symbol.");

    try {
        await apiFetch("/tickers", {
            method: "POST",
            body: JSON.stringify({ symbol, name: name || symbol }),
        });
        document.getElementById("add-ticker-symbol").value = "";
        document.getElementById("add-ticker-name").value = "";
        await loadTickers();
        populateTickerSelects();
        loadTickerList();
    } catch (e) {
        alert("Error adding ticker: " + e.message);
    }
}

async function removeTicker(key) {
    if (!confirm(`Remove ${key}?`)) return;
    try {
        await apiFetch(`/tickers/${key}`, { method: "DELETE" });
        await loadTickers();
        populateTickerSelects();
        loadTickerList();
    } catch (e) {
        alert("Error removing ticker: " + e.message);
    }
}
