"""
Exchange rate routes
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import httpx
import os
from typing import Optional

router = APIRouter()

# Cache for rates
_rate_cache = {}
_cache_ttl = 300  # 5 minutes

# ExchangeRate-API (free tier)
# Sign up at https://www.exchangerate-api.com/ for a free API key
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY", "demo")
EXCHANGE_RATE_BASE_URL = "https://v6.exchangerate-api.com/v6"

# For historical data, we'll use a free API
FRANKFURTER_BASE_URL = "https://api.frankfurter.app"


async def get_current_rate(base: str, quote: str) -> dict:
    """Fetch current exchange rate"""
    cache_key = f"{base}_{quote}"
    now = datetime.now()

    # Check cache
    if cache_key in _rate_cache:
        cached = _rate_cache[cache_key]
        if (now - cached["cached_at"]).seconds < _cache_ttl:
            return cached["data"]

    async with httpx.AsyncClient() as client:
        try:
            # Try ExchangeRate-API first
            if EXCHANGE_RATE_API_KEY != "demo":
                url = f"{EXCHANGE_RATE_BASE_URL}/{EXCHANGE_RATE_API_KEY}/pair/{base}/{quote}"
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    result = {
                        "base": base,
                        "quote": quote,
                        "rate": data["conversion_rate"],
                        "timestamp": datetime.now().isoformat()
                    }
                    _rate_cache[cache_key] = {"data": result, "cached_at": now}
                    return result

            # Fallback to Frankfurter API (free, no key needed)
            url = f"{FRANKFURTER_BASE_URL}/latest?from={base}&to={quote}"
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                result = {
                    "base": base,
                    "quote": quote,
                    "rate": data["rates"].get(quote, 0),
                    "timestamp": datetime.now().isoformat()
                }
                _rate_cache[cache_key] = {"data": result, "cached_at": now}
                return result

        except Exception as e:
            print(f"Error fetching rate: {e}")

    raise HTTPException(status_code=503, detail="Unable to fetch exchange rate")


@router.get("/{base}/{quote}")
async def get_rate(base: str, quote: str):
    """Get current exchange rate for a currency pair"""
    base = base.upper()
    quote = quote.upper()
    return await get_current_rate(base, quote)


@router.get("/{base}/{quote}/history")
async def get_history(base: str, quote: str, days: Optional[int] = 90):
    """Get historical exchange rate data"""
    base = base.upper()
    quote = quote.upper()

    async with httpx.AsyncClient() as client:
        try:
            # Get 3-month historical data from Frankfurter
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            url = f"{FRANKFURTER_BASE_URL}/{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}?from={base}&to={quote}"
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                rates_data = data.get("rates", {})

                # Convert to list format
                history = []
                for date_str, rates in sorted(rates_data.items()):
                    if quote in rates:
                        history.append({
                            "date": date_str,
                            "rate": rates[quote]
                        })

                # Calculate daily data (last 24 hours approximation using recent data)
                daily_data = history[-5:] if len(history) >= 5 else history  # Last few data points
                daily_open = daily_data[0]["rate"] if daily_data else 0
                daily_close = daily_data[-1]["rate"] if daily_data else 0

                # Calculate 3-month data
                three_month_open = history[0]["rate"] if history else 0
                three_month_close = history[-1]["rate"] if history else 0

                return {
                    "daily": {
                        "open": daily_open,
                        "close": daily_close,
                        "data": [{"time": d["date"], "rate": d["rate"]} for d in daily_data]
                    },
                    "threeMonth": {
                        "open": three_month_open,
                        "close": three_month_close,
                        "data": history
                    }
                }

        except Exception as e:
            print(f"Error fetching history: {e}")

    raise HTTPException(status_code=503, detail="Unable to fetch historical data")
