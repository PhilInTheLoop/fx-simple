# FX Simple - Currency Monitor

A simplified FX monitoring application with AI-powered analysis.

## Features

- Currency pair selection with 20+ currencies
- Current exchange rate display
- Daily change (absolute & percentage) with mini chart
- 3-month change (absolute & percentage) with mini chart
- Interest rates for both currencies
- AI-generated analysis (short-term & long-term outlook)

## Quick Start

### 1. Install dependencies

```bash
cd fx-simple
pip install -r requirements.txt
```

### 2. Configure (optional)

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

- `EXCHANGE_RATE_API_KEY` - Get a free key at https://www.exchangerate-api.com/
- `ANTHROPIC_API_KEY` - For AI analysis (optional, uses mock data if not set)

### 3. Run the app

```bash
cd backend
python main.py
```

Or with uvicorn directly:

```bash
uvicorn backend.main:app --reload
```

### 4. Open in browser

Navigate to http://localhost:8000

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/rates/{base}/{quote}` | Current exchange rate |
| `GET /api/rates/{base}/{quote}/history` | Historical data (90 days) |
| `GET /api/interest-rates/{base}/{quote}` | Interest rates for both currencies |
| `GET /api/ai/analyze/{base}/{quote}` | AI analysis (short & long term) |

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Charts**: Chart.js
- **FX Data**: Frankfurter API (free) / ExchangeRate-API
- **AI**: Claude API (Anthropic)
