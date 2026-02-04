"""
Exchange rate routes
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import httpx
import os
import xml.etree.ElementTree as ET
from typing import Optional

router = APIRouter()

# Cache for rates
_rate_cache = {}
_ecb_cache = {}
_fred_cache = {}
_cache_ttl = 300  # 5 minutes
_ecb_cache_ttl = 3600  # 1 hour (ECB updates once daily at 16:00 CET)
_fred_cache_ttl = 3600  # 1 hour (FRED updates daily)

# ExchangeRate-API (free tier)
# Sign up at https://www.exchangerate-api.com/ for a free API key
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY", "demo")
EXCHANGE_RATE_BASE_URL = "https://v6.exchangerate-api.com/v6"

# For historical data, we'll use a free API
FRANKFURTER_BASE_URL = "https://api.frankfurter.app"

# ECB Official Rate (daily reference rates)
ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

# FRED API (Federal Reserve Economic Data - St. Louis Fed)
# Get free API key at https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# FRED series IDs for exchange rates (format varies by currency)
# Most are: foreign currency per 1 USD
FRED_SERIES = {
    # USD as base (how much foreign currency per 1 USD)
    ("USD", "EUR"): {"series": "DEXUSEU", "invert": True},   # USD per EUR -> invert for USD/EUR
    ("USD", "GBP"): {"series": "DEXUSUK", "invert": True},   # USD per GBP -> invert
    ("USD", "JPY"): {"series": "DEXJPUS", "invert": False},  # JPY per USD
    ("USD", "CHF"): {"series": "DEXSZUS", "invert": False},  # CHF per USD
    ("USD", "CAD"): {"series": "DEXCAUS", "invert": False},  # CAD per USD
    ("USD", "AUD"): {"series": "DEXUSAL", "invert": True},   # USD per AUD -> invert
    ("USD", "NZD"): {"series": "DEXUSNZ", "invert": True},   # USD per NZD -> invert
    ("USD", "SEK"): {"series": "DEXSDUS", "invert": False},  # SEK per USD
    ("USD", "NOK"): {"series": "DEXNOUS", "invert": False},  # NOK per USD
    ("USD", "DKK"): {"series": "DEXDNUS", "invert": False},  # DKK per USD
    ("USD", "MXN"): {"series": "DEXMXUS", "invert": False},  # MXN per USD
    ("USD", "BRL"): {"series": "DEXBZUS", "invert": False},  # BRL per USD
    ("USD", "CNY"): {"series": "DEXCHUS", "invert": False},  # CNY per USD
    ("USD", "INR"): {"series": "DEXINUS", "invert": False},  # INR per USD
    ("USD", "KRW"): {"series": "DEXKOUS", "invert": False},  # KRW per USD
    ("USD", "SGD"): {"series": "DEXSIUS", "invert": False},  # SGD per USD
    ("USD", "HKD"): {"series": "DEXHKUS", "invert": False},  # HKD per USD
    ("USD", "ZAR"): {"series": "DEXSFUS", "invert": False},  # ZAR per USD
}


async def fetch_ecb_rates() -> dict:
    """Fetch official ECB reference rates (updated daily at 16:00 CET)"""
    global _ecb_cache
    now = datetime.now()

    # Check cache
    if "rates" in _ecb_cache:
        cached = _ecb_cache["rates"]
        if (now - cached["cached_at"]).seconds < _ecb_cache_ttl:
            return cached["data"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(ECB_DAILY_URL, timeout=10.0)
            if response.status_code == 200:
                # Parse XML
                root = ET.fromstring(response.content)
                ns = {
                    'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
                    'eurofxref': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'
                }

                rates = {"EUR": 1.0}  # EUR is always 1.0 as base
                ref_date = None

                # Find the Cube with time attribute (date)
                for cube in root.findall('.//eurofxref:Cube[@time]', ns):
                    ref_date = cube.get('time')
                    # Get all currency rates
                    for rate_cube in cube.findall('eurofxref:Cube', ns):
                        currency = rate_cube.get('currency')
                        rate = float(rate_cube.get('rate'))
                        rates[currency] = rate

                result = {
                    "rates": rates,
                    "date": ref_date,
                    "source": "ECB"
                }
                _ecb_cache["rates"] = {"data": result, "cached_at": now}
                return result

        except Exception as e:
            print(f"Error fetching ECB rates: {e}")

    return None


async def get_ecb_rate(base: str, quote: str) -> Optional[dict]:
    """Get ECB rate for a currency pair (EUR must be base or quote)"""
    ecb_data = await fetch_ecb_rates()
    if not ecb_data:
        return None

    rates = ecb_data["rates"]

    # ECB only provides EUR-based rates
    if base == "EUR" and quote in rates:
        return {
            "rate": rates[quote],
            "date": ecb_data["date"],
            "source": "ECB"
        }
    elif quote == "EUR" and base in rates:
        return {
            "rate": 1.0 / rates[base],
            "date": ecb_data["date"],
            "source": "ECB"
        }
    elif base in rates and quote in rates:
        # Cross rate via EUR (e.g., USD/GBP = EUR/GBP / EUR/USD)
        return {
            "rate": rates[quote] / rates[base],
            "date": ecb_data["date"],
            "source": "ECB (cross)"
        }

    return None


async def get_fred_rate(base: str, quote: str) -> Optional[dict]:
    """Get FRED rate for USD-based currency pairs"""
    global _fred_cache

    if not FRED_API_KEY:
        return None

    # Check if we have this pair in FRED series
    pair_key = (base, quote)
    inverse_key = (quote, base)

    series_info = None
    is_inverse = False

    if pair_key in FRED_SERIES:
        series_info = FRED_SERIES[pair_key]
    elif inverse_key in FRED_SERIES:
        series_info = FRED_SERIES[inverse_key]
        is_inverse = True

    if not series_info:
        return None

    series_id = series_info["series"]
    cache_key = series_id
    now = datetime.now()

    # Check cache
    if cache_key in _fred_cache:
        cached = _fred_cache[cache_key]
        if (now - cached["cached_at"]).seconds < _fred_cache_ttl:
            rate_data = cached["data"]
            rate = rate_data["rate"]
            # Apply inversions
            if series_info["invert"]:
                rate = 1.0 / rate
            if is_inverse:
                rate = 1.0 / rate
            return {
                "rate": rate,
                "date": rate_data["date"],
                "source": "FRED"
            }

    async with httpx.AsyncClient() as client:
        try:
            # Get latest observation
            params = {
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1
            }
            response = await client.get(FRED_BASE_URL, params=params, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                observations = data.get("observations", [])

                if observations and observations[0].get("value") != ".":
                    raw_rate = float(observations[0]["value"])
                    ref_date = observations[0]["date"]

                    # Cache the raw rate
                    _fred_cache[cache_key] = {
                        "data": {"rate": raw_rate, "date": ref_date},
                        "cached_at": now
                    }

                    # Apply inversions for the requested pair
                    rate = raw_rate
                    if series_info["invert"]:
                        rate = 1.0 / rate
                    if is_inverse:
                        rate = 1.0 / rate

                    return {
                        "rate": rate,
                        "date": ref_date,
                        "source": "FRED"
                    }

        except Exception as e:
            print(f"Error fetching FRED rate: {e}")

    return None


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
                        "timestamp": datetime.now().isoformat(),
                        "source": "ExchangeRate-API"
                    }
                    _rate_cache[cache_key] = {"data": result, "cached_at": now}
                    return result

            # Fallback to Frankfurter API (free, no key needed - uses ECB data)
            url = f"{FRANKFURTER_BASE_URL}/latest?from={base}&to={quote}"
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                result = {
                    "base": base,
                    "quote": quote,
                    "rate": data["rates"].get(quote, 0),
                    "timestamp": datetime.now().isoformat(),
                    "source": "Frankfurter (ECB)"
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

    # Get market rate
    result = await get_current_rate(base, quote)

    # Fetch official rates based on currency pair
    # ECB rate for EUR-based pairs
    ecb_rate = await get_ecb_rate(base, quote)
    if ecb_rate:
        result["ecb_rate"] = ecb_rate["rate"]
        result["ecb_date"] = ecb_rate["date"]
        result["ecb_source"] = ecb_rate["source"]

    # FRED rate for USD-based pairs
    fred_rate = await get_fred_rate(base, quote)
    if fred_rate:
        result["fred_rate"] = fred_rate["rate"]
        result["fred_date"] = fred_rate["date"]
        result["fred_source"] = fred_rate["source"]

    return result


async def get_fred_history(base: str, quote: str, days: int) -> Optional[list]:
    """Get historical rates from FRED for USD-based pairs"""
    if not FRED_API_KEY:
        return None

    # Check if we have this pair in FRED series
    pair_key = (base, quote)
    inverse_key = (quote, base)

    series_info = None
    is_inverse = False

    if pair_key in FRED_SERIES:
        series_info = FRED_SERIES[pair_key]
    elif inverse_key in FRED_SERIES:
        series_info = FRED_SERIES[inverse_key]
        is_inverse = True

    if not series_info:
        return None

    series_id = series_info["series"]

    async with httpx.AsyncClient() as client:
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            params = {
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "observation_start": start_date.strftime("%Y-%m-%d"),
                "observation_end": end_date.strftime("%Y-%m-%d"),
                "sort_order": "asc"
            }
            response = await client.get(FRED_BASE_URL, params=params, timeout=15.0)

            if response.status_code == 200:
                data = response.json()
                observations = data.get("observations", [])

                history = []
                for obs in observations:
                    if obs.get("value") != ".":
                        raw_rate = float(obs["value"])
                        # Apply inversions
                        rate = raw_rate
                        if series_info["invert"]:
                            rate = 1.0 / rate
                        if is_inverse:
                            rate = 1.0 / rate
                        history.append({
                            "date": obs["date"],
                            "rate": rate
                        })

                return history if history else None

        except Exception as e:
            print(f"Error fetching FRED history: {e}")

    return None


@router.get("/{base}/{quote}/history")
async def get_history(base: str, quote: str, days: Optional[int] = 90):
    """Get historical exchange rate data from ECB and FRED"""
    base = base.upper()
    quote = quote.upper()

    result = {
        "source": "ECB",
        "daily": None,
        "threeMonth": None
    }

    # Fetch ECB history (via Frankfurter)
    ecb_history = None
    async with httpx.AsyncClient() as client:
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            url = f"{FRANKFURTER_BASE_URL}/{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}?from={base}&to={quote}"
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                rates_data = data.get("rates", {})

                ecb_history = []
                for date_str, rates in sorted(rates_data.items()):
                    if quote in rates:
                        ecb_history.append({
                            "date": date_str,
                            "rate": rates[quote]
                        })

        except Exception as e:
            print(f"Error fetching ECB history: {e}")

    # Fetch FRED history for USD-based pairs
    fred_history = await get_fred_history(base, quote, days)

    # Determine which source to use as primary (USD base = FRED, others = ECB)
    is_usd_base = base == "USD"

    if is_usd_base and fred_history:
        primary_history = fred_history
        result["source"] = "FRED"
        result["ecb_history"] = ecb_history  # Include ECB as secondary
    else:
        primary_history = ecb_history
        result["source"] = "ECB"
        if fred_history:
            result["fred_history"] = fred_history  # Include FRED as secondary

    if primary_history:
        # Calculate daily data
        daily_data = primary_history[-5:] if len(primary_history) >= 5 else primary_history
        daily_open = daily_data[0]["rate"] if daily_data else 0
        daily_close = daily_data[-1]["rate"] if daily_data else 0

        # Calculate period data
        period_open = primary_history[0]["rate"] if primary_history else 0
        period_close = primary_history[-1]["rate"] if primary_history else 0

        result["daily"] = {
            "open": daily_open,
            "close": daily_close,
            "data": [{"time": d["date"], "rate": d["rate"]} for d in daily_data]
        }
        result["threeMonth"] = {
            "open": period_open,
            "close": period_close,
            "data": primary_history
        }

        return result

    raise HTTPException(status_code=503, detail="Unable to fetch historical data")
