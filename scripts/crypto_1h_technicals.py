"""
Crypto 1H Technical Indicators
===============================
Query any cryptocurrency's 1H technical indicators from TradingView.

Usage:
    python scripts/crypto_1h_technicals.py              # Default: BTC
    python scripts/crypto_1h_technicals.py BTC
    python scripts/crypto_1h_technicals.py ETH
    python scripts/crypto_1h_technicals.py SOL
    python scripts/crypto_1h_technicals.py BTC ETH SOL  # Multiple coins
"""

import sys
import io
import argparse

# Windows UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from tvscreener import CryptoScreener, CryptoField

# ============================================================
# Common coin -> Binance ticker mapping
# ============================================================
COIN_MAP = {
    "BTC":   "BINANCE:BTCUSDT",
    "ETH":   "BINANCE:ETHUSDT",
    "SOL":   "BINANCE:SOLUSDT",
    "BNB":   "BINANCE:BNBUSDT",
    "XRP":   "BINANCE:XRPUSDT",
    "ADA":   "BINANCE:ADAUSDT",
    "DOGE":  "BINANCE:DOGEUSDT",
}


def resolve_ticker(coin: str) -> str:
    """Resolve coin symbol to EXCHANGE:PAIR format."""
    coin = coin.upper().strip()
    if ":" in coin:
        return coin  # Already in EXCHANGE:PAIR format
    if coin in COIN_MAP:
        return COIN_MAP[coin]
    # Fallback: assume Binance USDT pair
    return f"BINANCE:{coin}USDT"


# ============================================================
# Parse arguments
# ============================================================
parser = argparse.ArgumentParser(description="Crypto 1H Technical Indicators")
parser.add_argument(
    "coins",
    nargs="*",
    default=["BTC"],
    help="Coin symbols (e.g. BTC ETH SOL) or full tickers (e.g. BINANCE:BTCUSDT)",
)
args = parser.parse_args()

tickers = [resolve_ticker(c) for c in args.coins]

# ============================================================
# Build screener
# ============================================================
cs = CryptoScreener()

cs.symbols = {
    "query": {"types": []},
    "tickers": tickers,
}

INTERVAL = "60"  # 1H

# --- Rating ---
rating = CryptoField.TECHNICAL_RATING.with_interval(INTERVAL)
ma_rating = CryptoField.MOVING_AVERAGES_RATING.with_interval(INTERVAL)
osc_rating = CryptoField.OSCILLATORS_RATING.with_interval(INTERVAL)

# --- Oscillators ---
rsi_14 = CryptoField.RELATIVE_STRENGTH_INDEX_14.with_interval(INTERVAL)
rsi_7 = CryptoField.RELATIVE_STRENGTH_INDEX_7.with_interval(INTERVAL)
stoch_k = CryptoField.STOCHASTIC_PERCENTK_14_3_3.with_interval(INTERVAL)
stoch_d = CryptoField.STOCHASTIC_PERCENTD_14_3_3.with_interval(INTERVAL)
macd_level = CryptoField.MACD_LEVEL_12_26.with_interval(INTERVAL)
macd_signal = CryptoField.MACD_SIGNAL_12_26.with_interval(INTERVAL)
macd_hist = CryptoField.MACD_HIST.with_interval(INTERVAL)
cci = CryptoField.COMMODITY_CHANNEL_INDEX_20.with_interval(INTERVAL)
adx = CryptoField.AVERAGE_DIRECTIONAL_INDEX_14.with_interval(INTERVAL)
awesome_osc = CryptoField.AWESOME_OSCILLATOR.with_interval(INTERVAL)
momentum = CryptoField.MOMENTUM_10.with_interval(INTERVAL)
williams_r = CryptoField.WILLIAMS_PERCENT_RANGE_14.with_interval(INTERVAL)
uo = CryptoField.ULTIMATE_OSCILLATOR_7_14_28.with_interval(INTERVAL)
stoch_rsi_fast = CryptoField.STOCHASTIC_RSI_FAST_3_3_14_14.with_interval(INTERVAL)
stoch_rsi_slow = CryptoField.STOCHASTIC_RSI_SLOW_3_3_14_14.with_interval(INTERVAL)
plus_di = CryptoField.POSITIVE_DIRECTIONAL_INDICATOR_14.with_interval(INTERVAL)
minus_di = CryptoField.NEGATIVE_DIRECTIONAL_INDICATOR_14.with_interval(INTERVAL)
aroon_up = CryptoField.AROON_UP_14.with_interval(INTERVAL)
aroon_down = CryptoField.AROON_DOWN_14.with_interval(INTERVAL)
bull_bear = CryptoField.BULL_BEAR_POWER.with_interval(INTERVAL)
roc = CryptoField.RATE_OF_CHANGE_9.with_interval(INTERVAL)

# --- Moving Averages ---
ema_10 = CryptoField.EXPONENTIAL_MOVING_AVERAGE_10.with_interval(INTERVAL)
ema_20 = CryptoField.EXPONENTIAL_MOVING_AVERAGE_20.with_interval(INTERVAL)
ema_50 = CryptoField.EXPONENTIAL_MOVING_AVERAGE_50.with_interval(INTERVAL)
ema_100 = CryptoField.EXPONENTIAL_MOVING_AVERAGE_100.with_interval(INTERVAL)
ema_200 = CryptoField.EXPONENTIAL_MOVING_AVERAGE_200.with_interval(INTERVAL)
sma_10 = CryptoField.SIMPLE_MOVING_AVERAGE_10.with_interval(INTERVAL)
sma_20 = CryptoField.SIMPLE_MOVING_AVERAGE_20.with_interval(INTERVAL)
sma_50 = CryptoField.SIMPLE_MOVING_AVERAGE_50.with_interval(INTERVAL)
sma_100 = CryptoField.SIMPLE_MOVING_AVERAGE_100.with_interval(INTERVAL)
sma_200 = CryptoField.SIMPLE_MOVING_AVERAGE_200.with_interval(INTERVAL)
hull_ma = CryptoField.HULL_MOVING_AVERAGE_9.with_interval(INTERVAL)
vwma = CryptoField.VOLUME_WEIGHTED_MOVING_AVERAGE_20.with_interval(INTERVAL)

# --- Bollinger Bands ---
bb_upper = CryptoField.BOLLINGER_UPPER_BAND_20.with_interval(INTERVAL)
bb_lower = CryptoField.BOLLINGER_LOWER_BAND_20.with_interval(INTERVAL)

# --- Keltner Channels ---
keltner_upper = CryptoField.KELTNER_CHANNELS_UPPER_BAND_20.with_interval(INTERVAL)
keltner_lower = CryptoField.KELTNER_CHANNELS_LOWER_BAND_20.with_interval(INTERVAL)

# --- Donchian Channels ---
donchian_upper = CryptoField.DONCHIAN_CHANNELS_UPPER_BAND_20.with_interval(INTERVAL)
donchian_lower = CryptoField.DONCHIAN_CHANNELS_LOWER_BAND_20.with_interval(INTERVAL)

# --- Volume Indicators ---
vwap = CryptoField.VOLUME_WEIGHTED_AVERAGE_PRICE.with_interval(INTERVAL)
cmf = CryptoField.CHAIKINMONEYFLOW.with_interval(INTERVAL)
mfi = CryptoField.MONEYFLOW.with_interval(INTERVAL)

# --- Ichimoku ---
ichimoku_base = CryptoField.ICHIMOKU_BASE_LINE_9_26_52_26.with_interval(INTERVAL)
ichimoku_conv = CryptoField.ICHIMOKU_CONVERSION_LINE_9_26_52_26.with_interval(INTERVAL)
ichimoku_lead_a = CryptoField.ICHIMOKU_LEADING_SPAN_A_9_26_52_26.with_interval(INTERVAL)
ichimoku_lead_b = CryptoField.ICHIMOKU_LEADING_SPAN_B_9_26_52_26.with_interval(INTERVAL)

# --- Pivot Points: Classic ---
pivot_classic_p = CryptoField.PIVOT_CLASSIC_P.with_interval(INTERVAL)
pivot_classic_r1 = CryptoField.PIVOT_CLASSIC_R1.with_interval(INTERVAL)
pivot_classic_r2 = CryptoField.PIVOT_CLASSIC_R2.with_interval(INTERVAL)
pivot_classic_r3 = CryptoField.PIVOT_CLASSIC_R3.with_interval(INTERVAL)
pivot_classic_s1 = CryptoField.PIVOT_CLASSIC_S1.with_interval(INTERVAL)
pivot_classic_s2 = CryptoField.PIVOT_CLASSIC_S2.with_interval(INTERVAL)
pivot_classic_s3 = CryptoField.PIVOT_CLASSIC_S3.with_interval(INTERVAL)

# --- Pivot Points: Fibonacci ---
pivot_fib_p = CryptoField.PIVOT_FIBONACCI_P.with_interval(INTERVAL)
pivot_fib_r1 = CryptoField.PIVOT_FIBONACCI_R1.with_interval(INTERVAL)
pivot_fib_r2 = CryptoField.PIVOT_FIBONACCI_R2.with_interval(INTERVAL)
pivot_fib_r3 = CryptoField.PIVOT_FIBONACCI_R3.with_interval(INTERVAL)
pivot_fib_s1 = CryptoField.PIVOT_FIBONACCI_S1.with_interval(INTERVAL)
pivot_fib_s2 = CryptoField.PIVOT_FIBONACCI_S2.with_interval(INTERVAL)
pivot_fib_s3 = CryptoField.PIVOT_FIBONACCI_S3.with_interval(INTERVAL)

# --- Other ---
atr = CryptoField.AVERAGE_TRUE_RANGE_14.with_interval(INTERVAL)
parabolic_sar = CryptoField.PARABOLIC_SAR.with_interval(INTERVAL)

# ============================================================
# Select all fields
# ============================================================
cs.select(
    # Price
    CryptoField.NAME,
    CryptoField.PRICE,
    CryptoField.CHANGE_PERCENT,
    CryptoField.HIGH,
    CryptoField.LOW,
    CryptoField.OPEN,
    CryptoField.VOLUME,
    # Rating
    rating, ma_rating, osc_rating,
    # Oscillators
    rsi_14, rsi_7,
    stoch_k, stoch_d,
    macd_level, macd_signal, macd_hist,
    cci, adx, awesome_osc, momentum, williams_r, uo,
    stoch_rsi_fast, stoch_rsi_slow,
    plus_di, minus_di,
    aroon_up, aroon_down,
    bull_bear, roc,
    # Moving Averages
    ema_10, ema_20, ema_50, ema_100, ema_200,
    sma_10, sma_20, sma_50, sma_100, sma_200,
    hull_ma, vwma,
    # Bollinger Bands
    bb_upper, bb_lower,
    # Keltner Channels
    keltner_upper, keltner_lower,
    # Donchian Channels
    donchian_upper, donchian_lower,
    # Volume Indicators
    vwap, cmf, mfi,
    # Ichimoku
    ichimoku_base, ichimoku_conv, ichimoku_lead_a, ichimoku_lead_b,
    # Pivot Classic
    pivot_classic_p,
    pivot_classic_r1, pivot_classic_r2, pivot_classic_r3,
    pivot_classic_s1, pivot_classic_s2, pivot_classic_s3,
    # Pivot Fibonacci
    pivot_fib_p,
    pivot_fib_r1, pivot_fib_r2, pivot_fib_r3,
    pivot_fib_s1, pivot_fib_s2, pivot_fib_s3,
    # Other
    atr, parabolic_sar,
)

# ============================================================
# Execute
# ============================================================
df = cs.get()

# ============================================================
# Display
# ============================================================

def fmt(val, decimals=2):
    if val is None or (isinstance(val, float) and val != val):
        return "--"
    if isinstance(val, float):
        return f"{val:,.{decimals}f}"
    return str(val)


def rating_label(val):
    if val is None or (isinstance(val, float) and val != val):
        return "--"
    if isinstance(val, (int, float)):
        if val >= 0.5:
            return f"{val:+.2f}  (Buy)"
        elif val <= -0.5:
            return f"{val:+.2f}  (Sell)"
        else:
            return f"{val:+.2f}  (Neutral)"
    return str(val)


def print_section(title, keywords, row, skip=None):
    skip = skip or ["Reco.", "Prev.", "Rating"]
    print(f"\n--- {title} ---")
    for col in df.columns:
        if any(sk in col for sk in skip):
            continue
        if any(kw in col for kw in keywords):
            print(f"  {col:<48} {fmt(row[col])}")


if df.empty:
    print("No data returned. Please check the ticker name.")
    sys.exit(1)

for idx, row in df.iterrows():
    name = row.get("Name", "N/A")
    print("=" * 64)
    print(f"  {name}  |  1H Technical Indicators")
    print("=" * 64)

    # --- Price ---
    print(f"\n  {'Price':<28} {fmt(row.get('Price'))}")
    print(f"  {'Change %':<28} {fmt(row.get('Change %'))} %")
    print(f"  {'High':<28} {fmt(row.get('High'))}")
    print(f"  {'Low':<28} {fmt(row.get('Low'))}")
    print(f"  {'Open':<28} {fmt(row.get('Open'))}")
    print(f"  {'Volume':<28} {fmt(row.get('Volume'))}")

    # --- Rating ---
    print(f"\n--- Rating (1H) ---")
    for col in df.columns:
        if "Technical Rating" in col or "Moving Averages Rating" in col or "Oscillators Rating" in col:
            print(f"  {col:<48} {rating_label(row[col])}")

    # --- Oscillators ---
    print_section("Oscillators (1H)", [
        "RSI", "Stochastic", "MACD", "CCI", "ADX",
        "Awesome", "Momentum", "Williams", "Ultimate",
        "Directional Indicator", "Aroon", "Bull Bear", "Rate Of Change",
    ], row)

    # --- Moving Averages ---
    print_section("Moving Averages (1H)", [
        "Exponential Moving", "Simple Moving", "Hull",
        "Volume Weighted Moving",
    ], row)

    # --- Bollinger Bands ---
    print_section("Bollinger Bands (1H)", ["Bollinger"], row)

    # --- Keltner Channels ---
    print_section("Keltner Channels (1H)", ["Keltner"], row)

    # --- Donchian Channels ---
    print_section("Donchian Channels (1H)", ["Donchian"], row)

    # --- Volume Indicators ---
    print_section("Volume Indicators (1H)", [
        "Volume Weighted Average Price", "Chaikin", "Moneyflow",
    ], row)

    # --- Ichimoku ---
    print_section("Ichimoku Cloud (1H)", ["Ichimoku"], row)

    # --- Pivot Classic ---
    print_section("Pivot Points - Classic (1H)", ["Pivot Classic", "Pivot M Classic"], row)

    # --- Pivot Fibonacci ---
    print_section("Pivot Points - Fibonacci (1H)", ["Pivot Fibonacci", "Pivot M Fibonacci"], row)

    # --- ATR / SAR ---
    print_section("Volatility (1H)", ["ATR", "Average True Range", "Parabolic"], row)

    print()
