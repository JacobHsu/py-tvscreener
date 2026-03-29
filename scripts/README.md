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

### 1️⃣ 多單入場訊號說明

標題列出現 `1️⃣` 表示當前價格已進入 **Fibonacci S1 長多入場區間**。

#### 策略邏輯

```
入場價 = Fibonacci S1 + offset
停損價 = Fibonacci S1
止盈價 = 入場價 + 3 × offset  （盈虧比 3:1）
```

| 幣種 | Offset | 入場條件 | 止盈距離 |
|------|--------|---------|---------|
| ETH  | 30 點  | price ≥ S1 + 30  | +90 點  |
| BTC  | 300 點 | price ≥ S1 + 300 | +900 點 |

#### 歷史回測結果（2026-02-10 ~ 2026-03-29，1H 資料）

| 幣種 | 勝率 | 每筆期望值 |
|------|------|----------|
| ETH  | **91.3%** | +2.65R |
| BTC  | **89.9%** | +2.60R |

損益平衡勝率（3:1 盈虧比）= 25%，兩者均大幅超越門檻。

#### Tech 訊號分布（ETH，276 筆）

| Tech 訊號 | 止盈 | 停損 | 勝率 |
|---------|-----|-----|-----|
| Buy | 87 | 2 | **97.8%** |
| Strong Buy | 24 | 2 | 92.3% |
| Neutral | 40 | 5 | 88.9% |
| Strong Sell | 16 | 2 | 88.9% |
| **Sell** | **85** | **13** | **86.7%** |

> **Sell 佔最多（98 筆，36%）**，且勝率仍達 86.7%。Tech 訊號與策略方向無關，Sell 時照樣能止盈。Tech 訊號僅供參考，不應作為是否開倉的過濾條件。

#### Tech 訊號分布（BTC，336 筆）

| Tech 訊號 | 止盈 | 停損 | 勝率 |
|---------|-----|-----|-----|
| Strong Buy | 23 | 1 | **95.8%** |
| Neutral | 46 | 3 | 93.9% |
| Buy | 110 | 8 | 93.2% |
| **Sell** | **107** | **19** | **84.9%** |
| Strong Sell | 16 | 3 | 84.2% |

> BTC 同樣以 Sell 佔比最高（126 筆，37.5%），規律與 ETH 一致。

#### RSI 區間勝率

| RSI 區間 | ETH 勝率 | BTC 勝率 |
|---------|---------|---------|
| 60–70 | **100%** | 95.9% |
| 40–60 | ~95% | 91–96% |
| > 70 | 84% | 81% |
| 30–40 | 82.6% | 84.3% |
| < 30 | 76.2% | **71.4%** ← 最差 |

RSI 在 40–70 之間是最佳開倉區間。RSI < 30 雖仍正期望值，但勝率明顯下降，需謹慎。

#### 最高風險組合（停損集中於此）

```
Sell 訊號 + RSI < 35 + 價格在 EMA50 下方
```

ETH/BTC 的停損案例幾乎都發生在此組合，建議此時觀望而非開倉。

> **注意**：`1️⃣` 僅表示價格已達入場區間，不代表自動開倉。開倉前以 RSI 40–70、EMA50 上方為優先，Tech 訊號作參考而非過濾條件。

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
