"""
Collect BTC/ETH 1H technical indicators from TradingView and store in SQLite.

Usage:
    python scripts/collect_to_db.py
"""

import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from tvscreener import CryptoScreener, CryptoField

# ============================================================
# Constants
# ============================================================
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "history.db"
SYMBOLS = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]
INTERVAL = "60"  # 1H
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

# ============================================================
# Column mapping: DataFrame label -> SQLite column name
# ============================================================
# Keys are the exact pandas column names returned by CryptoScreener.get().
# Non-interval fields use their base label (e.g. "Name", "Price").
# Interval fields use f"{label} ({interval})" (e.g. "Technical Rating (60)").

COLUMN_MAP = {
    # --- Price / basic ---
    "Name":       "name",
    "Price":      "price",
    "Change %":   "change_pct",
    "High":       "high",
    "Low":        "low",
    "Open":       "open",
    "Volume":     "volume",

    # --- Ratings (1H) ---
    f"Technical Rating ({INTERVAL})":         "technical_rating",
    f"Moving Averages Rating ({INTERVAL})":   "ma_rating",
    f"Oscillators Rating ({INTERVAL})":       "oscillators_rating",

    # --- Oscillators (1H) ---
    f"Relative Strength Index (14) ({INTERVAL})":     "rsi_14",
    f"Relative Strength Index (7) ({INTERVAL})":      "rsi_7",
    f"Stochastic %K (14, 3, 3) ({INTERVAL})":         "stoch_k",
    f"Stochastic %D (14, 3, 3) ({INTERVAL})":         "stoch_d",
    f"MACD Level (12, 26) ({INTERVAL})":               "macd_level",
    f"MACD Signal (12, 26) ({INTERVAL})":              "macd_signal",
    f"MACD Hist ({INTERVAL})":                         "macd_hist",
    f"Commodity Channel Index (20) ({INTERVAL})":      "cci_20",
    f"Average Directional Index (14) ({INTERVAL})":    "adx_14",
    f"Awesome Oscillator ({INTERVAL})":                "awesome_osc",
    f"Momentum (10) ({INTERVAL})":                     "momentum_10",
    f"Williams Percent Range (14) ({INTERVAL})":       "williams_r_14",
    f"Ultimate Oscillator (7, 14, 28) ({INTERVAL})":   "uo",
    f"Stochastic RSI Fast (3, 3, 14, 14) ({INTERVAL})": "stoch_rsi_fast",
    f"Stochastic RSI Slow (3, 3, 14, 14) ({INTERVAL})": "stoch_rsi_slow",
    f"Positive Directional Indicator (14) ({INTERVAL})": "plus_di",
    f"Negative Directional Indicator (14) ({INTERVAL})": "minus_di",
    f"Aroon Up (14) ({INTERVAL})":                     "aroon_up",
    f"Aroon Down (14) ({INTERVAL})":                   "aroon_down",
    f"Bull Bear Power ({INTERVAL})":                   "bull_bear_power",
    f"Rate Of Change (9) ({INTERVAL})":                "roc_9",

    # --- Moving Averages (1H) ---
    f"Exponential Moving Average (10) ({INTERVAL})":   "ema_10",
    f"Exponential Moving Average (20) ({INTERVAL})":   "ema_20",
    f"Exponential Moving Average (50) ({INTERVAL})":   "ema_50",
    f"Exponential Moving Average (100) ({INTERVAL})":  "ema_100",
    f"Exponential Moving Average (200) ({INTERVAL})":  "ema_200",
    f"Simple Moving Average (10) ({INTERVAL})":        "sma_10",
    f"Simple Moving Average (20) ({INTERVAL})":        "sma_20",
    f"Simple Moving Average (50) ({INTERVAL})":        "sma_50",
    f"Simple Moving Average (100) ({INTERVAL})":       "sma_100",
    f"Simple Moving Average (200) ({INTERVAL})":       "sma_200",
    f"Hull Moving Average (9) ({INTERVAL})":           "hull_ma_9",
    f"Volume Weighted Moving Average (20) ({INTERVAL})": "vwma_20",

    # --- Bollinger Bands (1H) ---
    f"Bollinger Upper Band (20) ({INTERVAL})":         "bb_upper",
    f"Bollinger Lower Band (20) ({INTERVAL})":         "bb_lower",

    # --- Keltner Channels (1H) ---
    f"Keltner Channels Upper Band (20) ({INTERVAL})":  "keltner_upper",
    f"Keltner Channels Lower Band (20) ({INTERVAL})":  "keltner_lower",

    # --- Donchian Channels (1H) ---
    f"Donchian Channels Upper Band (20) ({INTERVAL})": "donchian_upper",
    f"Donchian Channels Lower Band (20) ({INTERVAL})": "donchian_lower",

    # --- Volume Indicators (1H) ---
    f"Volume Weighted Average Price ({INTERVAL})":     "vwap",
    f"Chaikinmoneyflow ({INTERVAL})":                  "cmf",
    f"Moneyflow ({INTERVAL})":                         "mfi",

    # --- Ichimoku (1H) ---
    f"Ichimoku Base Line (9, 26, 52, 26) ({INTERVAL})":       "ichimoku_base",
    f"Ichimoku Conversion Line (9, 26, 52, 26) ({INTERVAL})": "ichimoku_conv",
    f"Ichimoku Leading Span A (9, 26, 52, 26) ({INTERVAL})":  "ichimoku_lead_a",
    f"Ichimoku Leading Span B (9, 26, 52, 26) ({INTERVAL})":  "ichimoku_lead_b",

    # --- Pivot Points: Classic (1H) ---
    f"Pivot Classic P ({INTERVAL})":   "pivot_classic_p",
    f"Pivot Classic R1 ({INTERVAL})":  "pivot_classic_r1",
    f"Pivot Classic R2 ({INTERVAL})":  "pivot_classic_r2",
    f"Pivot Classic R3 ({INTERVAL})":  "pivot_classic_r3",
    f"Pivot Classic S1 ({INTERVAL})":  "pivot_classic_s1",
    f"Pivot Classic S2 ({INTERVAL})":  "pivot_classic_s2",
    f"Pivot Classic S3 ({INTERVAL})":  "pivot_classic_s3",

    # --- Pivot Points: Fibonacci (1H) ---
    f"Pivot Fibonacci P ({INTERVAL})":   "pivot_fib_p",
    f"Pivot Fibonacci R1 ({INTERVAL})":  "pivot_fib_r1",
    f"Pivot Fibonacci R2 ({INTERVAL})":  "pivot_fib_r2",
    f"Pivot Fibonacci R3 ({INTERVAL})":  "pivot_fib_r3",
    f"Pivot Fibonacci S1 ({INTERVAL})":  "pivot_fib_s1",
    f"Pivot Fibonacci S2 ({INTERVAL})":  "pivot_fib_s2",
    f"Pivot Fibonacci S3 ({INTERVAL})":  "pivot_fib_s3",

    # --- Volatility (1H) ---
    f"Average True Range (14) ({INTERVAL})":  "atr_14",
    f"Parabolic SAR ({INTERVAL})":            "parabolic_sar",
}

# SQL column names for the indicator data (excludes id, collected_at, symbol)
SQL_COLUMNS = list(COLUMN_MAP.values())

# Rating signal columns appended after the three rating values
RATING_SIGNAL_COLUMNS = [
    "technical_rating_signal",
    "ma_rating_signal",
    "oscillators_rating_signal",
]

ALL_DB_COLUMNS = (
    ["collected_at", "symbol"]
    + SQL_COLUMNS
    + RATING_SIGNAL_COLUMNS
)


# ============================================================
# Rating signal helper
# ============================================================
def rating_signal(value) -> str | None:
    """Convert a numeric rating (-1..+1) to a human-readable signal string."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN check
        return None
    if v >= 0.5:
        return "Strong Buy"
    if v >= 0.1:
        return "Buy"
    if v > -0.1:
        return "Neutral"
    if v > -0.5:
        return "Sell"
    return "Strong Sell"


# ============================================================
# Build fields list (mirrors crypto_1h_technicals.py)
# ============================================================
def build_fields():
    """Return the list of CryptoField / FieldWithInterval to query."""
    I = INTERVAL  # noqa: E741
    return [
        # Price / basic
        CryptoField.NAME,
        CryptoField.PRICE,
        CryptoField.CHANGE_PERCENT,
        CryptoField.HIGH,
        CryptoField.LOW,
        CryptoField.OPEN,
        CryptoField.VOLUME,
        # Ratings
        CryptoField.TECHNICAL_RATING.with_interval(I),
        CryptoField.MOVING_AVERAGES_RATING.with_interval(I),
        CryptoField.OSCILLATORS_RATING.with_interval(I),
        # Oscillators
        CryptoField.RELATIVE_STRENGTH_INDEX_14.with_interval(I),
        CryptoField.RELATIVE_STRENGTH_INDEX_7.with_interval(I),
        CryptoField.STOCHASTIC_PERCENTK_14_3_3.with_interval(I),
        CryptoField.STOCHASTIC_PERCENTD_14_3_3.with_interval(I),
        CryptoField.MACD_LEVEL_12_26.with_interval(I),
        CryptoField.MACD_SIGNAL_12_26.with_interval(I),
        CryptoField.MACD_HIST.with_interval(I),
        CryptoField.COMMODITY_CHANNEL_INDEX_20.with_interval(I),
        CryptoField.AVERAGE_DIRECTIONAL_INDEX_14.with_interval(I),
        CryptoField.AWESOME_OSCILLATOR.with_interval(I),
        CryptoField.MOMENTUM_10.with_interval(I),
        CryptoField.WILLIAMS_PERCENT_RANGE_14.with_interval(I),
        CryptoField.ULTIMATE_OSCILLATOR_7_14_28.with_interval(I),
        CryptoField.STOCHASTIC_RSI_FAST_3_3_14_14.with_interval(I),
        CryptoField.STOCHASTIC_RSI_SLOW_3_3_14_14.with_interval(I),
        CryptoField.POSITIVE_DIRECTIONAL_INDICATOR_14.with_interval(I),
        CryptoField.NEGATIVE_DIRECTIONAL_INDICATOR_14.with_interval(I),
        CryptoField.AROON_UP_14.with_interval(I),
        CryptoField.AROON_DOWN_14.with_interval(I),
        CryptoField.BULL_BEAR_POWER.with_interval(I),
        CryptoField.RATE_OF_CHANGE_9.with_interval(I),
        # Moving Averages
        CryptoField.EXPONENTIAL_MOVING_AVERAGE_10.with_interval(I),
        CryptoField.EXPONENTIAL_MOVING_AVERAGE_20.with_interval(I),
        CryptoField.EXPONENTIAL_MOVING_AVERAGE_50.with_interval(I),
        CryptoField.EXPONENTIAL_MOVING_AVERAGE_100.with_interval(I),
        CryptoField.EXPONENTIAL_MOVING_AVERAGE_200.with_interval(I),
        CryptoField.SIMPLE_MOVING_AVERAGE_10.with_interval(I),
        CryptoField.SIMPLE_MOVING_AVERAGE_20.with_interval(I),
        CryptoField.SIMPLE_MOVING_AVERAGE_50.with_interval(I),
        CryptoField.SIMPLE_MOVING_AVERAGE_100.with_interval(I),
        CryptoField.SIMPLE_MOVING_AVERAGE_200.with_interval(I),
        CryptoField.HULL_MOVING_AVERAGE_9.with_interval(I),
        CryptoField.VOLUME_WEIGHTED_MOVING_AVERAGE_20.with_interval(I),
        # Bollinger Bands
        CryptoField.BOLLINGER_UPPER_BAND_20.with_interval(I),
        CryptoField.BOLLINGER_LOWER_BAND_20.with_interval(I),
        # Keltner Channels
        CryptoField.KELTNER_CHANNELS_UPPER_BAND_20.with_interval(I),
        CryptoField.KELTNER_CHANNELS_LOWER_BAND_20.with_interval(I),
        # Donchian Channels
        CryptoField.DONCHIAN_CHANNELS_UPPER_BAND_20.with_interval(I),
        CryptoField.DONCHIAN_CHANNELS_LOWER_BAND_20.with_interval(I),
        # Volume Indicators
        CryptoField.VOLUME_WEIGHTED_AVERAGE_PRICE.with_interval(I),
        CryptoField.CHAIKINMONEYFLOW.with_interval(I),
        CryptoField.MONEYFLOW.with_interval(I),
        # Ichimoku
        CryptoField.ICHIMOKU_BASE_LINE_9_26_52_26.with_interval(I),
        CryptoField.ICHIMOKU_CONVERSION_LINE_9_26_52_26.with_interval(I),
        CryptoField.ICHIMOKU_LEADING_SPAN_A_9_26_52_26.with_interval(I),
        CryptoField.ICHIMOKU_LEADING_SPAN_B_9_26_52_26.with_interval(I),
        # Pivot Classic
        CryptoField.PIVOT_CLASSIC_P.with_interval(I),
        CryptoField.PIVOT_CLASSIC_R1.with_interval(I),
        CryptoField.PIVOT_CLASSIC_R2.with_interval(I),
        CryptoField.PIVOT_CLASSIC_R3.with_interval(I),
        CryptoField.PIVOT_CLASSIC_S1.with_interval(I),
        CryptoField.PIVOT_CLASSIC_S2.with_interval(I),
        CryptoField.PIVOT_CLASSIC_S3.with_interval(I),
        # Pivot Fibonacci
        CryptoField.PIVOT_FIBONACCI_P.with_interval(I),
        CryptoField.PIVOT_FIBONACCI_R1.with_interval(I),
        CryptoField.PIVOT_FIBONACCI_R2.with_interval(I),
        CryptoField.PIVOT_FIBONACCI_R3.with_interval(I),
        CryptoField.PIVOT_FIBONACCI_S1.with_interval(I),
        CryptoField.PIVOT_FIBONACCI_S2.with_interval(I),
        CryptoField.PIVOT_FIBONACCI_S3.with_interval(I),
        # Volatility
        CryptoField.AVERAGE_TRUE_RANGE_14.with_interval(I),
        CryptoField.PARABOLIC_SAR.with_interval(I),
    ]


# ============================================================
# Database
# ============================================================
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS technical_indicators (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_at                TEXT    NOT NULL,
    symbol                      TEXT    NOT NULL,

    -- Price / basic
    name                        TEXT,
    price                       REAL,
    change_pct                  REAL,
    high                        REAL,
    low                         REAL,
    open                        REAL,
    volume                      REAL,

    -- Ratings (1H) — numeric + human-readable signal
    technical_rating            REAL,
    technical_rating_signal     TEXT,
    ma_rating                   REAL,
    ma_rating_signal            TEXT,
    oscillators_rating          REAL,
    oscillators_rating_signal   TEXT,

    -- Oscillators (1H)
    rsi_14                      REAL,
    rsi_7                       REAL,
    stoch_k                     REAL,
    stoch_d                     REAL,
    macd_level                  REAL,
    macd_signal                 REAL,
    macd_hist                   REAL,
    cci_20                      REAL,
    adx_14                      REAL,
    awesome_osc                 REAL,
    momentum_10                 REAL,
    williams_r_14               REAL,
    uo                          REAL,
    stoch_rsi_fast              REAL,
    stoch_rsi_slow              REAL,
    plus_di                     REAL,
    minus_di                    REAL,
    aroon_up                    REAL,
    aroon_down                  REAL,
    bull_bear_power             REAL,
    roc_9                       REAL,

    -- Moving Averages (1H)
    ema_10                      REAL,
    ema_20                      REAL,
    ema_50                      REAL,
    ema_100                     REAL,
    ema_200                     REAL,
    sma_10                      REAL,
    sma_20                      REAL,
    sma_50                      REAL,
    sma_100                     REAL,
    sma_200                     REAL,
    hull_ma_9                   REAL,
    vwma_20                     REAL,

    -- Bollinger Bands (1H)
    bb_upper                    REAL,
    bb_lower                    REAL,

    -- Keltner Channels (1H)
    keltner_upper               REAL,
    keltner_lower               REAL,

    -- Donchian Channels (1H)
    donchian_upper              REAL,
    donchian_lower              REAL,

    -- Volume Indicators (1H)
    vwap                        REAL,
    cmf                         REAL,
    mfi                         REAL,

    -- Ichimoku (1H)
    ichimoku_base               REAL,
    ichimoku_conv               REAL,
    ichimoku_lead_a             REAL,
    ichimoku_lead_b             REAL,

    -- Pivot Classic (1H)
    pivot_classic_p             REAL,
    pivot_classic_r1            REAL,
    pivot_classic_r2            REAL,
    pivot_classic_r3            REAL,
    pivot_classic_s1            REAL,
    pivot_classic_s2            REAL,
    pivot_classic_s3            REAL,

    -- Pivot Fibonacci (1H)
    pivot_fib_p                 REAL,
    pivot_fib_r1                REAL,
    pivot_fib_r2                REAL,
    pivot_fib_r3                REAL,
    pivot_fib_s1                REAL,
    pivot_fib_s2                REAL,
    pivot_fib_s3                REAL,

    -- Volatility (1H)
    atr_14                      REAL,
    parabolic_sar               REAL
);
"""

CREATE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_symbol_time
    ON technical_indicators(symbol, collected_at);
"""


def init_db():
    """Create the database and table if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)
    conn.execute(CREATE_INDEX_SQL)
    conn.commit()
    conn.close()
    log.info("Database ready: %s", DB_PATH)


# ============================================================
# Collect and store
# ============================================================
def collect_and_store():
    """Query TradingView screener and insert rows into SQLite."""
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    collected_at = now_utc.isoformat()

    # Build screener query
    cs = CryptoScreener()
    cs.symbols = {"query": {"types": []}, "tickers": SYMBOLS}
    cs.select(*build_fields())

    log.info("Querying TradingView for %s ...", SYMBOLS)
    df = cs.get()

    if df.empty:
        log.warning("Empty DataFrame returned — no data written.")
        return 0

    # Filter out auto-generated columns we don't want
    skip_prefixes = ("Update Mode", "Reco.", "Prev.")

    conn = sqlite3.connect(DB_PATH)
    rows_inserted = 0

    for _, row in df.iterrows():
        symbol = row.get("Symbol", "")

        # Map DataFrame columns → SQL values
        values = {"collected_at": collected_at, "symbol": symbol}
        for df_col, sql_col in COLUMN_MAP.items():
            if any(df_col.startswith(p) for p in skip_prefixes):
                continue
            val = row.get(df_col)
            # Convert NaN to None
            if val is not None and isinstance(val, float) and val != val:
                val = None
            values[sql_col] = val

        # Compute rating signal text
        values["technical_rating_signal"] = rating_signal(values.get("technical_rating"))
        values["ma_rating_signal"] = rating_signal(values.get("ma_rating"))
        values["oscillators_rating_signal"] = rating_signal(values.get("oscillators_rating"))

        columns = list(values.keys())
        placeholders = ", ".join("?" for _ in columns)
        col_names = ", ".join(columns)
        sql = f"INSERT OR IGNORE INTO technical_indicators ({col_names}) VALUES ({placeholders})"

        conn.execute(sql, [values[c] for c in columns])
        rows_inserted += 1

    conn.commit()
    conn.close()
    log.info("Inserted %d row(s) at %s", rows_inserted, collected_at)
    return rows_inserted


# ============================================================
# Main with retry
# ============================================================
def main():
    init_db()

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
