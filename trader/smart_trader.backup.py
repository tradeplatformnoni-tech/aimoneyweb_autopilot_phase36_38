#!/usr/bin/env python3
import datetime as dt
import json
import random
import time
from pathlib import Path

# ==== Config (tune here) ====
SYMBOLS = ["BTC/USD", "ETH/USD", "USDT/USD"]
BASE_CCY = "USD"
MAX_PCT_RISK = 0.01  # 1% of portfolio value per trade
MAX_CONCURRENT = 2
MIN_SPREAD_BPS = 1.5  # skip if spread > 1.5 bps
MAX_SLIPPAGE_BPS = 2.0
ATR_LOOKBACK = 14
SMA_FAST = 20
SMA_SLOW = 50
RSI_LEN = 14
RSI_BUY = 35
RSI_SELL = 65
TRAIL_BPS = 30  # trailing stop 0.30%
HARD_STOP_BPS = 60  # hard stop 0.60%
TAKE_PROFIT_BPS = 80  # TP 0.80%
DAILY_LOSS_LIMIT_PCT = 2.0  # halt for day at -2%
MAX_LOSS_STREAK = 4
COOLDOWN_SEC = 120
TRADE_WINDOW = (6, 20)  # 06:00-20:00 local
STATE_FILE = Path("trader/state.json")
LOG_FILE = Path("logs/trader.log")
PAPER = True


# ==== Mock / Broker bindings (replace with Alpaca/CCXT/etc) ====
class Broker:
    def __init__(self):
        self.cash = 90000.0
        self.equity = 90000.0
        self.positions = {}  # symbol -> {"qty":float,"avg":float}

    def fetch_quote(self, sym):
        # replace with real quote (bid, ask). Here: simulate tight spread
        mid = 1000.0 + random.random() * 10.0
        return {"bid": mid * 0.9995, "ask": mid * 1.0005}

    def fetch_portfolio_value(self):
        return self.equity

    def submit_order(self, sym, side, qty, price):
        notional = qty * price
        fee = max(0.0, 0.0002 * notional)
        if side == "buy":
            if notional + fee > self.cash:
                raise RuntimeError("insufficient balance")
            self.cash -= notional + fee
            pos = self.positions.get(sym, {"qty": 0.0, "avg": 0.0})
            new_qty = pos["qty"] + qty
            pos["avg"] = (pos["avg"] * pos["qty"] + price * qty) / max(1e-9, new_qty)
            pos["qty"] = new_qty
            self.positions[sym] = pos
        else:
            pos = self.positions.get(sym, {"qty": 0.0, "avg": 0.0})
            if qty > pos["qty"] + 1e-12:
                raise RuntimeError("sell qty>pos qty")
            pos["qty"] -= qty
            if pos["qty"] <= 1e-12:
                pnl = (price - pos["avg"]) * qty
                self.cash += qty * price - fee
                self.equity += pnl
                del self.positions[sym]
            else:
                self.cash += qty * price - fee
                self.positions[sym] = pos
        return {"filled_qty": qty, "filled_price": price}


# ==== TA helpers (simple rolling placeholders; swap for pandas/numba later) ====
class Ring:
    def __init__(self, n):
        self.n = n
        self.a = []

    def add(self, x):
        self.a.append(x)

    def arr(self):
        return self.a[-self.n :] if len(self.a) > self.n else self.a


def sma(x, n):
    a = x[-n:]
    return sum(a) / len(a) if a else None


def rsi(prices, n=14):
    if len(prices) < n + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-n, 0):
        d = prices[i] - prices[i - 1]
        if d > 0:
            gains += d
        else:
            losses -= d
    if losses == 0:
        return 100.0
    rs = gains / max(1e-9, losses)
    return 100.0 - (100.0 / (1.0 + rs))


# ==== Guardrails & utils ====
def now_hour():
    return dt.datetime.now().hour


def within_window():
    s, e = TRADE_WINDOW
    return s <= now_hour() < e


def spread_bps(q):
    mid = (q["bid"] + q["ask"]) / 2.0
    return (q["ask"] - q["bid"]) / mid * 10000


def size_for_risk(pv, price):
    notional = pv * MAX_PCT_RISK
    return max(0.0, notional / price)


def write_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def log(msg):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(f"[{dt.datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    print(msg, flush=True)


def circuit_breaker(state):
    if state["daily"]["pnl_pct"] <= -DAILY_LOSS_LIMIT_PCT:
        return "DAILY_PNL"
    if state["streak"]["losses"] >= MAX_LOSS_STREAK:
        return "LOSS_STREAK"
    return None


def trailing_levels(entry, side, best):
    # returns (hard_stop, trail_stop, take_profit)
    if side == "long":
        hs = entry * (1 - HARD_STOP_BPS / 10000)
        tp = entry * (1 + TAKE_PROFIT_BPS / 10000)
        # trail follows best price
        ts = best * (1 - TRAIL_BPS / 10000)
        return hs, ts, tp
    else:
        # for shorts (future-support); not used in this long-only example
        hs = entry * (1 + HARD_STOP_BPS / 10000)
        tp = entry * (1 - TAKE_PROFIT_BPS / 10000)
        ts = best * (1 + TRAIL_BPS / 10000)
        return hs, ts, tp


# ==== Main trader ====
def main():
    broker = Broker()
    prices = {s: Ring(200) for s in SYMBOLS}
    state = {
        "balances": {BASE_CCY: broker.cash},
        "positions": {},
        "pending": {},
        "daily": {"start_equity": broker.equity, "pnl_pct": 0.0},
        "streak": {"wins": 0, "losses": 0, "last_result": None},
        "cooldown_until": 0,
    }

    log("🟣 SmartTrader starting (paper=%s)" % PAPER)

    while True:
        try:
            # time window
            if not within_window():
                time.sleep(5)
                continue

            # cooldown
            if time.time() < state["cooldown_until"]:
                time.sleep(3)
                continue

            pv = broker.fetch_portfolio_value()
            state["balances"][BASE_CCY] = broker.cash

            # update pnl
            day_pnl_pct = (
                (pv - state["daily"]["start_equity"])
                / max(1e-9, state["daily"]["start_equity"])
                * 100.0
            )
            state["daily"]["pnl_pct"] = round(day_pnl_pct, 3)

            # circuit breaker
            halt = circuit_breaker(state)
            if halt:
                log(f"⛔ Circuit breaker: {halt}. Sleeping 30 min.")
                state["cooldown_until"] = time.time() + 1800
                write_state(state)
                time.sleep(5)
                continue

            # count concurrent
            open_syms = [s for s in broker.positions.keys()]
            if len(open_syms) >= MAX_CONCURRENT:
                time.sleep(2)
                continue

            for sym in SYMBOLS:
                q = broker.fetch_quote(sym)
                s_bps = spread_bps(q)
                if s_bps > MIN_SPREAD_BPS:
                    log(f"🔕 {sym} spread {s_bps:.2f}bps too wide")
                    continue

                mid = (q["bid"] + q["ask"]) / 2.0
                # record price
                prices[sym].add(mid)
                p = prices[sym].arr()
                if len(p) < max(SMA_SLOW, RSI_LEN) + 1:
                    continue

                sma_fast = sma(p, SMA_FAST)
                sma_slow = sma(p, SMA_SLOW)
                r = rsi(p, RSI_LEN)

                # volatility proxy using simple std dev on last ATR_LOOKBACK diffs
                diffs = [abs(p[i] - p[i - 1]) for i in range(-ATR_LOOKBACK + 1, 0)]
                vol = sum(diffs) / max(1, len(diffs)) / mid
                if vol > 0.01:  # >1% bar-to-bar avg move → too volatile
                    log(f"🌪️  {sym} vol too high ({vol:.3%})")
                    continue

                trend_ok = sma_fast and sma_slow and (sma_fast > sma_slow)
                rsi_ok_buy = r is not None and r < RSI_BUY

                # Entry rule: Uptrend + RSI pullback + acceptable spread/vol
                if trend_ok and rsi_ok_buy and sym not in broker.positions:
                    qty = size_for_risk(pv, q["ask"])
                    # buffer for fees & slippage
                    qty = qty * 0.98
                    if qty <= 0:
                        continue
                    try:
                        res = broker.submit_order(sym, "buy", qty, q["ask"])
                        log(f"🟩 BUY {sym} qty={qty:.6f} @ {res['filled_price']:.2f}")
                        state["positions"][sym] = {
                            "entry": res["filled_price"],
                            "side": "long",
                            "best": res["filled_price"],
                        }
                    except Exception as e:
                        log(f"⚠️ BUY error {sym}: {e}")
                        # insufficient balance → throttle for 5 minutes
                        if "insufficient" in str(e).lower():
                            state["cooldown_until"] = time.time() + 300

                # Manage open positions → trailing stop / TP / break-even
                if sym in broker.positions:
                    info = state["positions"][sym]
                    # track best in favor
                    if info["side"] == "long":
                        info["best"] = max(info["best"], q["bid"])
                        hs, ts, tp = trailing_levels(info["entry"], "long", info["best"])
                        # move to break-even if > 0.35% in favor
                        if q["bid"] >= info["entry"] * 1.0035:
                            hs = max(hs, info["entry"])
                        # decide exit
                        exit_price = None
                        reason = None
                        if q["bid"] <= hs:
                            exit_price = q["bid"]
                            reason = "HARD_STOP/BE"
                        elif q["bid"] <= ts:
                            exit_price = q["bid"]
                            reason = "TRAIL"
                        elif q["bid"] >= tp:
                            exit_price = q["bid"]
                            reason = "TAKE_PROFIT"
                        if exit_price:
                            qty = broker.positions[sym]["qty"]
                            try:
                                res = broker.submit_order(sym, "sell", qty, exit_price)
                                pnl = (res["filled_price"] - info["entry"]) * qty
                                log(
                                    f"🟥 SELL {sym} qty={qty:.6f} @ {res['filled_price']:.2f} | {reason} | pnl={pnl:.2f}"
                                )
                                # update streaks
                                if pnl >= 0:
                                    state["streak"]["wins"] += 1
                                    state["streak"]["losses"] = 0
                                    state["streak"]["last_result"] = "win"
                                else:
                                    state["streak"]["losses"] += 1
                                    state["streak"]["wins"] = 0
                                    state["streak"]["last_result"] = "loss"
                                state["cooldown_until"] = time.time() + (
                                    COOLDOWN_SEC if pnl < 0 else 5
                                )
                                del state["positions"][sym]
                            except Exception as e:
                                log(f"⚠️ SELL error {sym}: {e}")

            write_state(state)
            time.sleep(1.0)
        except KeyboardInterrupt:
            log("👋 Exiting on user request")
            break
        except Exception as e:
            log(f"💥 Loop error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
