# NeoLight Agent Trading Assessment

**Date:** 2025-11-18  
**Purpose:** Comprehensive assessment of why agents are not executing trades

---

## Executive Summary

SmartTrader is running in PAPER_TRADING_MODE and generating signals, but **no trades are being executed**. The system is collecting price data, generating signals (including SELL signals for BTC-USD, AAVE-USD, ADA-USD), but failing to execute buy or sell orders.

---

## System Architecture Overview

### Core Trading Components

1. **SmartTrader** (`trader/smart_trader.py`)
   - Main trading loop: 2939 lines
   - Mode: PAPER_TRADING_MODE (confirmed in logs)
   - Status: ✅ Running and collecting data
   - Signals: ✅ Generating (SELL signals observed)
   - Trades: ❌ NOT executing

2. **Intelligence Orchestrator** (`agents/intelligence_orchestrator.py`)
   - Purpose: Generates risk_scaler and confidence signals
   - Output: `runtime/atlas_brain.json`
   - Status: ✅ Running
   - Current values:
     - risk_scaler: 0.592
     - confidence: 0.484
     - Updated: 2025-11-18T11:44:13Z

3. **Weights Bridge** (`agents/weights_bridge.py`)
   - Purpose: Converts strategy weights to symbol allocations
   - Input: `runtime/strategy_weights.json` or `runtime/rl_strategy_weights.json`
   - Output: `runtime/allocations_override.json`
   - Status: ⚠️ **ISSUE IDENTIFIED** - Outputting strategy names instead of symbols

4. **Quote Service** (`trader/quote_service.py`)
   - Purpose: Multi-source quote fetching with fallback
   - Status: ✅ Working (fetching quotes successfully)
   - Sources: Alpaca=✅, Yahoo=✅, Finnhub=❌, TwelveData=❌

---

## Critical Issues Identified

### Issue #1: Allocations Configuration Mismatch ⚠️ **HIGH PRIORITY**

**Location:** `runtime/allocations_override.json`

**Problem:**

```json
{
  "allocations": {
    "turtle_trading": 0.714,
    "mean_reversion_rsi": 0.041,
    "momentum_sma_crossover": 0.041,
    ...
  }
}
```

The allocations_override.json contains **STRATEGY names** (turtle_trading, mean_reversion_rsi) instead of **SYMBOL names** (BTC-USD, AAPL, NVDA).

**Impact:**

- `load_allocations()` function filters out strategy names (line 1007-1018 in smart_trader.py)
- Falls back to `allocations_symbols.json` which has proper symbol allocations
- However, this creates confusion and may cause issues if weights_bridge is supposed to provide symbol allocations

**Root Cause:**

- `weights_bridge.py` is designed to normalize strategy weights, not convert them to symbol allocations
- The RL inference system outputs strategy weights, not symbol weights
- There's a missing layer that should convert strategy weights → symbol allocations

**Fix Required:**

- Either fix `weights_bridge.py` to output symbol allocations based on strategy preferences
- Or ensure `allocations_symbols.json` is always used as primary source
- Or create a new bridge that maps strategies to symbols

---

### Issue #2: Signal Generation vs Trade Execution Gap ⚠️ **HIGH PRIORITY**

**Observation:**

- Logs show signals being generated: `"📊 Signal generated for BTC-USD: SELL (RSI=100.0, confidence=0.50)"`
- But no actual trade execution logs: No "✅ PAPER BUY" or "✅ PAPER SELL" messages

**Possible Causes:**

1. **Position Check Failing (SELL signals)**
   - SELL signals require existing positions
   - If no positions exist, SELL signals are ignored
   - Code at line 2375-2377: `if pos["qty"] > 1e-6:` - only executes if position exists

2. **Buy Condition Not Met**
   - Line 2211: `if current_value < target_value * threshold:`
   - If `current_value` (existing position value) >= `target_value * 0.98`, buy is skipped
   - This means if positions already exist at target allocation, no new buys occur

3. **Cooldown Period Active**
   - Line 2086-2096: Cooldown check (5 min for crypto, 15 min for stocks)
   - If last trade was recent, execution is skipped

4. **Circuit Breaker Active**
   - Line 2178-2180: Circuit breaker check
   - If circuit breaker is OPEN, trades are skipped

5. **Confidence Threshold**
   - Line 2145-2147: Crypto RSI < 75 override
   - But if RSI >= 75, no forced buy occurs
   - Standard signal generation may require higher confidence

6. **Allocation Too Small**
   - Line 2205-2209: If allocation < 1%, uses minimum trade size
   - But if portfolio value is low or allocation is 0, may still skip

**Investigation Needed:**

- Check current positions in broker state
- Check last_trade timestamps
- Check circuit breaker state
- Check if signals are being generated but execution conditions fail

---

### Issue #3: Enhanced Signal Override Logic ⚠️ **MEDIUM PRIORITY**

**Location:** Lines 2142-2153 in `smart_trader.py`

**Problem:**

```python
# CRYPTO: Force BUY if RSI < 75 and no position (FINAL - override everything)
is_crypto = "-USD" in sym
if is_crypto and rsi_val is not None and rsi_val < 75 and not has_position:
    signal = "buy"  # Force BUY for crypto when RSI < 75 - FINAL OVERRIDE
```

**Issue:**

- Logs show RSI=100.0 for BTC-USD (overbought)
- RSI 100.0 means all recent price changes were up (unrealistic, likely data issue)
- Enhanced signal generator is outputting SELL (correct for RSI=100)
- But the crypto RSI < 75 override never triggers because RSI is too high

**Impact:**

- Crypto symbols with RSI >= 75 won't get forced buys
- Only standard signal generation applies
- If standard signals require multiple strategy votes, may not generate buy signals

---

### Issue #4: Strategy Vote Requirements ⚠️ **MEDIUM PRIORITY**

**Location:** Lines 882-886 in `smart_trader.py`

**Problem:**

```python
if strategy_votes["buy"] > strategy_votes["sell"] and strategy_votes["buy"] > 0:
    tech_signal = "buy"
elif strategy_votes["sell"] > strategy_votes["buy"] and strategy_votes["sell"] > 0:
    tech_signal = "sell"
```

**Issue:**

- Requires at least 1 strategy vote for buy/sell
- If no strategies vote, no signal is generated
- Strategies may not be voting due to:

  - Insufficient price history (need 20+ points)
  - Indicator calculations failing
  - Strategy conditions not met

**Investigation Needed:**

- Check which strategies are active
- Check if strategies are generating votes
- Check if vote threshold is too high

---

### Issue #5: Data Quality Issues ⚠️ **LOW PRIORITY**

**Observation:**

- Some symbols failing quote fetch: ADA-USD, DOGE-USD
- RSI values showing 100.0 (unrealistic - indicates all price changes were up)
- Historical data may be stale or incorrect

**Impact:**

- Symbols with bad data can't trade
- Unrealistic RSI values may cause incorrect signals
- But this doesn't explain why symbols with good data (BTC-USD, ETH-USD) aren't trading

---

## Current System State

### Running Processes

- ✅ SmartTrader: Running (PAPER_TRADING_MODE)
- ✅ Intelligence Orchestrator: Running
- ✅ Quote Service: Working
- ✅ Weights Bridge: Running (but outputting wrong format)

### Configuration Files

**Trading Mode:**

```json
{
  "mode": "PAPER_TRADING_MODE",
  "timestamp": "2025-11-05T05:42:11Z"
}
```

**Brain State:**

```json
{
  "risk_scaler": 0.592,
  "confidence": 0.484,
  "updated": "2025-11-18T11:44:13.437020Z"
}
```

**Symbol Allocations (from allocations_symbols.json):**

- Crypto: BTC-USD (3.5%), ETH-USD (2.8%), SOL-USD (1.6%), etc.
- Stocks: NVDA (3.5%), MSFT (3.1%), GOOGL (3.1%), etc.
- Total: 59 symbols with allocations

**Strategy Allocations (from allocations_override.json):**

- turtle_trading: 71.4%
- Other strategies: ~4% each
- ⚠️ **This is the problem** - should be symbol allocations, not strategy allocations

---

## Trade Execution Flow Analysis

### Buy Order Execution Path

1. **Signal Generation** ✅ Working
   - `generate_signal()` called
   - Returns signal="buy" or signal="sell"

2. **Signal Validation** ⚠️ Unknown
   - Line 2174: `if not signal: continue`
   - Signals are being generated, so this passes

3. **Circuit Breaker Check** ⚠️ Unknown
   - Line 2178: `if not trade_breaker.can_proceed(): continue`
   - Need to check circuit breaker state

4. **Position Size Calculation** ⚠️ Potential Issue
   - Line 2191: `target_allocation = allocations.get(sym, 0.0) * risk_scaler`
   - If allocation is 0 or very small, uses minimum (1% crypto, 0.5% stocks)
   - Line 2211: `if current_value < target_value * threshold:`
   - **This is likely the blocker** - if positions already exist at target, no new buys

5. **Order Submission** ❌ Not Reached
   - Line 2316: `result = broker.submit_order(sym, "buy", qty, price)`
   - No logs showing this being called

### Sell Order Execution Path

1. **Signal Generation** ✅ Working
   - SELL signals observed in logs

2. **Position Check** ⚠️ Likely Issue
   - Line 2377: `if pos["qty"] > 1e-6:`
   - **If no positions exist, SELL signals are ignored**
   - This is likely why SELL signals aren't executing

---

## Root Cause Hypothesis

### Primary Hypothesis: No Initial Positions

**Theory:**

1. System starts with no positions (fresh paper trading account)
2. SELL signals are generated but ignored (no positions to sell)
3. BUY signals are generated but execution conditions fail:
   - `current_value < target_value * threshold` check fails
   - If `current_value = 0` (no position) and `target_value > 0`, this should pass
   - But there may be other conditions blocking

**Evidence:**

- No trade execution logs in recent history
- SELL signals being generated but not executed
- System appears to be in initial state

### Secondary Hypothesis: Allocation Calculation Issue

**Theory:**

1. `allocations_override.json` has strategy names, not symbols
2. `load_allocations()` filters these out
3. Falls back to `allocations_symbols.json` which has proper allocations
4. But risk_scaler (0.592) may be reducing allocations too much
5. Combined with confidence (0.484), may be blocking trades

**Evidence:**

- allocations_override.json has wrong format
- risk_scaler is 0.592 (reducing position sizes by ~40%)
- confidence is 0.484 (below 0.5 threshold in some checks)

---

## Recommended Actions

### Immediate (High Priority)

1. **Check Current Positions**
   - Inspect broker state file or add logging to show current positions
   - Determine if system has any open positions

2. **Fix Allocations Override**
   - Either fix `weights_bridge.py` to output symbol allocations
   - Or ensure `allocations_symbols.json` is always used
   - Or disable `allocations_override.json` if it's causing issues

3. **Add Detailed Execution Logging**
   - Log when buy/sell conditions are checked
   - Log why trades are skipped (cooldown, circuit breaker, position check, etc.)
   - Log current_value vs target_value calculations

4. **Check Circuit Breaker State**
   - Verify circuit breaker is not blocking trades
   - Check if quote failures are causing circuit breaker to open

### Short-term (Medium Priority)

1. **Fix RSI Calculation**
   - Investigate why RSI=100.0 (unrealistic values)
   - Ensure price history is correct before calculating indicators

2. **Review Signal Generation Logic**
   - Ensure strategies are voting correctly
   - Verify vote thresholds are appropriate
   - Check if enhanced signals are overriding standard signals incorrectly

3. **Improve Initial Position Entry**
   - Add logic to force initial buys when no positions exist
   - Or lower thresholds for first trades

### Long-term (Low Priority)

1. **Refactor Allocations System**
   - Create clear separation between strategy weights and symbol allocations
   - Ensure weights_bridge outputs correct format
   - Add validation to prevent strategy names in symbol allocations

2. **Improve Error Handling**
   - Better logging when trades are skipped
   - Clearer error messages
   - Health checks for trading conditions

---

## Code References

### Key Functions

**Signal Generation:**

```763:971:trader/smart_trader.py
def generate_signal(broker: PaperBroker, sym: str, prices: deque, risk_scaler: float, confidence: float) -> Tuple[Optional[str], Dict[str, Any]]:
```

**Allocation Loading:**

```997:1072:trader/smart_trader.py
def load_allocations() -> Dict[str, float]:
```

**Buy Execution:**

```2196:2374:trader/smart_trader.py
if signal == "buy":
    # Check if we need to buy more
    # ... position size calculation ...
    # ... order submission ...
```

**Sell Execution:**

```2375:2430:trader/smart_trader.py
elif signal == "sell":
    pos = broker.get_position(sym)
    if pos["qty"] > 1e-6:
        # ... sell logic ...
```

**Main Loop:**

```1326:2939:trader/smart_trader.py
def main():
    # ... initialization ...
    while not stop_flag["stop"]:
        # ... main trading loop ...
```

---

## Diagnostic Commands

### Check Current State

```bash
# Check if SmartTrader is running
ps aux | grep smart_trader

# Check recent logs
tail -100 logs/smart_trader.log | grep -E "(BUY|SELL|signal|position|allocation)"

# Check brain state
cat runtime/atlas_brain.json

# Check allocations
cat runtime/allocations_symbols.json | jq '.allocations | keys | length'
cat runtime/allocations_override.json | jq '.allocations | keys'

# Check trading mode
cat state/trading_mode.json
```

### Check Circuit Breaker

```bash
# Look for circuit breaker messages in logs
grep -i "circuit breaker" logs/smart_trader.log | tail -20
```

### Check Positions

```bash
# Check if state file has position data
cat state/smart_trader_state.json | jq '.positions // {}'
```

---

## Next Steps for Claude Sonnet 4.5

1. **Review this assessment** to understand the full picture
2. **Focus on Issue #2** (Signal Generation vs Trade Execution Gap) - most likely root cause
3. **Add diagnostic logging** to identify exactly where execution is failing
4. **Check broker state** to see if positions exist
5. **Fix allocations_override.json** format issue
6. **Test with forced initial buy** to verify execution path works

---

## Files to Review

- `trader/smart_trader.py` - Main trading logic (2939 lines)
- `agents/weights_bridge.py` - Allocations bridge (92 lines)
- `agents/intelligence_orchestrator.py` - Brain state generator (48 lines)
- `trader/quote_service.py` - Quote fetching
- `runtime/allocations_override.json` - ⚠️ Wrong format
- `runtime/allocations_symbols.json` - ✅ Correct format
- `runtime/atlas_brain.json` - Brain state
- `state/trading_mode.json` - Trading mode
- `logs/smart_trader.log` - Trading logs

---

## End of Assessment
