#!/usr/bin/env python3
"""
AI Browser Assistant - Autonomous Web Problem Solver
Uses AI to control browsers, navigate websites, and solve problems automatically.
"""

import os
import time
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Try Playwright (alternative, more modern)
try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class AIBrowserAssistant:
    """
    AI-powered browser assistant that can:
    - Navigate websites
    - Fill forms
    - Click buttons
    - Extract data
    - Solve common problems
    - Take screenshots
    """

    def __init__(self, headless: bool = False, use_playwright: bool = True):
        self.headless = headless
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self.driver = None
        self.page = None
        self.browser = None

    def start(self):
        """Start browser session."""
        if self.use_playwright:
            self._start_playwright()
        else:
            self._start_selenium()

    def _start_playwright(self):
        """Start Playwright browser (recommended - faster, more reliable)."""
        if not PLAYWRIGHT_AVAILABLE:
            print(
                "[ai_browser] ⚠️ Playwright not installed. Install: pip install playwright",
                flush=True,
            )
            return False

        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=self.headless, args=["--disable-blink-features=AutomationControlled"]
            )
            context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            self.page = context.new_page()
            print("[ai_browser] ✅ Browser started with Playwright", flush=True)
            return True
        except Exception as e:
            print(f"[ai_browser] ❌ Failed to start Playwright: {e}", flush=True)
            return False

    def _start_selenium(self):
        """Start Selenium browser (fallback)."""
        if not SELENIUM_AVAILABLE:
            print("[ai_browser] ⚠️ Selenium not available", flush=True)
            return False

        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            print("[ai_browser] ✅ Browser started with Selenium", flush=True)
            return True
        except Exception as e:
            print(f"[ai_browser] ❌ Failed to start Selenium: {e}", flush=True)
            return False

    def navigate(self, url: str) -> bool:
        """Navigate to URL."""
        try:
            if self.use_playwright and self.page:
                self.page.goto(url, wait_until="networkidle", timeout=30000)
                print(f"[ai_browser] ✅ Navigated to: {url}", flush=True)
                return True
            elif self.driver:
                self.driver.get(url)
                time.sleep(2)
                print(f"[ai_browser] ✅ Navigated to: {url}", flush=True)
                return True
            return False
        except Exception as e:
            print(f"[ai_browser] ❌ Navigation failed: {e}", flush=True)
            return False

    def click(self, selector: str, timeout: int = 10) -> bool:
        """Click element by selector."""
        try:
            if self.use_playwright and self.page:
                self.page.click(selector, timeout=timeout * 1000)
                print(f"[ai_browser] ✅ Clicked: {selector}", flush=True)
                return True
            elif self.driver:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                element.click()
                print(f"[ai_browser] ✅ Clicked: {selector}", flush=True)
                return True
            return False
        except Exception as e:
            print(f"[ai_browser] ⚠️ Click failed: {e}", flush=True)
            return False

    def fill_input(self, selector: str, text: str, timeout: int = 10) -> bool:
        """Fill input field with text."""
        try:
            if self.use_playwright and self.page:
                self.page.fill(selector, text, timeout=timeout * 1000)
                print(f"[ai_browser] ✅ Filled {selector} with text", flush=True)
                return True
            elif self.driver:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                element.clear()
                element.send_keys(text)
                print(f"[ai_browser] ✅ Filled {selector} with text", flush=True)
                return True
            return False
        except Exception as e:
            print(f"[ai_browser] ⚠️ Fill failed: {e}", flush=True)
            return False

    def get_text(self, selector: str, timeout: int = 10) -> str | None:
        """Get text from element."""
        try:
            if self.use_playwright and self.page:
                text = self.page.text_content(selector, timeout=timeout * 1000)
                return text
            elif self.driver:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                return element.text
            return None
        except Exception as e:
            print(f"[ai_browser] ⚠️ Get text failed: {e}", flush=True)
            return None

    def screenshot(self, filename: str = None) -> str | None:
        """Take screenshot."""
        try:
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"

            screenshot_path = LOGS / filename

            if self.use_playwright and self.page:
                self.page.screenshot(path=str(screenshot_path))
            elif self.driver:
                self.driver.save_screenshot(str(screenshot_path))

            print(f"[ai_browser] ✅ Screenshot saved: {screenshot_path}", flush=True)
            return str(screenshot_path)
        except Exception as e:
            print(f"[ai_browser] ⚠️ Screenshot failed: {e}", flush=True)
            return None

    def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """Wait for element to appear."""
        try:
            if self.use_playwright and self.page:
                self.page.wait_for_selector(selector, timeout=timeout * 1000)
                return True
            elif self.driver:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                return True
            return False
        except Exception:
            return False

    def get_current_url(self) -> str | None:
        """Get current page URL."""
        try:
            if self.use_playwright and self.page:
                return self.page.url
            elif self.driver:
                return self.driver.current_url
            return None
        except Exception:
            return None

    def get_page_title(self) -> str | None:
        """Get page title."""
        try:
            if self.use_playwright and self.page:
                return self.page.title()
            elif self.driver:
                return self.driver.title
            return None
        except Exception:
            return None

    def close(self):
        """Close browser."""
        try:
            if self.use_playwright:
                if self.browser:
                    self.browser.close()
                if hasattr(self, "playwright"):
                    self.playwright.stop()
            elif self.driver:
                self.driver.quit()
            print("[ai_browser] ✅ Browser closed", flush=True)
        except Exception as e:
            print(f"[ai_browser] ⚠️ Close error: {e}", flush=True)


def solve_website_problem(
    url: str, problem_description: str, actions: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Use AI browser assistant to solve a website problem.

    Args:
        url: Website URL
        problem_description: What problem needs solving
        actions: List of actions to take

    Example actions:
        [
            {"type": "navigate", "url": "https://example.com"},
            {"type": "click", "selector": "button.login"},
            {"type": "fill", "selector": "input#email", "value": "user@example.com"},
            {"type": "fill", "selector": "input#password", "value": "password"},
            {"type": "click", "selector": "button[type='submit']"},
            {"type": "screenshot", "filename": "result.png"}
        ]
    """
    print("=" * 70, flush=True)
    print("🤖 AI Browser Assistant - Solving Website Problem", flush=True)
    print("=" * 70, flush=True)
    print(f"Problem: {problem_description}", flush=True)
    print(f"URL: {url}", flush=True)
    print()

    assistant = AIBrowserAssistant(headless=False)
    results = {"success": False, "actions_completed": [], "screenshots": [], "errors": []}

    try:
        if not assistant.start():
            results["errors"].append("Failed to start browser")
            return results

        # Execute actions
        for idx, action in enumerate(actions, 1):
            action_type = action.get("type")

            print(f"[{idx}/{len(actions)}] Executing: {action_type}", flush=True)

            try:
                if action_type == "navigate":
                    url_to_go = action.get("url", url)
                    if assistant.navigate(url_to_go):
                        results["actions_completed"].append(f"Navigated to {url_to_go}")

                elif action_type == "click":
                    selector = action.get("selector")
                    timeout = action.get("timeout", 10)
                    if assistant.click(selector, timeout):
                        results["actions_completed"].append(f"Clicked {selector}")
                    time.sleep(1)

                elif action_type == "fill":
                    selector = action.get("selector")
                    value = action.get("value", "")
                    timeout = action.get("timeout", 10)
                    if assistant.fill_input(selector, value, timeout):
                        results["actions_completed"].append(f"Filled {selector}")
                    time.sleep(0.5)

                elif action_type == "wait":
                    seconds = action.get("seconds", 2)
                    time.sleep(seconds)
                    results["actions_completed"].append(f"Waited {seconds}s")

                elif action_type == "wait_for":
                    selector = action.get("selector")
                    timeout = action.get("timeout", 10)
                    if assistant.wait_for_element(selector, timeout):
                        results["actions_completed"].append(f"Waited for {selector}")

                elif action_type == "screenshot":
                    filename = action.get("filename", f"step_{idx}.png")
                    screenshot = assistant.screenshot(filename)
                    if screenshot:
                        results["screenshots"].append(screenshot)

                elif action_type == "get_text":
                    selector = action.get("selector")
                    text = assistant.get_text(selector)
                    if text:
                        results["actions_completed"].append(
                            f"Got text from {selector}: {text[:50]}"
                        )

                else:
                    results["errors"].append(f"Unknown action type: {action_type}")

            except Exception as e:
                error_msg = f"Action {idx} failed: {e}"
                results["errors"].append(error_msg)
                print(f"[ai_browser] ⚠️ {error_msg}", flush=True)

        results["success"] = len(results["errors"]) == 0

        print()
        print("=" * 70, flush=True)
        print("📊 Results:", flush=True)
        print(f"   Success: {results['success']}", flush=True)
        print(f"   Actions completed: {len(results['actions_completed'])}", flush=True)
        print(f"   Screenshots: {len(results['screenshots'])}", flush=True)
        print(f"   Errors: {len(results['errors'])}", flush=True)
        print("=" * 70, flush=True)

    finally:
        if not assistant.headless:
            input("\nPress Enter to close browser...")
        assistant.close()

    return results


def main():
    """Example usage."""
    print("🤖 AI Browser Assistant - Ready to solve problems!", flush=True)
    print()
    print("Usage:", flush=True)
    print("  from agents.ai_browser_assistant import solve_website_problem", flush=True)
    print()
    print("Example:", flush=True)
    print("  solve_website_problem(", flush=True)
    print("      url='https://example.com',", flush=True)
    print("      problem_description='Login to account',", flush=True)
    print("      actions=[", flush=True)
    print("          {'type': 'click', 'selector': 'button.login'},", flush=True)
    print(
        "          {'type': 'fill', 'selector': 'input#email', 'value': 'user@example.com'},",
        flush=True,
    )
    print(
        "          {'type': 'fill', 'selector': 'input#password', 'value': 'password'},", flush=True
    )
    print("          {'type': 'click', 'selector': 'button[type=\"submit\"]'},", flush=True)
    print("          {'type': 'screenshot', 'filename': 'logged_in.png'},", flush=True)
    print("      ]", flush=True)
    print("  )", flush=True)


if __name__ == "__main__":
    main()
