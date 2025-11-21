#!/usr/bin/env python3
"""
Agent AI Client - Unified interface for AI models in trading agents
Supports Ollama (unlimited) and RapidAPI (500/month) with smart routing
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("agent_ai")

# Try to import requests
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("⚠️ requests not available - install with: pip install requests")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = "deepseek-r1:7b"  # Best for reasoning
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "f89c81c096msh0e367842c4a9cedp172050jsn8f96a4f06504")
RAPIDAPI_LLAMA_URL = "https://open-ai21.p.rapidapi.com/conversationllama"
RAPIDAPI_CLAUDE_URL = "https://claude-ai-all-models.p.rapidapi.com/chat/completions"

# Track RapidAPI usage
_rapidapi_usage_file = Path(__file__).parent.parent / "runtime" / "rapidapi_usage.json"
RAPIDAPI_MONTHLY_LIMIT = 500


def load_rapidapi_usage() -> dict[str, Any]:
    """Load RapidAPI usage tracking"""
    if _rapidapi_usage_file.exists():
        try:
            return json.loads(_rapidapi_usage_file.read_text())
        except Exception:
            pass
    return {"month": None, "count": 0}


def save_rapidapi_usage(usage: dict[str, Any]) -> None:
    """Save RapidAPI usage tracking"""
    try:
        _rapidapi_usage_file.parent.mkdir(parents=True, exist_ok=True)
        _rapidapi_usage_file.write_text(json.dumps(usage, indent=2))
    except Exception as e:
        logger.warning(f"⚠️ Could not save RapidAPI usage: {e}")


def check_rapidapi_quota() -> tuple[bool, int]:
    """Check if RapidAPI quota is available"""
    usage = load_rapidapi_usage()
    current_month = time.strftime("%Y-%m")

    # Reset if new month
    if usage.get("month") != current_month:
        usage = {"month": current_month, "count": 0}
        save_rapidapi_usage(usage)

    count = usage.get("count", 0)
    available = count < RAPIDAPI_MONTHLY_LIMIT
    remaining = max(0, RAPIDAPI_MONTHLY_LIMIT - count)

    return available, remaining


def increment_rapidapi_usage() -> None:
    """Increment RapidAPI usage counter"""
    usage = load_rapidapi_usage()
    usage["count"] = usage.get("count", 0) + 1
    save_rapidapi_usage(usage)


def query_ollama(prompt: str, model: str = OLLAMA_MODEL, timeout: int = 30) -> str | None:
    """
    Query Ollama for AI analysis (unlimited, local).
    
    Args:
        prompt: The prompt/question
        model: Ollama model name (default: deepseek-r1:7b)
        timeout: Request timeout in seconds
    
    Returns:
        Response text or None if failed
    """
    if not HAS_REQUESTS:
        logger.warning("⚠️ requests not available - cannot query Ollama")
        return None

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            },
            timeout=timeout
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            logger.warning(f"⚠️ Ollama request failed: {response.status_code}")
            return None

    except requests.exceptions.ConnectionError:
        logger.warning("⚠️ Ollama not running - start with: ollama serve")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Ollama query failed: {e}")
        return None


def query_rapidapi_llama(prompt: str, timeout: int = 30) -> str | None:
    """
    Query RapidAPI Llama 3.3 70B (500/month limit).
    
    Args:
        prompt: The prompt/question
        timeout: Request timeout in seconds
    
    Returns:
        Response text or None if failed
    """
    if not HAS_REQUESTS:
        return None

    # Check quota
    available, remaining = check_rapidapi_quota()
    if not available:
        logger.warning(f"⚠️ RapidAPI quota exhausted ({RAPIDAPI_MONTHLY_LIMIT}/month)")
        return None

    try:
        response = requests.post(
            RAPIDAPI_LLAMA_URL,
            headers={
                "x-rapidapi-host": "open-ai21.p.rapidapi.com",
                "x-rapidapi-key": RAPIDAPI_KEY,
                "Content-Type": "application/json"
            },
            json={
                "messages": [{"role": "user", "content": prompt}],
                "web_access": False
            },
            timeout=timeout
        )

        if response.status_code == 200:
            result = response.json()
            increment_rapidapi_usage()
            logger.debug(f"✅ RapidAPI used ({remaining - 1} remaining this month)")

            # Parse response (format may vary)
            if isinstance(result, dict):
                return result.get("response") or result.get("message") or str(result)
            return str(result)
        else:
            logger.warning(f"⚠️ RapidAPI request failed: {response.status_code}")
            return None

    except Exception as e:
        logger.warning(f"⚠️ RapidAPI query failed: {e}")
        return None


def query_rapidapi_claude(prompt: str, model: str = "claude-sonnet-4", timeout: int = 30) -> str | None:
    """
    Query RapidAPI Claude (500/month limit).
    
    Args:
        prompt: The prompt/question
        model: Claude model name (default: claude-sonnet-4)
        timeout: Request timeout in seconds
    
    Returns:
        Response text or None if failed
    """
    if not HAS_REQUESTS:
        return None

    # Check quota
    available, remaining = check_rapidapi_quota()
    if not available:
        logger.warning(f"⚠️ RapidAPI quota exhausted ({RAPIDAPI_MONTHLY_LIMIT}/month)")
        return None

    try:
        response = requests.post(
            RAPIDAPI_CLAUDE_URL,
            headers={
                "x-rapidapi-host": "claude-ai-all-models.p.rapidapi.com",
                "x-rapidapi-key": RAPIDAPI_KEY,
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000
            },
            timeout=timeout
        )

        if response.status_code == 200:
            result = response.json()
            increment_rapidapi_usage()
            logger.debug(f"✅ RapidAPI Claude used ({remaining - 1} remaining this month)")

            # Parse response
            if isinstance(result, dict):
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0].get("message", {}).get("content", "")
                return result.get("response") or result.get("message") or str(result)
            return str(result)
        else:
            logger.warning(f"⚠️ RapidAPI Claude request failed: {response.status_code}")
            return None

    except Exception as e:
        logger.warning(f"⚠️ RapidAPI Claude query failed: {e}")
        return None


def analyze_trading_signal(
    symbol: str,
    price: float,
    indicators: dict[str, Any],
    use_rapidapi: bool = False
) -> dict[str, Any] | None:
    """
    Analyze trading signal using AI (smart routing).
    
    Args:
        symbol: Trading symbol
        price: Current price
        indicators: Technical indicators (RSI, momentum, etc.)
        use_rapidapi: Force RapidAPI (for critical decisions)
    
    Returns:
        Analysis dict with signal, confidence, reasoning
    """
    prompt = f"""Analyze trading signal for {symbol}:

Price: ${price:.2f}
RSI: {indicators.get('rsi', 'N/A')}
Momentum: {indicators.get('momentum', 'N/A')}%
MACD: {indicators.get('macd', 'N/A')}

Provide:
1. Signal recommendation (BUY/SELL/HOLD)
2. Confidence (0.0-1.0)
3. Risk assessment (LOW/MEDIUM/HIGH)
4. Brief reasoning (1-2 sentences)

Respond in JSON format:
{{"signal": "BUY|SELL|HOLD", "confidence": 0.0-1.0, "risk": "LOW|MEDIUM|HIGH", "reasoning": "..."}}
"""

    # Smart routing: Use RapidAPI for critical decisions, Ollama for daily
    if use_rapidapi:
        logger.info(f"🤖 Using RapidAPI for critical analysis: {symbol}")
        response = query_rapidapi_llama(prompt)
        if not response:
            # Fallback to Ollama
            response = query_ollama(prompt)
    else:
        logger.debug(f"🤖 Using Ollama for analysis: {symbol}")
        response = query_ollama(prompt)
        # If Ollama fails, try RapidAPI as fallback
        if not response:
            logger.info(f"🤖 Ollama failed, using RapidAPI fallback: {symbol}")
            response = query_rapidapi_llama(prompt)

    if not response:
        return None

    # Try to parse JSON response
    try:
        # Extract JSON from response if wrapped in text
        if "{" in response and "}" in response:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            json_str = response[json_start:json_end]
            return json.loads(json_str)
    except Exception:
        pass

    # Fallback: return raw response
    return {
        "signal": "HOLD",
        "confidence": 0.5,
        "risk": "MEDIUM",
        "reasoning": response[:200]  # First 200 chars
    }


def assess_risk(
    symbol: str,
    position_size: float,
    portfolio_value: float,
    market_conditions: dict[str, Any],
    use_rapidapi: bool = False
) -> dict[str, Any] | None:
    """
    Assess risk using AI (smart routing).
    
    Args:
        symbol: Trading symbol
        position_size: Position size in dollars
        portfolio_value: Total portfolio value
        market_conditions: Market conditions dict
        use_rapidapi: Force RapidAPI (for critical risk assessment)
    
    Returns:
        Risk assessment dict
    """
    prompt = f"""Assess risk for {symbol} position:

Position Size: ${position_size:,.2f}
Portfolio Value: ${portfolio_value:,.2f}
Position %: {(position_size/portfolio_value*100):.2f}%
Market Conditions: {json.dumps(market_conditions, indent=2)}

Provide:
1. Risk level (LOW/MEDIUM/HIGH/CRITICAL)
2. Recommended action (INCREASE/REDUCE/HOLD/EXIT)
3. Max position size recommendation
4. Reasoning

Respond in JSON format:
{{"risk_level": "LOW|MEDIUM|HIGH|CRITICAL", "action": "INCREASE|REDUCE|HOLD|EXIT", "max_position": "$", "reasoning": "..."}}
"""

    if use_rapidapi:
        response = query_rapidapi_claude(prompt, model="claude-sonnet-4")
    else:
        response = query_ollama(prompt)
        if not response:
            response = query_rapidapi_claude(prompt, model="claude-sonnet-4")

    if not response:
        return None

    # Try to parse JSON
    try:
        if "{" in response and "}" in response:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            json_str = response[json_start:json_end]
            return json.loads(json_str)
    except Exception:
        pass

    return {
        "risk_level": "MEDIUM",
        "action": "HOLD",
        "max_position": position_size,
        "reasoning": response[:200]
    }


def get_rapidapi_status() -> dict[str, Any]:
    """Get RapidAPI usage status"""
    usage = load_rapidapi_usage()
    available, remaining = check_rapidapi_quota()

    return {
        "month": usage.get("month", "Unknown"),
        "used": usage.get("count", 0),
        "limit": RAPIDAPI_MONTHLY_LIMIT,
        "remaining": remaining,
        "available": available
    }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("🤖 Agent AI Client Test")
    print("=" * 50)

    # Test Ollama
    print("\n1. Testing Ollama (DeepSeek R1)...")
    result = query_ollama("What is RSI in trading?")
    if result:
        print(f"✅ Ollama response: {result[:100]}...")
    else:
        print("❌ Ollama failed")

    # Test RapidAPI status
    print("\n2. RapidAPI Status:")
    status = get_rapidapi_status()
    print(f"   Month: {status['month']}")
    print(f"   Used: {status['used']}/{status['limit']}")
    print(f"   Remaining: {status['remaining']}")

    # Test trading signal analysis
    print("\n3. Testing Trading Signal Analysis...")
    analysis = analyze_trading_signal(
        symbol="BTC-USD",
        price=50000.0,
        indicators={"rsi": 65.0, "momentum": 2.5},
        use_rapidapi=False  # Use Ollama (unlimited)
    )
    if analysis:
        print(f"✅ Analysis: {analysis}")
    else:
        print("❌ Analysis failed")

