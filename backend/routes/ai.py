"""
AI Analysis routes using Claude API with Web Research
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import httpx
import os
import json
import asyncio

router = APIRouter()

# Anthropic API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Cache for AI analysis (1 hour TTL)
_ai_cache = {}
_ai_cache_ttl = 3600

# Major financial news sources for web research
SEARCH_QUERIES = [
    "{pair} forecast analyst outlook",
    "{pair} technical analysis today",
    "{pair} {base} {quote} bank forecast",
    "{pair} sentiment weekly"
]


async def get_market_context(base: str, quote: str) -> dict:
    """Gather market context for AI analysis"""
    # Import here to avoid circular imports
    from backend.routes.rates import get_current_rate
    from backend.routes.interest import INTEREST_RATES

    try:
        rate_data = await get_current_rate(base, quote)
        rate = rate_data["rate"]
    except:
        rate = None

    base_interest = INTEREST_RATES.get(base, {}).get("rate", 0)
    quote_interest = INTEREST_RATES.get(quote, {}).get("rate", 0)

    return {
        "pair": f"{base}/{quote}",
        "current_rate": rate,
        "base_interest_rate": base_interest,
        "quote_interest_rate": quote_interest,
        "interest_differential": base_interest - quote_interest,
        "timestamp": datetime.now().isoformat()
    }


def build_analysis_prompt(
    context: dict,
    short_term_focus: str = "",
    long_term_focus: str = "",
    style: str = "balanced",
    depth: str = "standard",
    sources: str = "interest_rates,central_banks,economic,technical",
    for_web_search: bool = False
) -> str:
    """Build prompt for Claude API with full customization"""

    # Style modifiers
    style_instructions = {
        "balanced": "Provide a balanced analysis considering both technical and fundamental factors.",
        "technical": "Focus heavily on technical analysis, chart patterns, support/resistance levels, and momentum indicators.",
        "fundamental": "Focus on fundamental factors: economic data, central bank policies, trade balances, and macroeconomic trends.",
        "risk": "Focus on risk assessment, potential volatility, key risk events, and hedging considerations.",
        "brief": "Keep your analysis concise and to the point. Prioritize actionable insights."
    }

    # Depth modifiers
    depth_instructions = {
        "standard": "Provide key insights with moderate detail.",
        "detailed": "Provide comprehensive analysis with extensive reasoning and multiple factors.",
        "brief": "Keep responses short and focused on the most critical points only."
    }

    style_text = style_instructions.get(style, style_instructions["balanced"])
    depth_text = depth_instructions.get(depth, depth_instructions["standard"])

    # Build sources list
    source_list = sources.split(',') if sources else []
    source_items = []
    if 'interest_rates' in source_list:
        source_items.append("Interest rate differentials and carry trade dynamics")
    if 'central_banks' in source_list:
        source_items.append("Central bank policies and monetary policy outlook")
    if 'economic' in source_list:
        source_items.append("Economic conditions and growth differentials")
    if 'technical' in source_list:
        source_items.append("Technical factors and market sentiment")

    sources_text = "\n".join(f"- {s}" for s in source_items) if source_items else "- General market factors"

    # Custom focus areas
    short_focus_text = f"\n\nAdditional short-term focus: {short_term_focus}" if short_term_focus else ""
    long_focus_text = f"\n\nAdditional long-term focus: {long_term_focus}" if long_term_focus else ""

    if for_web_search:
        intro = f"""You are a professional FX analyst. Analyze the {context['pair']} currency pair based on the web research provided below."""
        research_instructions = f"""
Base your analysis on the web research findings, focusing on:
{sources_text}

IMPORTANT: Include analyst sentiment, specific price targets, and forecasts from the research."""
        source_instructions = """
Requirements:
- Use REAL sources from the web research - do not make up URLs
- Cite specific price targets or levels when available
- Mention specific analysts or institutions when referenced"""
    else:
        intro = f"""You are a professional FX analyst. Analyze the {context['pair']} currency pair."""
        research_instructions = f"""
Base your analysis on:
{sources_text}"""
        source_instructions = """
Requirements:
- Provide relevant financial news sources (Reuters, Bloomberg, FXStreet, etc.)"""

    return f"""{intro}

Current Market Data:
- Currency Pair: {context['pair']}
- Current Rate: {context['current_rate']}
- {context['pair'].split('/')[0]} Interest Rate: {context['base_interest_rate']}%
- {context['pair'].split('/')[1]} Interest Rate: {context['quote_interest_rate']}%
- Interest Rate Differential: {context['interest_differential']:.2f}%

Analysis Style: {style_text}
Detail Level: {depth_text}
{research_instructions}{short_focus_text}{long_focus_text}

Provide analysis in this JSON format:
{{
    "shortTerm": {{
        "trend": "Bullish" | "Bearish" | "Neutral",
        "summary": "1-2 sentence short-term (1-7 day) outlook",
        "details": "Detailed paragraph with reasoning",
        "sources": [{{"name": "Source", "url": "https://..."}}]
    }},
    "longTerm": {{
        "trend": "Bullish" | "Bearish" | "Neutral",
        "summary": "1-2 sentence mid/long-term (1-3 month) outlook",
        "details": "Detailed paragraph with reasoning",
        "sources": [{{"name": "Source", "url": "https://..."}}]
    }}
}}
{source_instructions}

Return ONLY valid JSON."""


async def call_claude_api_with_search(prompt: str, pair: str) -> dict:
    """Call Claude API with web search enabled for real-time market analysis"""
    if not ANTHROPIC_API_KEY:
        return get_mock_analysis()

    async with httpx.AsyncClient() as client:
        try:
            # First, use Claude with web search to gather market intelligence
            research_prompt = f"""Research the current market outlook for {pair}. Search for:

1. Recent analyst forecasts and price targets from major banks (Goldman Sachs, JP Morgan, Deutsche Bank, UBS, etc.)
2. Current technical analysis levels (support, resistance, trend)
3. Fundamental factors affecting this pair right now
4. Market sentiment from financial news (Reuters, Bloomberg, FXStreet, Investing.com)

Summarize the key findings from your web research."""

            # Call with web search tool - using server-side tool
            research_response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4096,
                    "tools": [
                        {
                            "type": "web_search_20250305",
                            "name": "web_search",
                            "max_uses": 5
                        }
                    ],
                    "messages": [
                        {"role": "user", "content": research_prompt}
                    ]
                },
                timeout=90.0
            )

            web_research = ""
            sources_found = []

            if research_response.status_code == 200:
                research_data = research_response.json()
                print(f"Research response stop_reason: {research_data.get('stop_reason')}")

                # Extract all text content and web search results from response
                for block in research_data.get("content", []):
                    if block.get("type") == "text":
                        web_research += block.get("text", "") + "\n"
                    elif block.get("type") == "web_search_tool_result":
                        # Extract search results
                        for result in block.get("content", []):
                            if result.get("type") == "web_search_result":
                                sources_found.append({
                                    "title": result.get("title", ""),
                                    "url": result.get("url", ""),
                                    "snippet": result.get("encrypted_content", result.get("content", ""))[:200]
                                })

                if sources_found:
                    web_research += "\n\nSources found:\n"
                    for src in sources_found[:8]:
                        web_research += f"- {src['title']}: {src['url']}\n"

            else:
                print(f"Web search API error: {research_response.status_code} - {research_response.text}")

            # Truncate research to avoid rate limits (keep most relevant ~4000 chars)
            if len(web_research) > 4000:
                web_research = web_research[:4000] + "\n... (truncated)"

            # Now generate structured analysis using the research
            analysis_prompt = f"""{prompt}

--- WEB RESEARCH FINDINGS ---
{web_research if web_research else "No web research available. Base analysis on general market knowledge."}
--- END RESEARCH ---

Based on the web research above, provide your analysis. Use REAL URLs from the sources listed above. Return ONLY valid JSON."""

            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1500,
                    "messages": [
                        {"role": "user", "content": analysis_prompt}
                    ]
                },
                timeout=45.0
            )

            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"]
                # Try to extract JSON from the response
                # Sometimes the model might wrap it in markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                return json.loads(content)
            else:
                print(f"Claude API error: {response.status_code} - {response.text}")
                return get_mock_analysis()

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Content was: {content[:500] if 'content' in dir() else 'N/A'}")
            return get_mock_analysis()
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            import traceback
            traceback.print_exc()
            return get_mock_analysis()


def get_mock_analysis() -> dict:
    """Return mock analysis when API is unavailable"""
    return {
        "shortTerm": {
            "trend": "Neutral",
            "summary": "Market conditions suggest a consolidation phase in the short term. Watch for upcoming economic data releases.",
            "details": "The currency pair is currently trading within a defined range. Key factors to monitor include central bank communications, employment data, and inflation figures. The interest rate differential provides some support, but market sentiment remains cautious ahead of major economic releases.",
            "sources": [
                {"name": "Market Analysis (Demo)", "url": "https://example.com"}
            ]
        },
        "longTerm": {
            "trend": "Neutral",
            "summary": "Medium-term outlook depends on monetary policy divergence between the two central banks.",
            "details": "Over the next 1-3 months, the direction will likely be determined by central bank policy decisions and economic growth differentials. Current interest rate spreads suggest potential for carry trade flows, but geopolitical factors and global risk appetite will also play significant roles in determining the trend.",
            "sources": [
                {"name": "Economic Outlook (Demo)", "url": "https://example.com"}
            ]
        }
    }


async def call_claude_api_simple(prompt: str) -> dict:
    """Call Claude API without web search (faster, uses less tokens)"""
    if not ANTHROPIC_API_KEY:
        print("No API key configured")
        return get_mock_analysis()

    async with httpx.AsyncClient() as client:
        try:
            print(f"Calling Claude API (simple mode)...")
            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30.0
            )

            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"]
                print(f"Got response, content length: {len(content)}")
                # Handle markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                return json.loads(content)
            else:
                print(f"Claude API error: {response.status_code} - {response.text[:500]}")
                return get_mock_analysis()

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Content was: {content[:300] if 'content' in dir() else 'N/A'}")
            return get_mock_analysis()
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            import traceback
            traceback.print_exc()
            return get_mock_analysis()


@router.get("/analyze/{base}/{quote}")
async def analyze_pair(
    base: str,
    quote: str,
    short_term_focus: str = "",
    long_term_focus: str = "",
    style: str = "balanced",
    depth: str = "standard",
    sources: str = "interest_rates,central_banks,economic,technical",
    use_web_search: bool = False
):
    """Get AI analysis for a currency pair with full customization"""
    base = base.upper()
    quote = quote.upper()
    pair = f"{base}/{quote}"

    # Include all settings in cache key
    settings_hash = hash(f"{short_term_focus}{long_term_focus}{style}{depth}{sources}{use_web_search}")
    cache_key = f"{base}_{quote}_{settings_hash}"
    now = datetime.now()

    # Check cache
    if cache_key in _ai_cache:
        cached = _ai_cache[cache_key]
        if (now - cached["cached_at"]).seconds < _ai_cache_ttl:
            return cached["data"]

    # Get market context
    context = await get_market_context(base, quote)

    # Build prompt with all custom settings
    prompt = build_analysis_prompt(
        context,
        short_term_focus=short_term_focus,
        long_term_focus=long_term_focus,
        style=style,
        depth=depth,
        sources=sources,
        for_web_search=use_web_search
    )

    # Call API - with or without web search
    if use_web_search:
        analysis = await call_claude_api_with_search(prompt, pair)
    else:
        analysis = await call_claude_api_simple(prompt)

    # Cache result
    _ai_cache[cache_key] = {"data": analysis, "cached_at": now}

    return analysis
