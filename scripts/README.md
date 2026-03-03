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
| **Volume Indicators** | VWAP, VWMA(20), Chaikin Money Flow, Money Flow Index |
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

---

## send_tg_notification.py

讀取 SQLite 歷史資料，呼叫 GitHub Models API（GPT-4.1）產生 AI 預測，格式化後透過 Telegram Bot 傳送通知。

### 訊息格式說明

| 欄位 | 說明 |
|------|------|
| `Tech` | TradingView 綜合技術評級 |
| `MA: 🔥 Strong Buy ×NH` | MA 評級 + 連續持續小時數（Strong Buy/Sell 顯示 🔥） |
| `Oscillator` | 震盪指標評級 + 個別 Buy/Sell 計數 |
| `RSI \| MACD \| DC(S)` | RSI(14)、MACD Histogram、DC(S) 支撐位 |
| `Band- BB \| KC \| ATR` | Bollinger Lower、Keltner Lower、ATR(14)（波動度通道帶） |
| `Trend- ADX \| Aroon` | 趨勢強度與方向 |
| `Volume- VWAP \| VWMA` | 成交量加權均價指標 |
| `Money- CMF \| MFI` | 資金流向指標 |

### 粗體規則

| 欄位 | 粗體條件 |
|------|---------|
| RSI | RSI < 30 或 > 70（極端值） |
| MA 評級 | 永遠粗體（含持續時數） |
| ADX / Aroon | ADX 與 Aroon 方向一致（同向確認）或 ADX > 50 |
| VWAP / VWMA | 兩者方向一致（同時高於或低於價格） |
| CMF / MFI | 兩者方向一致 或 MFI < 20 / > 80 |
| ATR | ATR / Price ≥ 1.5%（高波動） |
| **BB / KC** | **Squeeze ON：BB 完全在 KC 內側時同時粗體**（壓縮蓄力中） |
| DC(S) | 固定顯示，為 DC Lower × 0.98（−2% 支撐位） |

### Squeeze 說明

**Squeeze ON** = `BB Upper < KC Upper` 且 `BB Lower > KC Lower`

Bollinger Bands 收縮進入 Keltner Channels 內側，代表波動度極低、行情蓄力，即將出現方向性突破。觸發時 BB 與 KC 數值同時以粗體顯示。參考：John Carter / LazyBear Squeeze Momentum。

### DC(S) 支撐位說明

`DC(S) = Donchian Lower(20) × 0.98`

根據歷史回測（21 天）：
- **DC Lower** 守住率 52%（BTC）/ 62%（ETH）
- **DC(S) −2%** 守住率 **81%**（BTC/ETH 相同），且跌破時均為趨勢性下跌而非假跌破

---

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
