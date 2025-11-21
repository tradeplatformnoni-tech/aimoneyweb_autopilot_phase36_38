#!/usr/bin/env python3
"""
NeoLight Multi-AI Research Assistant
====================================
Unified interface for multiple AI providers (OpenAI, Anthropic, Mistral, Google, Groq)
Provides research, code analysis, and development assistance for NeoLight.

Features:
- Multi-provider support with automatic fallback
- Research assistance for trading strategies
- Code analysis and optimization
- Autonomous development suggestions
- Performance optimization recommendations
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger("research_assistant")

# Try to import all AI SDKs
AI_PROVIDERS = {}

try:
    import openai

    AI_PROVIDERS["openai"] = openai
except ImportError:
    pass

try:
    import anthropic

    AI_PROVIDERS["anthropic"] = anthropic
except ImportError:
    pass

try:
    from mistralai import Mistral

    AI_PROVIDERS["mistral"] = Mistral
except ImportError:
    pass

try:
    import google.generativeai as genai

    AI_PROVIDERS["google"] = genai
except ImportError:
    pass

try:
    from groq import Groq

    AI_PROVIDERS["groq"] = Groq
except ImportError:
    pass


class NeoLightResearchAssistant:
    """
    Multi-AI Research Assistant for NeoLight
    Supports OpenAI, Anthropic Claude, Mistral, Google Gemini, Groq
    """

    def __init__(self):
        self.providers = {}
        self.provider_order = []

        # Initialize available providers
        self._init_providers()

    def _init_providers(self):
        """Initialize available AI providers"""
        # OpenAI
        if "openai" in AI_PROVIDERS:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.providers["openai"] = {
                    "client": AI_PROVIDERS["openai"],
                    "api_key": api_key,
                    "model": "gpt-4-turbo-preview",
                }
                self.provider_order.append("openai")
                logger.info("✅ OpenAI configured")

        # Anthropic Claude
        if "anthropic" in AI_PROVIDERS:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.providers["anthropic"] = {
                    "client": AI_PROVIDERS["anthropic"],
                    "api_key": api_key,
                    "model": "claude-3-opus-20240229",
                }
                self.provider_order.append("anthropic")
                logger.info("✅ Anthropic Claude configured")

        # Mistral
        if "mistral" in AI_PROVIDERS:
            api_key = os.getenv("MISTRAL_API_KEY")
            if api_key:
                self.providers["mistral"] = {
                    "client": AI_PROVIDERS["mistral"],
                    "api_key": api_key,
                    "model": "mistral-large-latest",
                }
                self.provider_order.append("mistral")
                logger.info("✅ Mistral configured")

        # Google Gemini
        if "google" in AI_PROVIDERS:
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.providers["google"] = {
                    "client": genai,
                    "api_key": api_key,
                    "model": "gemini-pro",
                }
                self.provider_order.append("google")
                logger.info("✅ Google Gemini configured")

        # Groq (fast, free tier available)
        if "groq" in AI_PROVIDERS:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                self.providers["groq"] = {
                    "client": Groq(api_key=api_key),
                    "api_key": api_key,
                    "model": "llama-3-70b-8192",
                }
                self.provider_order.append("groq")
                logger.info("✅ Groq configured")

        # Ollama (local, unlimited)
        ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        if HAS_REQUESTS:
            try:
                import requests
                # Test if Ollama is running
                test_response = requests.get(f"{ollama_base}/api/tags", timeout=2)
                if test_response.status_code == 200:
                    self.providers["ollama"] = {
                        "base_url": ollama_base,
                        "model": "deepseek-r1:7b",
                        "available": True,
                    }
                    self.provider_order.insert(0, "ollama")  # Prioritize Ollama
                    logger.info("✅ Ollama configured (unlimited, local)")
            except Exception:
                logger.debug("⚠️ Ollama not available (start with: ollama serve)")

        # RapidAPI (500/month limit)
        rapidapi_key = os.getenv("RAPIDAPI_KEY")
        if rapidapi_key and HAS_REQUESTS:
            self.providers["rapidapi"] = {
                "api_key": rapidapi_key,
                "llama_url": "https://open-ai21.p.rapidapi.com/conversationllama",
                "claude_url": "https://claude-ai-all-models.p.rapidapi.com/chat/completions",
                "available": True,
            }
            self.provider_order.append("rapidapi")
            logger.info("✅ RapidAPI configured (500/month limit)")

        if not self.providers:
            logger.warning("⚠️ No AI providers configured. Set API keys in environment variables.")

    def research(
        self,
        query: str,
        context: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        provider: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Conduct research using available AI providers with automatic fallback.

        Args:
            query: Research question
            context: Optional context
            max_tokens: Maximum response tokens
            temperature: Creativity (0.0-1.0)
            provider: Specific provider to use (optional)

        Returns:
            Dict with 'content', 'provider', 'model', etc.
        """
        if not self.providers:
            logger.error("❌ No AI providers available")
            return None

        providers_to_try = (
            [provider] if provider and provider in self.providers else self.provider_order
        )

        for prov_name in providers_to_try:
            try:
                result = self._query_provider(prov_name, query, context, max_tokens, temperature)
                if result:
                    result["provider"] = prov_name
                    return result
            except Exception as e:
                logger.warning(f"⚠️ {prov_name} failed: {e}, trying next provider...")
                continue

        logger.error("❌ All AI providers failed")
        return None

    def _query_provider(
        self, provider: str, query: str, context: str | None, max_tokens: int, temperature: float
    ) -> dict[str, Any] | None:
        """Query a specific provider"""
        prov = self.providers[provider]
        system_prompt = """You are NeoLight Research Assistant, an AI expert for the NeoLight autonomous trading system.

NeoLight Architecture:
- Python: AI/ML decision layer (SmartTrader, agents)
- Go: High-speed API & telemetry (dashboard, real-time data)
- Rust: Risk & execution core (risk engine, backtesting)
- Hybrid multi-runtime orchestration

Provide world-class insights on:
1. Trading strategies (RSI, momentum, regime-aware)
2. Code optimization and performance
3. Risk management and capital allocation
4. System architecture improvements

Always provide actionable, production-ready recommendations."""

        user_content = query
        if context:
            user_content = f"Context: {context}\n\nQuery: {query}"

        if provider == "openai":
            client = prov["client"]
            client.api_key = prov["api_key"]
            response = client.chat.completions.create(
                model=prov["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage.dict() if hasattr(response.usage, "dict") else {},
            }

        elif provider == "anthropic":
            client = prov["client"].Anthropic(api_key=prov["api_key"])
            response = client.messages.create(
                model=prov["model"],
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            return {
                "content": response.content[0].text,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }

        elif provider == "mistral":
            client = prov["client"](api_key=prov["api_key"])
            response = client.chat.complete(
                model=prov["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage.dict() if hasattr(response.usage, "dict") else {},
            }

        elif provider == "google":
            model = prov["client"].GenerativeModel(prov["model"])
            prompt = f"{system_prompt}\n\n{user_content}"
            response = model.generate_content(prompt)
            return {"content": response.text, "model": prov["model"], "usage": {}}

        elif provider == "groq":
            client = prov["client"]
            response = client.chat.completions.create(
                model=prov["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage.dict() if hasattr(response.usage, "dict") else {},
            }

        elif provider == "ollama":
            # Ollama local model (unlimited)
            import requests
            response = requests.post(
                f"{prov['base_url']}/api/generate",
                json={
                    "model": prov["model"],
                    "prompt": f"{system_prompt}\n\n{user_content}",
                    "stream": False,
                    "options": {"temperature": temperature}
                },
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                return {
                    "content": result.get("response", "").strip(),
                    "model": prov["model"],
                    "usage": {}
                }
            return None

        elif provider == "rapidapi":
            # RapidAPI (500/month limit) - use Llama 3.3 70B
            import requests
            response = requests.post(
                prov["llama_url"],
                headers={
                    "x-rapidapi-host": "open-ai21.p.rapidapi.com",
                    "x-rapidapi-key": prov["api_key"],
                    "Content-Type": "application/json"
                },
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "web_access": False
                },
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                return {
                    "content": str(result.get("response") or result.get("message") or result),
                    "model": "llama-3.3-70b",
                    "usage": {}
                }
            return None

        return None

    def analyze_code(
        self, code: str, language: str = "python", focus: str = "optimization"
    ) -> str | None:
        """Analyze code with AI assistance"""
        query = f"""Analyze this {language} code for {focus}:

```{language}
{code}
```

Focus on:
1. Performance optimization
2. Security best practices
3. Code quality and maintainability
4. NeoLight architecture alignment
5. Memory and CPU efficiency

Provide actionable recommendations."""

        result = self.research(query, context="Code analysis for NeoLight trading system")
        return result.get("content") if result else None

    def suggest_strategy(self, market_condition: str, indicators: dict | None = None) -> str | None:
        """Suggest trading strategy"""
        query = f"""Market condition: {market_condition}

Indicators: {json.dumps(indicators, indent=2) if indicators else "None"}

Suggest a trading strategy for NeoLight SmartTrader that:
1. Uses RSI + momentum + regime-aware approach
2. Considers Guardian AutoPause risk management
3. Optimizes Sharpe ratio and drawdown control
4. Uses adaptive signal weighting

Provide specific, actionable recommendations."""

        result = self.research(query, context="Trading strategy for NeoLight")
        return result.get("content") if result else None

    def get_available_providers(self) -> list[str]:
        """Get list of available providers"""
        return list(self.providers.keys())


# Singleton instance
_assistant_instance: NeoLightResearchAssistant | None = None


def get_research_assistant() -> NeoLightResearchAssistant:
    """Get singleton research assistant instance"""
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = NeoLightResearchAssistant()
    return _assistant_instance


# Convenience functions
def research(query: str, context: str | None = None, provider: str | None = None) -> str | None:
    """Quick research function"""
    assistant = get_research_assistant()
    result = assistant.research(query, context, provider=provider)
    return result.get("content") if result else None


def analyze_code(code: str, language: str = "python") -> str | None:
    """Quick code analysis"""
    assistant = get_research_assistant()
    return assistant.analyze_code(code, language)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    assistant = get_research_assistant()

    print("🧠 NeoLight Multi-AI Research Assistant")
    print("=" * 50)
    print(f"Available providers: {', '.join(assistant.get_available_providers()) or 'None'}")

    if assistant.get_available_providers():
        result = assistant.research("What are best practices for RSI-based trading?")
        if result:
            print(f"\n✅ Research Result ({result.get('provider', 'unknown')}):")
            print(result.get("content", "")[:300] + "...")
    else:
        print("\n⚠️ No AI providers configured. Set API keys:")
        print("  - OPENAI_API_KEY")
        print("  - ANTHROPIC_API_KEY")
        print("  - MISTRAL_API_KEY")
        print("  - GOOGLE_API_KEY")
        print("  - GROQ_API_KEY")
