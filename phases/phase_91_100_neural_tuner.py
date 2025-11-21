#!/usr/bin/env python3
import datetime as dt
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
RUNTIME = ROOT / "runtime"
STATE = RUNTIME / "atlas_learning.json"
TRADER_CFG = RUNTIME / "smart_params.json"  # live parameters for SmartTrader
TUNER_LOG = LOGS / "neural_tuner.log"

LOGS.mkdir(parents=True, exist_ok=True)
RUNTIME.mkdir(parents=True, exist_ok=True)


def log(msg):
    line = f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}\n"
    with open(TUNER_LOG, "a") as f:
        f.write(line)
    print(line, end="", flush=True)


def jload(p, default=None):
    try:
        return json.loads(pathlib.Path(p).read_text())
    except:
        return default


def jdump(p, obj):
    pathlib.Path(p).write_text(json.dumps(obj, indent=2))


# Safe default seed
if not STATE.exists():
    jdump(
        STATE,
        {
            "win_rate": 0.50,
            "avg_profit": 0.0,
            "avg_loss": 0.0,
            "risk_factor": 1.0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "last_update": "",
            "version": "91-100.v1",
        },
    )

# bootstrap trading params if missing
if not TRADER_CFG.exists():
    jdump(
        TRADER_CFG,
        dict(
            SMA_FAST=20,
            SMA_SLOW=50,
            RSI_LEN=14,
            RSI_BUY=35,
            RSI_SELL=65,
            MIN_SPREAD_BPS=1.5,
            MAX_SLIPPAGE_BPS=2.0,
            TRAIL_BPS=30,
            HARD_STOP_BPS=60,
            TAKE_PROFIT_BPS=80,
            MAX_PCT_RISK=0.01,
            MAX_CONCURRENT=2,
        ),
    )


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def tune_once():
    st = jload(STATE, {})
    cfg = jload(TRADER_CFG, {})

    wr = float(st.get("win_rate", 0.5))
    avgp = float(st.get("avg_profit", 0.0))
    avgl = float(st.get("avg_loss", 0.0))
    risk = float(st.get("risk_factor", 1.0))
    trades = int(st.get("total_trades", 0))

    # Risk nudges based on WR, bounded
    if wr > 0.58:
        risk = clamp(risk * 1.03, 0.5, 2.0)
    elif wr < 0.42:
        risk = clamp(risk * 0.95, 0.5, 2.0)

    # RSI & SMA dynamic tuning (weekly bias, but we apply gently)
    # If avg profit > |avg loss| and WR decent, slightly increase aggressiveness (lower RSI buy, tighten fast SMA)
    if trades >= 20:
        edge = avgp - abs(avgl) * 0.6
        if wr >= 0.53 and edge > 0:
            cfg["RSI_BUY"] = clamp(cfg["RSI_BUY"] - 1, 25, 45)  # more willing to buy dips
            cfg["SMA_FAST"] = clamp(cfg["SMA_FAST"] - 1, 10, 40)
            cfg["TAKE_PROFIT_BPS"] = clamp(cfg["TAKE_PROFIT_BPS"] + 2, 50, 120)
        elif wr <= 0.47 or edge < 0:
            cfg["RSI_BUY"] = clamp(cfg["RSI_BUY"] + 1, 25, 45)  # more selective
            cfg["SMA_FAST"] = clamp(cfg["SMA_FAST"] + 1, 10, 40)
            cfg["HARD_STOP_BPS"] = clamp(cfg["HARD_STOP_BPS"] + 2, 40, 100)
            cfg["TRAIL_BPS"] = clamp(cfg["TRAIL_BPS"] + 2, 20, 80)

    # tie MAX_PCT_RISK to risk factor (nonlinear, cautious)
    cfg["MAX_PCT_RISK"] = round(
        0.008 * risk, 5
    )  # 0.8% @ rf=1.0, bounded by drawdown guard separately

    # Write back runtime parameters and patched risk factor in state
    st["risk_factor"] = round(risk, 4)
    st["last_update"] = dt.datetime.now().strftime("%F_%T")
    jdump(STATE, st)
    jdump(TRADER_CFG, cfg)
    log(
        f"🧪 Tuner set: WR={wr:.2f} RF={risk:.2f} | SMA_FAST={cfg['SMA_FAST']} SMA_SLOW={cfg['SMA_SLOW']} RSI_BUY={cfg['RSI_BUY']} MAX_PCT_RISK={cfg['MAX_PCT_RISK']}"
    )
    return True


def main():
    log("🚀 Neural Tuner online")
    while True:
        try:
            ok = tune_once()
            time.sleep(
                60
            )  # run every minute (lightweight). A weekly bias emerges via small nudges.
        except KeyboardInterrupt:
            log("👋 Exiting on user request")
            break
        except Exception as e:
            log(f"💥 Tuner error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
