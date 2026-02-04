// API Base URLs
const API_BASE = 'http://localhost:8000/api';
const FX_TRADER_API = 'https://fx-trader.thiel.ph/api';

// Available currencies
const CURRENCIES = [
    { code: 'EUR', name: 'Euro' },
    { code: 'USD', name: 'US Dollar' },
    { code: 'GBP', name: 'British Pound' },
    { code: 'JPY', name: 'Japanese Yen' },
    { code: 'CHF', name: 'Swiss Franc' },
    { code: 'AUD', name: 'Australian Dollar' },
    { code: 'CAD', name: 'Canadian Dollar' },
    { code: 'NZD', name: 'New Zealand Dollar' },
    { code: 'SEK', name: 'Swedish Krona' },
    { code: 'NOK', name: 'Norwegian Krone' },
    { code: 'DKK', name: 'Danish Krone' },
    { code: 'PLN', name: 'Polish Zloty' },
    { code: 'CZK', name: 'Czech Koruna' },
    { code: 'HUF', name: 'Hungarian Forint' },
    { code: 'CNY', name: 'Chinese Yuan' },
    { code: 'INR', name: 'Indian Rupee' },
    { code: 'MXN', name: 'Mexican Peso' },
    { code: 'BRL', name: 'Brazilian Real' },
    { code: 'ZAR', name: 'South African Rand' },
    { code: 'SGD', name: 'Singapore Dollar' },
    { code: 'HKD', name: 'Hong Kong Dollar' },
    { code: 'KRW', name: 'South Korean Won' },
    { code: 'TRY', name: 'Turkish Lira' }
];

// Chart instances
let historyChart = null;

// Current period (days)
let currentPeriod = 90;

// Trade data cache
let tradesCache = null;

// Exposure data cache
let exposureCache = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeCurrencyDropdowns();
    setupEventListeners();
    loadTrades(); // Pre-load trades
    loadExposure(); // Pre-load exposure
});

// Populate currency dropdowns
function initializeCurrencyDropdowns() {
    const baseSelect = document.getElementById('base-currency');
    const quoteSelect = document.getElementById('quote-currency');

    CURRENCIES.forEach(currency => {
        const option1 = new Option(`${currency.code}`, currency.code);
        const option2 = new Option(`${currency.code}`, currency.code);
        baseSelect.add(option1);
        quoteSelect.add(option2);
    });

    baseSelect.value = 'EUR';
    quoteSelect.value = 'USD';
}

// Setup event listeners
function setupEventListeners() {
    const baseSelect = document.getElementById('base-currency');
    const quoteSelect = document.getElementById('quote-currency');
    const swapBtn = document.getElementById('swap-btn');
    const periodSelect = document.getElementById('chart-period');

    baseSelect.addEventListener('change', onPairChange);
    quoteSelect.addEventListener('change', onPairChange);
    swapBtn.addEventListener('click', swapCurrencies);
    periodSelect.addEventListener('change', onPeriodChange);

    // Initial load
    onPairChange();
}

// Handle period change
async function onPeriodChange() {
    const periodSelect = document.getElementById('chart-period');
    currentPeriod = parseInt(periodSelect.value);

    const base = document.getElementById('base-currency').value;
    const quote = document.getElementById('quote-currency').value;

    if (base && quote && base !== quote) {
        const historicalData = await fetchHistoricalData(base, quote, currentPeriod);
        updateHistoricalChart(historicalData, base, quote);
    }
}

// Swap currencies
function swapCurrencies() {
    const baseSelect = document.getElementById('base-currency');
    const quoteSelect = document.getElementById('quote-currency');

    const temp = baseSelect.value;
    baseSelect.value = quoteSelect.value;
    quoteSelect.value = temp;

    onPairChange();
}

// Load trades from fx-trader
async function loadTrades() {
    try {
        const response = await fetch(`${FX_TRADER_API}/trades`);
        if (response.ok) {
            const data = await response.json();
            tradesCache = data.trades || [];
        }
    } catch (error) {
        console.log('Could not load trades:', error);
        tradesCache = [];
    }
}

// Load exposure from fx-trader
async function loadExposure() {
    try {
        const response = await fetch(`${FX_TRADER_API}/exposure`);
        if (response.ok) {
            const data = await response.json();
            exposureCache = data.exposure || [];
        }
    } catch (error) {
        console.log('Could not load exposure:', error);
        exposureCache = [];
    }
}

// Get exposure for a currency
function getExposureForCurrency(currency) {
    if (!exposureCache) return null;
    return exposureCache.find(e => e.currency === currency) || null;
}

// Get trades for a specific pair
function getTradesForPair(base, quote) {
    if (!tradesCache) return [];

    return tradesCache.filter(trade => {
        // Match direct pair (e.g., EUR/USD)
        const directMatch = trade.base_currency === base && trade.quote_currency === quote;
        // Match inverse pair (e.g., USD/EUR when looking at EUR/USD)
        const inverseMatch = trade.base_currency === quote && trade.quote_currency === base;
        return directMatch || inverseMatch;
    }).map(trade => {
        const isInverse = trade.base_currency === quote && trade.quote_currency === base;
        return {
            date: trade.entry_date,
            direction: isInverse ? (trade.direction === 'BUY' ? 'SELL' : 'BUY') : trade.direction,
            rate: isInverse ? (1 / trade.forward_rate) : trade.forward_rate,
            notional: trade.notional,
            notes: trade.notes
        };
    });
}

// Handle currency pair change
async function onPairChange() {
    const base = document.getElementById('base-currency').value;
    const quote = document.getElementById('quote-currency').value;

    if (!base || !quote || base === quote) {
        document.getElementById('main-content').classList.add('hidden');
        return;
    }

    showLoading(true);

    try {
        const [rateData, historicalData, interestData] = await Promise.all([
            fetchCurrentRate(base, quote),
            fetchHistoricalData(base, quote, currentPeriod),
            fetchInterestRates(base, quote)
        ]);

        updateCurrentRate(rateData, historicalData);
        updatePairExposure(base, quote);
        updateHistoricalChart(historicalData, base, quote);
        updateInterestRates(interestData, base, quote);
        updateExposure(base, quote);
        resetAISection(); // Don't auto-load AI, show request button

        document.getElementById('main-content').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading data:', error);
        alert('Error loading data. Please check if the backend is running.');
    } finally {
        showLoading(false);
    }
}

// API Calls
async function fetchCurrentRate(base, quote) {
    const response = await fetch(`${API_BASE}/rates/${base}/${quote}`);
    if (!response.ok) throw new Error('Failed to fetch rate');
    return response.json();
}

async function fetchHistoricalData(base, quote, days = 90) {
    const response = await fetch(`${API_BASE}/rates/${base}/${quote}/history?days=${days}`);
    if (!response.ok) throw new Error('Failed to fetch history');
    return response.json();
}

async function fetchInterestRates(base, quote) {
    const response = await fetch(`${API_BASE}/interest-rates/${base}/${quote}`);
    if (!response.ok) throw new Error('Failed to fetch interest rates');
    return response.json();
}

async function fetchAIAnalysis(base, quote) {
    const settings = getSettingsForAPI();
    const params = new URLSearchParams();

    if (settings.short_term_focus) params.append('short_term_focus', settings.short_term_focus);
    if (settings.long_term_focus) params.append('long_term_focus', settings.long_term_focus);
    if (settings.style) params.append('style', settings.style);
    if (settings.depth) params.append('depth', settings.depth);
    if (settings.sources) params.append('sources', settings.sources);
    if (settings.use_web_search) params.append('use_web_search', 'true');

    const url = `${API_BASE}/ai/analyze/${base}/${quote}${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch AI analysis');
    return response.json();
}

// UI Updates
function updateCurrentRate(data, historicalData) {
    document.getElementById('current-rate').textContent = data.rate.toFixed(4);
    const time = new Date(data.timestamp);
    document.getElementById('rate-timestamp').textContent = time.toLocaleTimeString();

    // Daily change (from last few data points)
    const dailyAbsolute = document.getElementById('daily-absolute');
    const dailyPercent = document.getElementById('daily-percent');

    if (historicalData && historicalData.daily) {
        const change = data.rate - historicalData.daily.open;
        const percentChange = (change / historicalData.daily.open) * 100;

        dailyAbsolute.textContent = formatChange(change);
        dailyAbsolute.className = `change-value ${change >= 0 ? 'positive' : 'negative'}`;

        dailyPercent.textContent = formatPercent(percentChange);
        dailyPercent.className = `change-value ${percentChange >= 0 ? 'positive' : 'negative'}`;
    }
}

// Update pair exposure (prominent section)
function updatePairExposure(base, quote) {
    const card = document.getElementById('pair-exposure-card');
    const pairLabel = document.getElementById('pair-label');
    const pairValue = document.getElementById('pair-exposure-value');
    const pairDetails = document.getElementById('pair-exposure-details');
    const expandArrow = document.getElementById('pair-expand-arrow');

    pairLabel.textContent = `${base}/${quote}`;

    // Reset state
    card.classList.remove('expanded', 'no-trades');
    pairDetails.classList.add('hidden');

    // Get trades for this specific pair
    const trades = getTradesForPair(base, quote);

    if (trades.length === 0) {
        pairValue.textContent = 'No position';
        pairValue.className = 'pair-exposure-value neutral';
        pairDetails.innerHTML = '';
        expandArrow.style.display = 'none';
        card.classList.add('no-trades');
        return;
    }

    // Show expand arrow when there are trades
    expandArrow.style.display = 'inline';

    // Calculate net exposure for this pair
    let netExposure = 0;
    trades.forEach(trade => {
        if (trade.direction === 'BUY') {
            netExposure += trade.notional;
        } else {
            netExposure -= trade.notional;
        }
    });

    // Display net exposure
    const isLong = netExposure > 0;
    const isShort = netExposure < 0;
    pairValue.textContent = `${isLong ? 'Long' : isShort ? 'Short' : ''} ${formatExposure(Math.abs(netExposure))}`;
    pairValue.className = `pair-exposure-value ${isLong ? 'long' : isShort ? 'short' : 'neutral'}`;

    // Prepare trade details (hidden by default)
    const detailsHtml = trades.map(trade => {
        const dir = trade.direction === 'BUY' ? 'Buy' : 'Sell';
        return `<div class="trade-item">
            <span>${dir} ${formatExposure(trade.notional)} @ ${trade.rate.toFixed(4)}</span>
            <span>${trade.date}</span>
        </div>`;
    }).join('');
    pairDetails.innerHTML = detailsHtml;
}

// Update historical chart with period
function updateHistoricalChart(historicalData, base, quote) {
    const periodAbsolute = document.getElementById('period-absolute');
    const periodPercent = document.getElementById('period-percent');
    const periodLabel = document.getElementById('period-label');

    // Update period label
    const periodNames = { 30: '1M', 90: '3M', 365: '1Y' };
    periodLabel.textContent = `${periodNames[currentPeriod] || ''} Change`;

    if (historicalData.threeMonth) {
        const change = historicalData.threeMonth.close - historicalData.threeMonth.open;
        const percentChange = (change / historicalData.threeMonth.open) * 100;

        periodAbsolute.textContent = formatChange(change);
        periodAbsolute.className = `change-value ${change >= 0 ? 'positive' : 'negative'}`;

        periodPercent.textContent = formatPercent(percentChange);
        periodPercent.className = `change-value ${percentChange >= 0 ? 'positive' : 'negative'}`;

        // Get trades for this pair
        const trades = getTradesForPair(base, quote);
        renderHistoryChart(historicalData.threeMonth.data, trades);
    }
}

function updateInterestRates(data, base, quote) {
    document.getElementById('base-name').textContent = base;
    document.getElementById('quote-name').textContent = quote;
    document.getElementById('base-interest').textContent = `${data.base_rate.toFixed(2)}%`;
    document.getElementById('quote-interest').textContent = `${data.quote_rate.toFixed(2)}%`;

    // Base direction indicator
    const baseDir = document.getElementById('base-direction');
    baseDir.textContent = getDirectionSymbol(data.base_last_decision);
    baseDir.className = `rate-direction ${data.base_last_decision}`;

    // Quote direction indicator
    const quoteDir = document.getElementById('quote-direction');
    quoteDir.textContent = getDirectionSymbol(data.quote_last_decision);
    quoteDir.className = `rate-direction ${data.quote_last_decision}`;

    // Meta info (days at rate)
    document.getElementById('base-meta').textContent = formatDaysAtRate(data.base_days_at_rate);
    document.getElementById('quote-meta').textContent = formatDaysAtRate(data.quote_days_at_rate);

    const diff = data.base_rate - data.quote_rate;
    const diffEl = document.getElementById('rate-differential');
    diffEl.textContent = `${diff >= 0 ? '+' : ''}${diff.toFixed(2)}%`;
    diffEl.className = `interest-value ${diff >= 0 ? 'positive' : 'negative'}`;
}

function getDirectionSymbol(decision) {
    switch (decision) {
        case 'up': return '▲';
        case 'down': return '▼';
        default: return '●';
    }
}

function formatDaysAtRate(days) {
    if (days < 30) return `${days}d at this rate`;
    if (days < 365) return `${Math.floor(days / 30)}mo at this rate`;
    return `${(days / 365).toFixed(1)}y at this rate`;
}

function updateExposure(base, quote) {
    const baseExp = getExposureForCurrency(base);
    const quoteExp = getExposureForCurrency(quote);

    // Update base currency exposure
    document.getElementById('base-exp-name').textContent = base;
    const baseExpValue = document.getElementById('base-exposure');
    const baseExpBar = document.getElementById('base-exp-bar');

    if (baseExp) {
        const net = baseExp.net;
        baseExpValue.textContent = formatExposure(net);
        baseExpValue.className = `exposure-value ${net > 0 ? 'long' : net < 0 ? 'short' : 'neutral'}`;

        // Calculate bar width (normalize to max exposure for visual)
        const maxExp = Math.max(...exposureCache.map(e => Math.abs(e.net)));
        const barWidth = maxExp > 0 ? (Math.abs(net) / maxExp) * 100 : 0;
        baseExpBar.style.width = `${barWidth}%`;
        baseExpBar.className = `exposure-bar ${net > 0 ? 'long' : 'short'}`;
    } else {
        baseExpValue.textContent = 'No position';
        baseExpValue.className = 'exposure-value neutral';
        baseExpBar.style.width = '0%';
    }

    // Update quote currency exposure
    document.getElementById('quote-exp-name').textContent = quote;
    const quoteExpValue = document.getElementById('quote-exposure');
    const quoteExpBar = document.getElementById('quote-exp-bar');

    if (quoteExp) {
        const net = quoteExp.net;
        quoteExpValue.textContent = formatExposure(net);
        quoteExpValue.className = `exposure-value ${net > 0 ? 'long' : net < 0 ? 'short' : 'neutral'}`;

        const maxExp = Math.max(...exposureCache.map(e => Math.abs(e.net)));
        const barWidth = maxExp > 0 ? (Math.abs(net) / maxExp) * 100 : 0;
        quoteExpBar.style.width = `${barWidth}%`;
        quoteExpBar.className = `exposure-bar ${net > 0 ? 'long' : 'short'}`;
    } else {
        quoteExpValue.textContent = 'No position';
        quoteExpValue.className = 'exposure-value neutral';
        quoteExpBar.style.width = '0%';
    }
}

function formatExposure(value) {
    const absValue = Math.abs(value);
    let formatted;

    if (absValue >= 1000000) {
        formatted = (absValue / 1000000).toFixed(2) + 'M';
    } else if (absValue >= 1000) {
        formatted = (absValue / 1000).toFixed(1) + 'K';
    } else {
        formatted = absValue.toFixed(0);
    }

    return (value >= 0 ? '+' : '-') + formatted;
}

// Reset AI section to initial state (request button)
function resetAISection() {
    document.getElementById('ai-request').classList.remove('hidden');
    document.getElementById('ai-results').classList.add('hidden');
    document.getElementById('ai-status').textContent = '';
    document.getElementById('ai-status').className = 'ai-status';
}

// Request AI analysis (button click)
async function requestAIAnalysis() {
    const base = document.getElementById('base-currency').value;
    const quote = document.getElementById('quote-currency').value;

    if (!base || !quote || base === quote) return;

    const requestBtn = document.getElementById('request-ai-btn');
    const refreshBtn = document.getElementById('refresh-ai');
    const status = document.getElementById('ai-status');

    // Update UI to loading state
    requestBtn.disabled = true;
    requestBtn.innerHTML = '<span class="btn-icon">⏳</span> Analyzing...';
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.textContent = 'Analyzing...';
    }
    status.textContent = 'Loading...';
    status.className = 'ai-status loading';

    // Show results section with loading state
    document.getElementById('ai-request').classList.add('hidden');
    document.getElementById('ai-results').classList.remove('hidden');

    document.getElementById('short-term-trend').textContent = '...';
    document.getElementById('short-term-trend').className = 'trend-indicator';
    document.getElementById('short-term-summary').textContent = 'Analyzing market data...';

    document.getElementById('long-term-trend').textContent = '...';
    document.getElementById('long-term-trend').className = 'trend-indicator';
    document.getElementById('long-term-summary').textContent = 'Analyzing market data...';

    try {
        const data = await fetchAIAnalysis(base, quote);
        updateAIDisplay('short-term', data.shortTerm);
        updateAIDisplay('long-term', data.longTerm);
        status.textContent = 'Ready';
        status.className = 'ai-status ready';
    } catch (error) {
        console.error('AI analysis error:', error);
        document.getElementById('short-term-summary').textContent = 'Analysis unavailable';
        document.getElementById('long-term-summary').textContent = 'Analysis unavailable';
        status.textContent = 'Error';
        status.className = 'ai-status';
    } finally {
        requestBtn.disabled = false;
        requestBtn.innerHTML = '<span class="btn-icon">🤖</span> Request AI Analysis';
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.textContent = 'Refresh Analysis';
        }
    }
}

function updateAIDisplay(prefix, data) {
    const trendEl = document.getElementById(`${prefix}-trend`);
    const summaryEl = document.getElementById(`${prefix}-summary`);
    const fullEl = document.getElementById(`${prefix}-full`);
    const sourcesEl = document.getElementById(`${prefix}-sources`);

    trendEl.textContent = data.trend;
    trendEl.className = `trend-indicator ${data.trend.toLowerCase()}`;

    summaryEl.textContent = data.summary;
    fullEl.textContent = data.details;

    if (data.sources && data.sources.length > 0) {
        sourcesEl.innerHTML = '<strong>Sources:</strong> ' +
            data.sources.map(s => `<a href="${s.url}" target="_blank">${s.name}</a>`).join(' | ');
    } else {
        sourcesEl.innerHTML = '';
    }
}


// Chart function
function renderHistoryChart(data, trades = []) {
    const ctx = document.getElementById('history-chart').getContext('2d');

    if (historyChart) {
        historyChart.destroy();
    }

    const labels = data.map(d => {
        const parts = d.date.split('-');
        return `${parts[1]}/${parts[2]}`;
    });
    const values = data.map(d => d.rate);
    const color = values[values.length - 1] >= values[0] ? '#16a34a' : '#dc2626';

    // Create annotations for trades
    const annotations = {};
    const legend = document.getElementById('trade-legend');

    if (trades.length > 0) {
        legend.style.display = 'flex';

        trades.forEach((trade, idx) => {
            const tradeDate = trade.date;
            const labelIdx = data.findIndex(d => d.date === tradeDate);

            if (labelIdx !== -1) {
                const isBuy = trade.direction === 'BUY';
                annotations[`trade${idx}`] = {
                    type: 'point',
                    xValue: labelIdx,
                    yValue: data[labelIdx].rate,
                    backgroundColor: isBuy ? '#16a34a' : '#dc2626',
                    borderColor: '#fff',
                    borderWidth: 2,
                    radius: 6
                };
            }
        });
    } else {
        legend.style.display = 'none';
    }

    // Adjust tick density based on period
    const maxTicks = currentPeriod <= 30 ? 6 : currentPeriod <= 90 ? 8 : 12;

    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                borderColor: color,
                borderWidth: 2,
                fill: false,
                tension: 0.3,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                annotation: {
                    annotations: annotations
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: { display: false },
                    ticks: {
                        font: { size: 9 },
                        color: '#9ca3af',
                        maxTicksLimit: maxTicks
                    }
                },
                y: {
                    display: true,
                    position: 'right',
                    grid: { color: '#e5e7eb' },
                    ticks: {
                        font: { size: 9 },
                        color: '#9ca3af',
                        callback: v => v.toFixed(4)
                    }
                }
            }
        }
    });
}

// Toggle pair exposure details
function togglePairDetails() {
    const card = document.getElementById('pair-exposure-card');
    const details = document.getElementById('pair-exposure-details');

    // Don't toggle if no trades
    if (card.classList.contains('no-trades')) return;

    card.classList.toggle('expanded');
    details.classList.toggle('hidden');
}

// Toggle AI details
function toggleDetails(prefix) {
    const block = document.getElementById(`${prefix}-block`);
    const details = document.getElementById(`${prefix}-details`);

    block.classList.toggle('expanded');
    details.classList.toggle('hidden');
}


// Utility functions
function formatChange(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(4)}`;
}

function formatPercent(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    const main = document.getElementById('main-content');

    if (show) {
        loading.classList.remove('hidden');
        main.classList.add('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

// ============ Settings Modal ============

const DEFAULT_SETTINGS = {
    shortTermPrompt: '',
    longTermPrompt: '',
    analysisStyle: 'balanced',
    analysisDepth: 'standard',
    useWebSearch: false,
    sources: {
        interestRates: true,
        centralBanks: true,
        economic: true,
        technical: true
    }
};

const STYLE_DESCRIPTIONS = {
    balanced: 'Considers both technical and fundamental factors equally.',
    technical: 'Emphasizes chart patterns, support/resistance levels, and momentum indicators.',
    fundamental: 'Focuses on economic data, central bank policies, and macroeconomic trends.',
    risk: 'Prioritizes risk assessment, volatility, and potential market-moving events.',
    brief: 'Provides quick, actionable insights without extensive detail.'
};

function loadSettings() {
    try {
        const saved = localStorage.getItem('fxSimpleSettings');
        return saved ? JSON.parse(saved) : { ...DEFAULT_SETTINGS };
    } catch {
        return { ...DEFAULT_SETTINGS };
    }
}

function saveSettingsToStorage(settings) {
    localStorage.setItem('fxSimpleSettings', JSON.stringify(settings));
}

function openSettings() {
    const settings = loadSettings();

    // Basic settings
    document.getElementById('short-term-prompt').value = settings.shortTermPrompt || '';
    document.getElementById('long-term-prompt').value = settings.longTermPrompt || '';
    document.getElementById('analysis-style').value = settings.analysisStyle || 'balanced';
    document.getElementById('analysis-depth').value = settings.analysisDepth || 'standard';
    document.getElementById('use-web-search').checked = settings.useWebSearch || false;

    // Source checkboxes
    const sources = settings.sources || DEFAULT_SETTINGS.sources;
    document.getElementById('source-interest-rates').checked = sources.interestRates !== false;
    document.getElementById('source-central-banks').checked = sources.centralBanks !== false;
    document.getElementById('source-economic').checked = sources.economic !== false;
    document.getElementById('source-technical').checked = sources.technical !== false;

    // Update style description
    updateStyleDescription();

    // Setup style change listener
    document.getElementById('analysis-style').addEventListener('change', updateStyleDescription);

    document.getElementById('settings-modal').classList.remove('hidden');
}

function updateStyleDescription() {
    const style = document.getElementById('analysis-style').value;
    const desc = document.getElementById('style-description');
    desc.textContent = STYLE_DESCRIPTIONS[style] || '';
}

function closeSettings() {
    document.getElementById('settings-modal').classList.add('hidden');
}

function closeSettingsOnOverlay(event) {
    if (event.target.id === 'settings-modal') {
        closeSettings();
    }
}

function saveSettings() {
    const settings = {
        shortTermPrompt: document.getElementById('short-term-prompt').value.trim(),
        longTermPrompt: document.getElementById('long-term-prompt').value.trim(),
        analysisStyle: document.getElementById('analysis-style').value,
        analysisDepth: document.getElementById('analysis-depth').value,
        useWebSearch: document.getElementById('use-web-search').checked,
        sources: {
            interestRates: document.getElementById('source-interest-rates').checked,
            centralBanks: document.getElementById('source-central-banks').checked,
            economic: document.getElementById('source-economic').checked,
            technical: document.getElementById('source-technical').checked
        }
    };
    saveSettingsToStorage(settings);
    closeSettings();

    // Show notification
    alert('Settings saved! Click "Request AI Analysis" to use new settings.');
}

function resetSettings() {
    // Reset all fields to defaults
    document.getElementById('short-term-prompt').value = '';
    document.getElementById('long-term-prompt').value = '';
    document.getElementById('analysis-style').value = 'balanced';
    document.getElementById('analysis-depth').value = 'standard';
    document.getElementById('use-web-search').checked = false;
    document.getElementById('source-interest-rates').checked = true;
    document.getElementById('source-central-banks').checked = true;
    document.getElementById('source-economic').checked = true;
    document.getElementById('source-technical').checked = true;

    updateStyleDescription();

    // Also clear from storage
    saveSettingsToStorage({ ...DEFAULT_SETTINGS });
}

function togglePromptPreview() {
    const preview = document.getElementById('prompt-preview');
    preview.classList.toggle('hidden');

    if (!preview.classList.contains('hidden')) {
        updatePromptPreview();
    }
}

function updatePromptPreview() {
    const settings = {
        style: document.getElementById('analysis-style').value,
        depth: document.getElementById('analysis-depth').value,
        shortFocus: document.getElementById('short-term-prompt').value,
        longFocus: document.getElementById('long-term-prompt').value,
        webSearch: document.getElementById('use-web-search').checked,
        sources: {
            interestRates: document.getElementById('source-interest-rates').checked,
            centralBanks: document.getElementById('source-central-banks').checked,
            economic: document.getElementById('source-economic').checked,
            technical: document.getElementById('source-technical').checked
        }
    };

    const styleText = STYLE_DESCRIPTIONS[settings.style];
    const sourcesText = [];
    if (settings.sources.interestRates) sourcesText.push('Interest rate differentials');
    if (settings.sources.centralBanks) sourcesText.push('Central bank policies');
    if (settings.sources.economic) sourcesText.push('Economic conditions');
    if (settings.sources.technical) sourcesText.push('Technical factors');

    let preview = `You are a professional FX analyst. Analyze the {PAIR} currency pair.

Current Market Data:
- Currency Pair: {PAIR}
- Current Rate: {RATE}
- Base Interest Rate: {BASE_RATE}%
- Quote Interest Rate: {QUOTE_RATE}%
- Interest Rate Differential: {DIFFERENTIAL}%

Analysis Style: ${styleText}
Analysis Depth: ${settings.depth}
`;

    if (sourcesText.length > 0) {
        preview += `\nBase analysis on:\n${sourcesText.map(s => '- ' + s).join('\n')}`;
    }

    if (settings.shortFocus) {
        preview += `\n\nShort-term focus: ${settings.shortFocus}`;
    }

    if (settings.longFocus) {
        preview += `\n\nLong-term focus: ${settings.longFocus}`;
    }

    if (settings.webSearch) {
        preview += `\n\n[Web research will be performed to gather analyst forecasts and market sentiment]`;
    }

    document.getElementById('prompt-preview-text').textContent = preview;
}

function getSettingsForAPI() {
    const settings = loadSettings();
    const sources = settings.sources || DEFAULT_SETTINGS.sources;

    // Build sources string
    const sourcesList = [];
    if (sources.interestRates) sourcesList.push('interest_rates');
    if (sources.centralBanks) sourcesList.push('central_banks');
    if (sources.economic) sourcesList.push('economic');
    if (sources.technical) sourcesList.push('technical');

    return {
        short_term_focus: settings.shortTermPrompt,
        long_term_focus: settings.longTermPrompt,
        style: settings.analysisStyle,
        depth: settings.analysisDepth || 'standard',
        use_web_search: settings.useWebSearch,
        sources: sourcesList.join(',')
    };
}
