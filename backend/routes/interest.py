"""
Interest rate routes
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

# Central bank interest rates (manually maintained - update periodically)
# Data as of February 2026 - includes last decision and date of last change
# last_decision: "up", "down", "unchanged"
INTEREST_RATES = {
    "USD": {
        "rate": 4.25,
        "bank": "Federal Reserve",
        "last_change": "2025-12-18",
        "last_decision": "down",
        "previous_rate": 4.50
    },
    "EUR": {
        "rate": 2.75,
        "bank": "European Central Bank",
        "last_change": "2025-12-12",
        "last_decision": "down",
        "previous_rate": 3.00
    },
    "GBP": {
        "rate": 4.50,
        "bank": "Bank of England",
        "last_change": "2025-11-07",
        "last_decision": "down",
        "previous_rate": 4.75
    },
    "JPY": {
        "rate": 0.50,
        "bank": "Bank of Japan",
        "last_change": "2025-12-19",
        "last_decision": "up",
        "previous_rate": 0.25
    },
    "CHF": {
        "rate": 0.25,
        "bank": "Swiss National Bank",
        "last_change": "2025-12-12",
        "last_decision": "down",
        "previous_rate": 0.50
    },
    "AUD": {
        "rate": 4.10,
        "bank": "Reserve Bank of Australia",
        "last_change": "2025-11-05",
        "last_decision": "down",
        "previous_rate": 4.35
    },
    "CAD": {
        "rate": 3.00,
        "bank": "Bank of Canada",
        "last_change": "2025-12-11",
        "last_decision": "down",
        "previous_rate": 3.25
    },
    "NZD": {
        "rate": 3.75,
        "bank": "Reserve Bank of New Zealand",
        "last_change": "2025-11-27",
        "last_decision": "down",
        "previous_rate": 4.25
    },
    "SEK": {
        "rate": 2.25,
        "bank": "Sveriges Riksbank",
        "last_change": "2025-12-19",
        "last_decision": "down",
        "previous_rate": 2.50
    },
    "NOK": {
        "rate": 4.50,
        "bank": "Norges Bank",
        "last_change": "2024-12-19",
        "last_decision": "unchanged",
        "previous_rate": 4.50
    },
    "DKK": {
        "rate": 2.60,
        "bank": "Danmarks Nationalbank",
        "last_change": "2025-12-12",
        "last_decision": "down",
        "previous_rate": 2.85
    },
    "PLN": {
        "rate": 5.75,
        "bank": "National Bank of Poland",
        "last_change": "2023-10-04",
        "last_decision": "down",
        "previous_rate": 6.00
    },
    "CZK": {
        "rate": 4.00,
        "bank": "Czech National Bank",
        "last_change": "2024-11-07",
        "last_decision": "down",
        "previous_rate": 4.25
    },
    "HUF": {
        "rate": 6.50,
        "bank": "Magyar Nemzeti Bank",
        "last_change": "2024-09-24",
        "last_decision": "down",
        "previous_rate": 6.75
    },
    "CNY": {
        "rate": 3.00,
        "bank": "People's Bank of China",
        "last_change": "2025-10-21",
        "last_decision": "down",
        "previous_rate": 3.10
    },
    "INR": {
        "rate": 6.25,
        "bank": "Reserve Bank of India",
        "last_change": "2025-02-07",
        "last_decision": "down",
        "previous_rate": 6.50
    },
    "MXN": {
        "rate": 9.50,
        "bank": "Banco de Mexico",
        "last_change": "2025-12-19",
        "last_decision": "down",
        "previous_rate": 10.00
    },
    "BRL": {
        "rate": 13.25,
        "bank": "Central Bank of Brazil",
        "last_change": "2025-12-11",
        "last_decision": "up",
        "previous_rate": 12.25
    },
    "ZAR": {
        "rate": 7.50,
        "bank": "South African Reserve Bank",
        "last_change": "2025-11-21",
        "last_decision": "down",
        "previous_rate": 7.75
    },
    "SGD": {
        "rate": 3.25,
        "bank": "Monetary Authority of Singapore",
        "last_change": "2025-10-14",
        "last_decision": "down",
        "previous_rate": 3.50
    },
    "HKD": {
        "rate": 4.50,
        "bank": "Hong Kong Monetary Authority",
        "last_change": "2025-12-19",
        "last_decision": "down",
        "previous_rate": 4.75
    },
    "KRW": {
        "rate": 2.75,
        "bank": "Bank of Korea",
        "last_change": "2025-11-28",
        "last_decision": "down",
        "previous_rate": 3.00
    },
    "TRY": {
        "rate": 45.00,
        "bank": "Central Bank of Turkey",
        "last_change": "2024-03-21",
        "last_decision": "up",
        "previous_rate": 42.50
    }
}


def calculate_days_at_rate(last_change_str: str) -> int:
    """Calculate days since last rate change"""
    last_change = datetime.strptime(last_change_str, "%Y-%m-%d")
    today = datetime.now()
    return (today - last_change).days


@router.get("/{base}/{quote}")
async def get_interest_rates(base: str, quote: str):
    """Get interest rates for both currencies in a pair"""
    base = base.upper()
    quote = quote.upper()

    default_info = {
        "rate": 0,
        "bank": "Unknown",
        "last_change": "N/A",
        "last_decision": "unchanged",
        "previous_rate": 0
    }

    base_info = INTEREST_RATES.get(base, default_info)
    quote_info = INTEREST_RATES.get(quote, default_info)

    # Calculate days at current rate
    base_days = calculate_days_at_rate(base_info["last_change"]) if base_info["last_change"] != "N/A" else 0
    quote_days = calculate_days_at_rate(quote_info["last_change"]) if quote_info["last_change"] != "N/A" else 0

    return {
        "base": base,
        "quote": quote,
        "base_rate": base_info["rate"],
        "base_bank": base_info["bank"],
        "base_last_decision": base_info["last_decision"],
        "base_last_change": base_info["last_change"],
        "base_days_at_rate": base_days,
        "quote_rate": quote_info["rate"],
        "quote_bank": quote_info["bank"],
        "quote_last_decision": quote_info["last_decision"],
        "quote_last_change": quote_info["last_change"],
        "quote_days_at_rate": quote_days,
        "differential": base_info["rate"] - quote_info["rate"]
    }


@router.get("/")
async def get_all_rates():
    """Get all interest rates with additional info"""
    result = {}
    for currency, info in INTEREST_RATES.items():
        days = calculate_days_at_rate(info["last_change"])
        result[currency] = {
            **info,
            "days_at_rate": days
        }
    return result
