# FX Simple - Currency Monitor

A modern currency monitoring application with real-time exchange rates from multiple official sources, AI-powered market analysis, and portfolio exposure tracking.

## Features

### Multi-Source Exchange Rates
- **Real-time rates** from Frankfurter API (ECB data)
- **Official ECB rates** (European Central Bank) - preferred for EUR-based pairs
- **Official FRED rates** (Federal Reserve Economic Data) - preferred for USD-based pairs
- Automatic source selection based on base currency
- Rate comparison showing difference between market and official rates

### Historical Data & Charts
- Adjustable time periods: 1 month, 3 months, 1 year
- Data source indicator (ECB/FRED) on chart
- Trade markers overlay for portfolio positions
- Period change calculation (absolute & percentage)

### 23 Supported Currencies
Full currency selector with names and symbols:
- Major: EUR, USD, GBP, JPY, CHF, AUD, CAD, NZD
- European: SEK, NOK, DKK, PLN, CZK, HUF
- Asian: CNY, INR, SGD, HKD, KRW
- Americas: MXN, BRL
- Other: ZAR, TRY

### AI-Powered Analysis
- Powered by **Claude AI** (Anthropic)
- Short-term outlook (1-7 days)
- Long-term outlook (1-3 months)
- Optional **live web research** for real-time analyst forecasts
- Customizable analysis style:
  - Balanced (technical & fundamental)
  - Technical (charts, levels, momentum)
  - Fundamental (economics & policy)
  - Risk-focused (volatility & events)
  - Brief (concise summary)

### Central Bank Interest Rates
- Current rates for 23 central banks
- Last decision indicator (up/down/unchanged)
- Days at current rate
- Interest rate differential calculation

### Portfolio Integration
- Integration with FX Trader API
- Currency exposure as percentage of total portfolio
- Position details with trade history
- Visual exposure bars (long/short indicators)

## Tech Stack

- **Backend**: Python 3.8+, FastAPI, httpx, python-dotenv
- **Frontend**: Vanilla JavaScript, Chart.js
- **Data Sources**:
  - Frankfurter API (ECB exchange rates)
  - ECB XML Feed (official reference rates)
  - FRED API (Federal Reserve economic data)
  - Anthropic Claude API (AI analysis)

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/PhilInTheLoop/fx-simple.git
cd fx-simple
```

### 2. Install dependencies
```bash
pip install fastapi uvicorn httpx python-dotenv
```

### 3. Configure API keys

Create a `.env` file in the project root:
```env
# Optional: ExchangeRate-API key (free tier)
# https://www.exchangerate-api.com/
EXCHANGE_RATE_API_KEY=

# FRED API key (Federal Reserve Economic Data)
# Get free key at: https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY=your_fred_api_key

# Anthropic API key for AI analysis
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 4. Start the server
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 5. Open in browser
Navigate to http://localhost:8000

## API Endpoints

### Exchange Rates
| Endpoint | Description |
|----------|-------------|
| `GET /api/rates/{base}/{quote}` | Current rate with ECB/FRED official rates |
| `GET /api/rates/{base}/{quote}/history?days=90` | Historical data with source indicator |

### Interest Rates
| Endpoint | Description |
|----------|-------------|
| `GET /api/interest-rates/{base}/{quote}` | Central bank rates for both currencies |

### AI Analysis
| Endpoint | Description |
|----------|-------------|
| `GET /api/ai/analyze/{base}/{quote}` | AI market analysis |

Query parameters for AI analysis:
- `style`: balanced, technical, fundamental, risk, brief
- `depth`: standard, detailed, brief
- `sources`: interest_rates, central_banks, economic, technical
- `use_web_search`: true/false (enables live web research)
- `short_term_focus`: custom prompt addition
- `long_term_focus`: custom prompt addition

## Data Sources

| Source | Description | Update Frequency | Used For |
|--------|-------------|------------------|----------|
| Frankfurter | ECB reference rates | Daily 16:00 CET | Default market rate |
| ECB | European Central Bank | Daily 16:00 CET | EUR-based pairs (preferred) |
| FRED | Federal Reserve | Daily (1-2 day delay) | USD-based pairs (preferred) |
| Anthropic | Claude AI | On-demand | Market analysis |

## Project Structure

```
fx-simple/
├── backend/
│   ├── main.py              # FastAPI application
│   └── routes/
│       ├── rates.py         # Exchange rate endpoints (ECB, FRED)
│       ├── interest.py      # Interest rate data
│       └── ai.py            # AI analysis with Claude
├── frontend/
│   ├── index.html           # Main application page
│   ├── css/
│   │   └── style.css        # Application styles
│   └── js/
│       └── app.js           # Frontend JavaScript
├── .env                     # API keys (not in git)
├── .gitignore
└── README.md
```

## License

MIT License

## Author

Created with Claude Code
