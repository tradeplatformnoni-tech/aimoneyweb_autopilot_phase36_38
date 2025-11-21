#!/usr/bin/env python3
"""
NeoLight TEST_MODE Diagnostic Script
Identifies why TEST_MODE quote fetching fails while PAPER_TRADING_MODE works
"""

import os
import sys
import inspect
import logging
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load environment variables from .env if exists
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

logger = logging.getLogger(__name__)

def print_section(title):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def check_environment():
    """Check environment variables"""
    print_section("1. ENVIRONMENT VARIABLES")
    
    env_vars = {
        'TRADING_MODE': os.getenv('TRADING_MODE', 'NOT SET'),
        'ALPACA_API_KEY': '***' if os.getenv('ALPACA_API_KEY') else 'NOT SET',
        'ALPACA_SECRET_KEY': '***' if os.getenv('ALPACA_SECRET_KEY') else 'NOT SET',
        'NEOLIGHT_USE_ALPACA_QUOTES': os.getenv('NEOLIGHT_USE_ALPACA_QUOTES', 'NOT SET'),
        'FINNHUB_API_KEY': '***' if os.getenv('FINNHUB_API_KEY') else 'NOT SET',
        'TWELVEDATA_API_KEY': '***' if os.getenv('TWELVEDATA_API_KEY') else 'NOT SET',
        'ALPHAVANTAGE_API_KEY': '***' if os.getenv('ALPHAVANTAGE_API_KEY') else 'NOT SET'
    }
    
    for key, value in env_vars.items():
        status = "✅" if value != 'NOT SET' else "❌"
        print(f"{status} {key}: {value}")

def check_imports():
    """Check if required modules can be imported"""
    print_section("2. MODULE IMPORTS")
    
    modules = [
        ('trader.smart_trader', 'SmartTrader'),
        ('trader.quote_service', 'QuoteService or UnifiedQuoteService'),
        ('alpaca.trading.client', 'TradingClient'),
        ('yfinance', 'yfinance'),
    ]
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✅ {description}: Can import")
        except ImportError as e:
            print(f"❌ {description}: Import failed - {e}")

def analyze_smart_trader():
    """Analyze SmartTrader class structure"""
    print_section("3. SMARTTRADER CLASS ANALYSIS")
    
    try:
        from trader.smart_trader import SmartTrader
        
        # Check __init__ signature
        init_signature = inspect.signature(SmartTrader.__init__)
        print(f"📋 __init__ signature: {init_signature}")
        
        # Check methods
        methods = [m for m in dir(SmartTrader) if not m.startswith('_')]
        print(f"\n📋 Public methods ({len(methods)}):")
        for method in methods[:20]:  # First 20
            print(f"   - {method}")
        
        # Check for quote-related methods
        quote_methods = [m for m in methods if 'quote' in m.lower()]
        print(f"\n📋 Quote-related methods:")
        for method in quote_methods:
            print(f"   - {method}")
        
        # Check for trade methods
        trade_methods = [m for m in methods if 'trade' in m.lower()]
        print(f"\n📋 Trade-related methods:")
        for method in trade_methods:
            print(f"   - {method}")
        
        return SmartTrader
        
    except Exception as e:
        print(f"❌ Failed to analyze SmartTrader: {e}")
        return None

def test_initialization():
    """Test SmartTrader initialization in both modes"""
    print_section("4. INITIALIZATION TEST")
    
    try:
        from trader.smart_trader import SmartTrader
        
        # Test TEST_MODE
        print("\n🧪 Testing TEST_MODE initialization...")
        os.environ['TRADING_MODE'] = 'TEST_MODE'
        
        try:
            trader_test = SmartTrader()
            print(f"✅ TEST_MODE initialized")
            print(f"   Mode: {trader_test.mode}")
            print(f"   Broker: {trader_test.broker.__class__.__name__ if hasattr(trader_test, 'broker') else 'NOT FOUND'}")
            print(f"   Quote Service: {trader_test.quote_service.__class__.__name__ if hasattr(trader_test, 'quote_service') else 'NOT FOUND'}")
            
            # Check if broker has quote_service
            if hasattr(trader_test, 'broker') and hasattr(trader_test.broker, 'quote_service'):
                print(f"   Broker Quote Service: {trader_test.broker.quote_service.__class__.__name__}")
            else:
                print(f"   ❌ Broker does NOT have quote_service attribute")
        except Exception as e:
            print(f"❌ TEST_MODE initialization failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test PAPER_TRADING_MODE
        print("\n📄 Testing PAPER_TRADING_MODE initialization...")
        os.environ['TRADING_MODE'] = 'PAPER_TRADING_MODE'
        
        try:
            trader_paper = SmartTrader()
            print(f"✅ PAPER_TRADING_MODE initialized")
            print(f"   Mode: {trader_paper.mode}")
            print(f"   Broker: {trader_paper.broker.__class__.__name__ if hasattr(trader_paper, 'broker') else 'NOT FOUND'}")
            print(f"   Quote Service: {trader_paper.quote_service.__class__.__name__ if hasattr(trader_paper, 'quote_service') else 'NOT FOUND'}")
            
            # Check if broker has quote_service
            if hasattr(trader_paper, 'broker') and hasattr(trader_paper.broker, 'quote_service'):
                print(f"   Broker Quote Service: {trader_paper.broker.quote_service.__class__.__name__}")
            else:
                print(f"   ❌ Broker does NOT have quote_service attribute")
        except Exception as e:
            print(f"❌ PAPER_TRADING_MODE initialization failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Failed to test initialization: {e}")

def test_quote_fetching():
    """Test actual quote fetching in both modes"""
    print_section("5. QUOTE FETCHING TEST")
    
    test_symbol = "BTC-USD"
    
    try:
        from trader.smart_trader import SmartTrader
        
        # Test in TEST_MODE
        print(f"\n🧪 Testing quote fetch in TEST_MODE for {test_symbol}...")
        os.environ['TRADING_MODE'] = 'TEST_MODE'
        
        try:
            trader_test = SmartTrader()
            
            # Try different methods of getting a quote
            print(f"\n   Attempting quote fetch...")
            
            # Method 1: Direct quote_service (if exists)
            if hasattr(trader_test, 'quote_service'):
                try:
                    quote1 = trader_test.quote_service.fetch_quote(test_symbol)
                    if quote1:
                        print(f"   ✅ quote_service.fetch_quote() worked: ${quote1.get('price', 0):.2f}")
                    else:
                        print(f"   ❌ quote_service.fetch_quote() returned None")
                except Exception as e:
                    print(f"   ❌ quote_service.fetch_quote() failed: {e}")
            else:
                print(f"   ❌ trader_test has no 'quote_service' attribute")
            
            # Method 2: test_trade method
            if hasattr(trader_test, 'test_trade'):
                try:
                    result = trader_test.test_trade(test_symbol, 'buy')
                    if result.get('success'):
                        print(f"   ✅ test_trade() worked: {result}")
                    else:
                        print(f"   ❌ test_trade() failed: {result.get('error')}")
                except Exception as e:
                    print(f"   ❌ test_trade() raised exception: {e}")
            else:
                print(f"   ❌ trader_test has no 'test_trade' method")
                
        except Exception as e:
            print(f"❌ TEST_MODE quote test failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test in PAPER_TRADING_MODE
        print(f"\n📄 Testing quote fetch in PAPER_TRADING_MODE for {test_symbol}...")
        os.environ['TRADING_MODE'] = 'PAPER_TRADING_MODE'
        
        try:
            trader_paper = SmartTrader()
            
            # Try different methods of getting a quote
            print(f"\n   Attempting quote fetch...")
            
            # Method 1: Direct quote_service (if exists)
            if hasattr(trader_paper, 'quote_service'):
                try:
                    quote1 = trader_paper.quote_service.fetch_quote(test_symbol)
                    if quote1:
                        print(f"   ✅ quote_service.fetch_quote() worked: ${quote1.get('price', 0):.2f}")
                    else:
                        print(f"   ❌ quote_service.fetch_quote() returned None")
                except Exception as e:
                    print(f"   ❌ quote_service.fetch_quote() failed: {e}")
            else:
                print(f"   ❌ trader_paper has no 'quote_service' attribute")
            
            # Method 2: paper_trade method
            if hasattr(trader_paper, 'paper_trade'):
                try:
                    result = trader_paper.paper_trade(test_symbol, 'buy')
                    if result.get('success'):
                        print(f"   ✅ paper_trade() worked: {result}")
                    else:
                        print(f"   ❌ paper_trade() failed: {result.get('error')}")
                except Exception as e:
                    print(f"   ❌ paper_trade() raised exception: {e}")
            else:
                print(f"   ❌ trader_paper has no 'paper_trade' method")
                
        except Exception as e:
            print(f"❌ PAPER_TRADING_MODE quote test failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Failed to test quote fetching: {e}")

def analyze_broker_classes():
    """Analyze broker class implementations"""
    print_section("6. BROKER CLASS ANALYSIS")
    
    try:
        from trader.smart_trader import SmartTrader
        
        # Get broker classes from SmartTrader module
        import trader.smart_trader as st_module
        
        # Find TestBroker
        if hasattr(st_module, 'TestBroker'):
            TestBroker = st_module.TestBroker
            print("\n🧪 TestBroker found:")
            print(f"   __init__ signature: {inspect.signature(TestBroker.__init__)}")
            
            # Check if it accepts quote_service
            init_params = inspect.signature(TestBroker.__init__).parameters
            if 'quote_service' in init_params:
                print(f"   ✅ Accepts 'quote_service' parameter")
            else:
                print(f"   ❌ Does NOT accept 'quote_service' parameter")
                print(f"   Parameters: {list(init_params.keys())}")
        else:
            print("❌ TestBroker not found in smart_trader module")
        
        # Find PaperBroker
        if hasattr(st_module, 'PaperBroker'):
            PaperBroker = st_module.PaperBroker
            print("\n📄 PaperBroker found:")
            print(f"   __init__ signature: {inspect.signature(PaperBroker.__init__)}")
            
            # Check if it accepts quote_service
            init_params = inspect.signature(PaperBroker.__init__).parameters
            if 'quote_service' in init_params:
                print(f"   ✅ Accepts 'quote_service' parameter")
            else:
                print(f"   ❌ Does NOT accept 'quote_service' parameter")
                print(f"   Parameters: {list(init_params.keys())}")
        else:
            print("❌ PaperBroker not found in smart_trader module")
            
    except Exception as e:
        print(f"❌ Failed to analyze broker classes: {e}")
        import traceback
        traceback.print_exc()

def print_diagnosis():
    """Print diagnosis and recommendations"""
    print_section("7. DIAGNOSIS & RECOMMENDATIONS")
    
    print("""
Based on the analysis above, here are the likely issues:

🔍 COMMON ISSUES:

1. TestBroker doesn't accept quote_service parameter
   → TestBroker.__init__ should accept quote_service
   → Fix: Add quote_service parameter to TestBroker.__init__

2. test_trade() uses different quote fetching method
   → Check if test_trade() calls self.quote_service.fetch_quote()
   → Fix: Make test_trade() use same method as paper_trade()

3. TEST_MODE initializes broker without quote_service
   → Check SmartTrader.__init__ for mode-specific initialization
   → Fix: Pass quote_service to TestBroker like PaperBroker

4. Environment variables not accessible in TEST_MODE
   → Check if ALPACA_API_KEY is set
   → Fix: Ensure env vars are loaded before SmartTrader init

📋 ACTION ITEMS:

1. Review Section 3 - Check if quote-related methods exist
2. Review Section 4 - Compare TEST_MODE vs PAPER_TRADING_MODE init
3. Review Section 5 - See which quote fetch method fails
4. Review Section 6 - Check if TestBroker accepts quote_service

🎯 RECOMMENDED FIX:

Apply the fix from the artifacts provided:
- Unified quote fetching for all modes
- TestBroker updated to accept quote_service
- Single UnifiedQuoteService instance shared by all modes
See INTEGRATION_GUIDE.md for step-by-step implementation.
""")

def main():
    """Run all diagnostics"""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║          NeoLight TEST_MODE Diagnostic Script                             ║
║          Identifies why TEST_MODE fails while PAPER_TRADING_MODE works    ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
""")
    
    try:
        # Run diagnostics
        check_environment()
        check_imports()
        analyze_smart_trader()
        test_initialization()
        test_quote_fetching()
        analyze_broker_classes()
        print_diagnosis()
        
        print_section("DIAGNOSTIC COMPLETE")
        print("\n✅ Diagnostic completed successfully")
        print("\nNext steps:")
        print("1. Review the output above")
        print("2. Identify which checks failed (marked with ❌)")
        print("3. Apply the fix from the Integration Guide")
        print("4. Run this diagnostic again to verify the fix\n")
        
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

