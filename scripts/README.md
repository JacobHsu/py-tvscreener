# Scripts

## crypto_1h_technicals.py

Query any cryptocurrency's 1H technical indicators from TradingView via tvscreener.

### Prerequisites

```bash
pip install tvscreener
```

If using the local development version (includes bug fix for `FieldWithInterval`):

```bash
pip install -e .
```

### Run

```bash
# Default: BTC
python scripts/crypto_1h_technicals.py

# Specify coin
python scripts/crypto_1h_technicals.py BTC
python scripts/crypto_1h_technicals.py ETH
python scripts/crypto_1h_technicals.py SOL

# Multiple coins at once
python scripts/crypto_1h_technicals.py BTC ETH SOL

# Full ticker format also works
python scripts/crypto_1h_technicals.py BINANCE:BTCUSDT
```

### Supported Coins (built-in mapping)

BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, LINK, MATIC, SHIB, LTC, UNI, ATOM, APT, ARB, OP, SUI, NEAR, FIL, PEPE

Any other symbol will auto-resolve to `BINANCE:<SYMBOL>USDT`.

### Indicators Included

| Category | Indicators |
|----------|-----------|
| **Rating** | Technical Rating, MA Rating, Oscillators Rating |
| **Oscillators** | RSI(14/7), Stochastic K/D, Stochastic RSI Fast/Slow, MACD Level/Signal/Hist, CCI, ADX, +DI/-DI, Aroon Up/Down, Awesome Oscillator, Momentum, Williams %R, Ultimate Oscillator, Bull Bear Power, ROC |
| **Moving Averages** | EMA(10/20/50/100/200), SMA(10/20/50/100/200), Hull MA, VWMA |
| **Bollinger Bands** | Upper Band, Lower Band |
| **Keltner Channels** | Upper Band, Lower Band |
| **Donchian Channels** | Upper Band, Lower Band |
| **Volume Indicators** | VWAP, Chaikin Money Flow, Money Flow Index |
| **Ichimoku Cloud** | Base Line, Conversion Line, Leading Span A, Leading Span B |
| **Pivot Classic** | P, R1, R2, R3, S1, S2, S3 |
| **Pivot Fibonacci** | P, R1, R2, R3, S1, S2, S3 |
| **Volatility** | ATR(14), Parabolic SAR |

### Output Example

```
================================================================
  BTCUSDT  |  1H Technical Indicators
================================================================

  Price                        69,728.95
  Change %                     -0.58 %
  ...

--- Rating (1H) ---
  Technical Rating (60)                    -0.40  (Neutral)
  Moving Averages Rating (60)              -0.80  (Sell)
  Oscillators Rating (60)                  +0.00  (Neutral)

--- Pivot Points - Fibonacci (1H) ---
  Pivot Fibonacci P (60)                   69,896.79
  Pivot Fibonacci R1 (60)                  77,292.31
  Pivot Fibonacci R2 (60)                  81,861.27
  Pivot Fibonacci R3 (60)                  89,256.79
  Pivot Fibonacci S1 (60)                  62,501.27
  Pivot Fibonacci S2 (60)                  57,932.31
  Pivot Fibonacci S3 (60)                  50,536.79
  ...
```

### Customization

**Change interval** - Modify the `INTERVAL` variable in the script:

```python
INTERVAL = "5"     # 5 minutes
INTERVAL = "15"    # 15 minutes
INTERVAL = "60"    # 1 hour (default)
INTERVAL = "240"   # 4 hours
INTERVAL = "1D"    # Daily
INTERVAL = "1W"    # Weekly
```

### GitHub Actions (Scheduled Run)

```yaml
# .github/workflows/crypto-technicals.yml
name: Crypto 1H Technicals

on:
  schedule:
    - cron: '0 * * * *'  # Every hour
  workflow_dispatch:       # Manual trigger

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e .
      - run: python scripts/crypto_1h_technicals.py BTC ETH SOL
```
