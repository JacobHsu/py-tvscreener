"""
Collect XAU/XAG (Gold/Silver) daily technical indicators from TradingView
and store in SQLite (same history.db as crypto).

Usage:
    python scripts/collect_metals_to_db.py
"""

import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from tvscreener import FuturesScreener
from tvscreener.field.futures import FuturesField

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "history.db"
SYMBOLS = ["COMEX:GC1!", "COMEX:SI1!"]
MAX_RETRIES = 3
RETRY_DELAY = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

COLUMN_MAP = {
    # Basic
    "Description":          "name",
    "Close":                "price",
    "Change":               "change_pct",
    "High":                 "high",
    "Low":                  "low",
    "Open":                 "open",
    "Volume":               "volume",
    # Ratings
    "Recommend All":        "technical_rating",
    "Recommend Ma":         "ma_rating",
    "Recommend Other":      "oscillators_rating",
    # Oscillators
    "RSI":                  "rsi_14",
    "Rsi7":                 "rsi_7",
    "Stoch K":              "stoch_k",
    "Stoch D":              "stoch_d",
    "MACD MACD":            "macd_level",
    "MACD Signal":          "macd_signal",
    "MACD Hist":            "macd_hist",
    "Cci20":                "cci_20",
    "ADX":                  "adx_14",
    "AO":                   "awesome_osc",
    "Mom":                  "momentum_10",
    "W R":                  "williams_r_14",
    "UO":                   "uo",
    "Stoch RSI K":          "stoch_rsi_fast",
    "Stoch RSI D":          "stoch_rsi_slow",
    "ADX+Di":               "plus_di",
    "ADX-Di":               "minus_di",
    "Aroon Up":             "aroon_up",
    "Aroon Down":           "aroon_down",
    "Bbpower":              "bull_bear_power",
    "Roc":                  "roc_9",
    # Moving Averages
    "Ema10":  "ema_10",  "Ema20":  "ema_20",  "Ema50":  "ema_50",
    "Ema100": "ema_100", "Ema200": "ema_200",
    "Sma10":  "sma_10",  "Sma20":  "sma_20",  "Sma50":  "sma_50",
    "Sma100": "sma_100", "Sma200": "sma_200",
    "Hullma9": "hull_ma_9",
    "VWMA":    "vwma_20",
    # Bands
    "Bb Upper":           "bb_upper",
    "Bb Lower":           "bb_lower",
    "Kltchnl Upper":      "keltner_upper",
    "Kltchnl Lower":      "keltner_lower",
    "Donchch20 Upper":    "donchian_upper",
    "Donchch20 Lower":    "donchian_lower",
    # Volume / Money
    "VWAP":               "vwap",
    "Chaikinmoneyflow":   "cmf",
    "Moneyflow":          "mfi",
    # Volatility
    "ATR":   "atr_14",
    "P Sar": "parabolic_sar",
    # Ichimoku
    "Ichimoku Bline":  "ichimoku_base",
    "Ichimoku Cline":  "ichimoku_conv",
    "Ichimoku Lead1":  "ichimoku_lead_a",
    "Ichimoku Lead2":  "ichimoku_lead_b",
    # Pivot Fibonacci (NOTE: "Middle" is the pivot point, not "P")
    "Pivot M Fibonacci Middle": "pivot_fib_p",
    "Pivot M Fibonacci R1":     "pivot_fib_r1",
    "Pivot M Fibonacci R2":     "pivot_fib_r2",
    "Pivot M Fibonacci R3":     "pivot_fib_r3",
    "Pivot M Fibonacci S1":     "pivot_fib_s1",
    "Pivot M Fibonacci S2":     "pivot_fib_s2",
    "Pivot M Fibonacci S3":     "pivot_fib_s3",
    # Pivot Classic (NOTE: "Middle" is the pivot point, not "P")
    "Pivot M Classic Middle": "pivot_classic_p",
    "Pivot M Classic R1":     "pivot_classic_r1",
    "Pivot M Classic R2":     "pivot_classic_r2",
    "Pivot M Classic R3":     "pivot_classic_r3",
    "Pivot M Classic S1":     "pivot_classic_s1",
    "Pivot M Classic S2":     "pivot_classic_s2",
    "Pivot M Classic S3":     "pivot_classic_s3",
    # Candle patterns (daily — no |60 suffix)
    "Candle 3Whitesoldiers":    "candle_3white_soldiers",
    "Candle 3Blackcrows":       "candle_3black_crows",
    "Candle Morningstar":       "candle_morning_star",
    "Candle Eveningstar":       "candle_evening_star",
    "Candle Engulfing Bullish": "candle_engulfing_bull",
    "Candle Engulfing Bearish": "candle_engulfing_bear",
    "Candle Hammer":            "candle_hammer",
    "Candle Invertedhammer":    "candle_inv_hammer",
    "Candle Shootingstar":      "candle_shooting_star",
    "Candle Hangingman":        "candle_hanging_man",
}

RATING_SIGNAL_COLUMNS = [
    "technical_rating_signal",
    "ma_rating_signal",
    "oscillators_rating_signal",
]


def rating_signal(value) -> str | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:
        return None
    if v >= 0.5:   return "Strong Buy"
    if v >= 0.1:   return "Buy"
    if v > -0.1:   return "Neutral"
    if v > -0.5:   return "Sell"
    return "Strong Sell"


def build_fields():
    return [
        FuturesField.DESCRIPTION,
        FuturesField.CLOSE, FuturesField.CHANGE, FuturesField.HIGH,
        FuturesField.LOW, FuturesField.OPEN, FuturesField.VOLUME,
        # Ratings
        FuturesField.RECOMMEND_ALL, FuturesField.RECOMMEND_MA, FuturesField.RECOMMEND_OTHER,
        # Oscillators
        FuturesField.RSI, FuturesField.RSI7,
        FuturesField.STOCH_K, FuturesField.STOCH_D,
        FuturesField.MACD_MACD, FuturesField.MACD_SIGNAL, FuturesField.MACD_HIST,
        FuturesField.CCI20, FuturesField.ADX, FuturesField.ADX_PLUS_DI, FuturesField.ADX_MINUS_DI,
        FuturesField.AO, FuturesField.MOM, FuturesField.W_R, FuturesField.UO,
        FuturesField.STOCH_RSI_K, FuturesField.STOCH_RSI_D,
        FuturesField.AROON_UP, FuturesField.AROON_DOWN,
        FuturesField.BBPOWER, FuturesField.ROC,
        # MAs
        FuturesField.EMA10, FuturesField.EMA20, FuturesField.EMA50,
        FuturesField.EMA100, FuturesField.EMA200,
        FuturesField.SMA10, FuturesField.SMA20, FuturesField.SMA50,
        FuturesField.SMA100, FuturesField.SMA200,
        FuturesField.HULLMA9, FuturesField.VWMA,
        # Bands
        FuturesField.BB_UPPER, FuturesField.BB_LOWER,
        FuturesField.KLTCHNL_UPPER, FuturesField.KLTCHNL_LOWER,
        FuturesField.DONCHCH20_UPPER, FuturesField.DONCHCH20_LOWER,
        # Volume/Money
        FuturesField.VWAP, FuturesField.CHAIKINMONEYFLOW, FuturesField.MONEYFLOW,
        # Volatility
        FuturesField.ATR, FuturesField.P_SAR,
        # Ichimoku
        FuturesField.ICHIMOKU_BLINE, FuturesField.ICHIMOKU_CLINE,
        FuturesField.ICHIMOKU_LEAD1, FuturesField.ICHIMOKU_LEAD2,
        # Pivot Fibonacci (MIDDLE = the pivot point)
        FuturesField.PIVOT_M_FIBONACCI_MIDDLE,
        FuturesField.PIVOT_M_FIBONACCI_R1, FuturesField.PIVOT_M_FIBONACCI_R2, FuturesField.PIVOT_M_FIBONACCI_R3,
        FuturesField.PIVOT_M_FIBONACCI_S1, FuturesField.PIVOT_M_FIBONACCI_S2, FuturesField.PIVOT_M_FIBONACCI_S3,
        # Pivot Classic (MIDDLE = the pivot point)
        FuturesField.PIVOT_M_CLASSIC_MIDDLE,
        FuturesField.PIVOT_M_CLASSIC_R1, FuturesField.PIVOT_M_CLASSIC_R2, FuturesField.PIVOT_M_CLASSIC_R3,
        FuturesField.PIVOT_M_CLASSIC_S1, FuturesField.PIVOT_M_CLASSIC_S2, FuturesField.PIVOT_M_CLASSIC_S3,
        # Candle patterns
        FuturesField.CANDLE_3WHITESOLDIERS, FuturesField.CANDLE_3BLACKCROWS,
        FuturesField.CANDLE_MORNINGSTAR, FuturesField.CANDLE_EVENINGSTAR,
        FuturesField.CANDLE_ENGULFING_BULLISH, FuturesField.CANDLE_ENGULFING_BEARISH,
        FuturesField.CANDLE_HAMMER, FuturesField.CANDLE_INVERTEDHAMMER,
        FuturesField.CANDLE_SHOOTINGSTAR, FuturesField.CANDLE_HANGINGMAN,
    ]


def collect_and_store():
    # collected_at = UTC midnight (daily boundary)
    now_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    collected_at = now_utc.isoformat()

    fs = FuturesScreener()
    fs.misc['symbols'] = {'query': {'types': []}, 'tickers': SYMBOLS}
    fs.select(*build_fields())

    log.info("Querying TradingView for %s ...", SYMBOLS)
    df = fs.get()

    if df.empty:
        log.warning("Empty DataFrame returned — no data written.")
        return 0

    rows_inserted = 0

    with sqlite3.connect(DB_PATH) as conn:
        for _, row in df.iterrows():
            symbol = row.get("Symbol", "")
            values = {"collected_at": collected_at, "symbol": symbol}

            for df_col, sql_col in COLUMN_MAP.items():
                val = row.get(df_col)
                if val is not None and isinstance(val, float) and val != val:
                    val = None
                values[sql_col] = val

            values["technical_rating_signal"] = rating_signal(values.get("technical_rating"))
            values["ma_rating_signal"] = rating_signal(values.get("ma_rating"))
            values["oscillators_rating_signal"] = rating_signal(values.get("oscillators_rating"))

            columns = list(values.keys())
            placeholders = ", ".join("?" for _ in columns)
            col_names = ", ".join(columns)
            sql = f"INSERT OR IGNORE INTO technical_indicators ({col_names}) VALUES ({placeholders})"
            cursor = conn.execute(sql, [values[c] for c in columns])
            rows_inserted += max(0, cursor.rowcount)

    log.info("Inserted %d row(s) at %s", rows_inserted, collected_at)
    return rows_inserted


def main():
    if not DB_PATH.exists():
        log.error("DB not found: %s — run collect_to_db.py first to initialise", DB_PATH)
        sys.exit(1)

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            n = collect_and_store()
            log.info("Done. %d row(s) written.", n)
            return
        except Exception as e:
            last_err = e
            log.error("Attempt %d/%d failed: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                log.info("Retrying in %ds ...", RETRY_DELAY)
                time.sleep(RETRY_DELAY)

    log.critical("All %d attempts failed. Last error: %s", MAX_RETRIES, last_err)
    sys.exit(1)


if __name__ == "__main__":
    main()
