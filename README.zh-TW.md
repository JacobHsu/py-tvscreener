<div align="center">
  <img src="https://raw.githubusercontent.com/deepentropy/tvscreener/main/.github/img/logo.png" alt="TradingView Screener API Logo" width="200" height="200"><br>
  <h1>TradingView™ Screener API</h1>
</div>

**[English](README.md) | 繁體中文**

-----------------

# TradingView™ Screener API：簡易的 Python 程式庫，從 TradingView™ Screener 取得資料

[![PyPI version](https://badge.fury.io/py/tvscreener.svg)](https://badge.fury.io/py/tvscreener)
[![Downloads](https://pepy.tech/badge/tvscreener)](https://pepy.tech/project/tvscreener)
[![Coverage](https://codecov.io/github/deepentropy/tvscreener/coverage.svg?branch=main)](https://codecov.io/gh/deepentropy/tvscreener)

## 🚀 試用程式碼產生器

**以視覺化方式建立篩選查詢，即時產生 Python 程式碼！**

[![Code Generator](https://img.shields.io/badge/Try%20it-Code%20Generator-2962ff?style=for-the-badge&logo=python&logoColor=white)](https://deepentropy.github.io/tvscreener/)

程式碼產生器功能：
- 選擇 6 種篩選類型（股票、加密貨幣、外匯、債券、期貨、幣種）
- 以視覺化方式建立篩選條件，涵蓋 13,000+ 欄位
- 產生可直接使用的 Python 程式碼
- 複製後即可在您的環境中執行

---

![tradingview-screener.png](https://raw.githubusercontent.com/deepentropy/tvscreener/main/.github/img/tradingview-screener.png)

取得結果為 Pandas Dataframe

![dataframe.png](https://github.com/deepentropy/tvscreener/blob/main/.github/img/dataframe.png?raw=true)

## 免責聲明

**本程式庫為非官方的第三方專案，與 TradingView™ 無任何關聯、背書或合作關係。** TradingView™ 為 TradingView™, Inc. 的商標。本獨立專案提供 Python 介面來存取 TradingView 篩選器的公開資料。使用本程式庫的風險由使用者自行承擔，並須遵守 TradingView 的服務條款。

# v0.2.0 新功能

**MCP 伺服器整合** — 本版本新增 Model Context Protocol (MCP) 支援，讓 Claude 等 AI 助手可以直接查詢市場資料。

### AI 助手專用 MCP 伺服器

```bash
# 安裝 MCP 支援
pip install tvscreener[mcp]

# 啟動 MCP 伺服器
tvscreener-mcp

# 註冊至 Claude Code
claude mcp add tvscreener -- tvscreener-mcp
```

**MCP 工具：**
- `discover_fields` — 以關鍵字搜尋 3,500+ 可用欄位
- `custom_query` — 使用任意欄位與篩選條件進行靈活查詢
- `search_stocks` / `search_crypto` / `search_forex` — 簡化版篩選器
- `get_top_movers` — 取得漲幅 / 跌幅排行

---

# v0.1.0 新功能

**重大 API 增強版本** — 本版本大幅擴充程式庫，新增篩選器、13,000+ 欄位，以及更直覺的 API。

### 新增篩選器
- **BondScreener** — 查詢政府與企業債券
- **FuturesScreener** — 查詢期貨合約
- **CoinScreener** — 查詢中心化與去中心化交易所的幣種

### 擴充欄位覆蓋範圍
- **13,000+ 欄位**，涵蓋所有篩選器類型（原先約 300 個）
- 完整的技術指標覆蓋，包含所有時間週期
- 欄位依類別組織，提供搜尋與探索方法

### 符合 Python 風格的比較語法
```python
from tvscreener import StockScreener, StockField

ss = StockScreener()
ss.where(StockField.PRICE > 50)
ss.where(StockField.VOLUME >= 1_000_000)
ss.where(StockField.MARKET_CAPITALIZATION.between(1e9, 50e9))
ss.where(StockField.SECTOR.isin(['Technology', 'Healthcare']))
df = ss.get()
```

### 流暢式 API
```python
# 鏈式呼叫讓程式碼更簡潔
ss = StockScreener()
ss.select(StockField.NAME, StockField.PRICE, StockField.CHANGE_PERCENT)
ss.where(StockField.PRICE > 100)
df = ss.get()
```

### 欄位預設組合
```python
from tvscreener import StockScreener, STOCK_VALUATION_FIELDS, STOCK_DIVIDEND_FIELDS

ss = StockScreener()
ss.specific_fields = STOCK_VALUATION_FIELDS + STOCK_DIVIDEND_FIELDS
```

### 型別安全驗證
程式庫現在會驗證您是否在每個篩選器使用正確的欄位類型，及早發現錯誤。

---

# 主要功能

- 查詢**股票**、**外匯**、**加密貨幣**、**債券**、**期貨**及**幣種**篩選器
- 所有**可用欄位**：涵蓋所有篩選器類型的 13,000+ 欄位
- **任意時間週期**（`無需註冊帳號` — 1D、5m、1h 等）
- **流暢式 API**，透過 `select()` 與 `where()` 方法讓程式碼更簡潔
- **欄位探索** — 依名稱搜尋欄位、取得技術指標、依類別篩選
- **欄位預設組合** — 針對常見使用情境的精選欄位群組
- **型別安全驗證** — 偵測欄位與篩選器的不匹配
- 依任意欄位、代號、市場、國家等條件篩選
- 以 Pandas Dataframe 格式取得結果
- **美化輸出** — 具備 TradingView 風格的顏色與格式
- **串流 / 自動更新** — 以指定間隔持續取得資料

## 安裝

原始碼目前託管於 GitHub：
https://github.com/deepentropy/tvscreener

最新版本的安裝檔可從 [Python Package Index (PyPI)](https://pypi.org/project/tvscreener) 取得

```sh
# 透過 PyPI 安裝
pip install tvscreener
```

透過 pip + GitHub 安裝：

```sh
$ pip install git+https://github.com/deepentropy/tvscreener.git
```

## 使用方式

### 基本篩選器

```python
import tvscreener as tvs

# 股票篩選器
ss = tvs.StockScreener()
df = ss.get()  # 預設回傳 150 列的 dataframe

# 外匯篩選器
fs = tvs.ForexScreener()
df = fs.get()

# 加密貨幣篩選器
cs = tvs.CryptoScreener()
df = cs.get()

# 債券篩選器（新增）
bs = tvs.BondScreener()
df = bs.get()

# 期貨篩選器（新增）
futs = tvs.FuturesScreener()
df = futs.get()

# 幣種篩選器（新增）— 中心化與去中心化交易所幣種
coins = tvs.CoinScreener()
df = coins.get()
```

### 流暢式 API

使用 `select()` 與 `where()` 讓程式碼更簡潔、可鏈式呼叫：

```python
from tvscreener import StockScreener, StockField

ss = StockScreener()
ss.select(
    StockField.NAME,
    StockField.PRICE,
    StockField.CHANGE_PERCENT,
    StockField.VOLUME,
    StockField.MARKET_CAPITALIZATION
)
ss.where(StockField.MARKET_CAPITALIZATION > 1e9)
ss.where(StockField.CHANGE_PERCENT > 5)
df = ss.get()
```

### 欄位探索

搜尋與探索 13,000+ 可用欄位：

```python
from tvscreener import StockField

# 依名稱或標籤搜尋欄位
rsi_fields = StockField.search("rsi")
print(f"找到 {len(rsi_fields)} 個 RSI 相關欄位")

# 取得所有技術指標欄位
technicals = StockField.technicals()
print(f"找到 {len(technicals)} 個技術指標欄位")

# 取得建議欄位
recommendations = StockField.recommendations()
```

### 欄位預設組合

使用精選欄位群組，滿足常見分析需求：

```python
from tvscreener import (
    StockScreener, get_preset, list_presets,
    STOCK_PRICE_FIELDS, STOCK_VALUATION_FIELDS, STOCK_DIVIDEND_FIELDS,
    STOCK_PERFORMANCE_FIELDS, STOCK_OSCILLATOR_FIELDS
)

# 查看所有可用預設組合
print(list_presets())
# ['stock_price', 'stock_volume', 'stock_valuation', 'stock_dividend', ...]

# 直接使用預設組合
ss = StockScreener()
ss.specific_fields = STOCK_VALUATION_FIELDS + STOCK_DIVIDEND_FIELDS
df = ss.get()

# 或依名稱取得預設組合
fields = get_preset('stock_performance')
```

**可用預設組合：**
| 類別 | 預設組合 |
|------|---------|
| 股票 | `stock_price`、`stock_volume`、`stock_valuation`、`stock_dividend`、`stock_profitability`、`stock_performance`、`stock_oscillators`、`stock_moving_averages`、`stock_earnings` |
| 加密貨幣 | `crypto_price`、`crypto_volume`、`crypto_performance`、`crypto_technical` |
| 外匯 | `forex_price`、`forex_performance`、`forex_technical` |
| 債券 | `bond_basic`、`bond_yield`、`bond_maturity` |
| 期貨 | `futures_price`、`futures_technical` |
| 幣種 | `coin_price`、`coin_market` |

### 技術指標的時間週期

對技術指標套用不同的時間週期：

```python
from tvscreener import StockScreener, StockField

ss = StockScreener()

# 取得 1 小時週期的 RSI
rsi_1h = StockField.RELATIVE_STRENGTH_INDEX_14.with_interval("60")

# 可用週期：1, 5, 15, 30, 60, 120, 240, 1D, 1W, 1M
ss.specific_fields = [
    StockField.NAME,
    StockField.PRICE,
    rsi_1h,
    StockField.MACD_LEVEL_12_26.with_interval("240"),  # 4 小時 MACD
]
df = ss.get()
```

## 參數

詳細的使用範例請參閱下方的文件與筆記本。

## 美化輸出

您可以使用 `beautify` 函式對篩選結果套用 TradingView 風格的格式。這會為評級與漲跌幅加上彩色文字、為數字加上 K/M/B 後綴，並為買入/賣出/中性建議加上視覺指標。

```python
import tvscreener as tvs

# 取得原始資料
ss = tvs.StockScreener()
df = ss.get()

# 套用 TradingView 樣式
styled = tvs.beautify(df, tvs.StockField)

# 在 Jupyter/IPython 中顯示（呈現彩色輸出）
styled
```

美化輸出包含：
- **評級欄位**帶有彩色文字與方向箭頭：
  - 買入訊號：藍色文字加上向上箭頭（↑）
  - 賣出訊號：紅色文字加上向下箭頭（↓）
  - 中性：灰色文字加上橫線（-）
- **漲跌幅欄位**：正值為綠色，負值為紅色
- **數字格式化**：大數字使用 K、M、B、T 後綴
- **缺失值**：顯示為「--」

## 串流 / 自動更新

您可以使用 `stream()` 方法以指定間隔持續取得篩選資料。這對於監控即時市場資料非常實用。

```python
import tvscreener as tvs

# 基本串流，設定迭代次數上限
ss = tvs.StockScreener()
for df in ss.stream(interval=10, max_iterations=5):
    print(f"取得 {len(df)} 列")

# 搭配回呼函式的串流
from datetime import datetime

def on_update(df):
    print(f"更新時間 {datetime.now()}：{len(df)} 列")

ss = tvs.StockScreener()
try:
    for df in ss.stream(interval=5, on_update=on_update):
        # 處理資料
        pass
except KeyboardInterrupt:
    print("已停止串流")

# 搭配篩選條件的串流
ss = tvs.StockScreener()
ss.set_markets(tvs.Market.AMERICA)
for df in ss.stream(interval=30, max_iterations=10):
    print(df.head())
```

**參數：**
- `interval`：重新整理間隔（秒），最小為 1.0 以避免速率限制
- `max_iterations`：最大重新整理次數（None = 無限）
- `on_update`：選用的回呼函式，每次取得 DataFrame 時呼叫

## 文件

📖 **[完整文件](https://deepentropy.github.io/tvscreener/docs/)** — 完整指南、API 參考與範例。

### 快速連結

| 指南 | 說明 |
|------|------|
| [快速入門](https://deepentropy.github.io/tvscreener/docs/getting-started/quickstart/) | 5 分鐘快速上手 |
| [篩選條件](https://deepentropy.github.io/tvscreener/docs/guide/filtering/) | 完整的篩選條件參考 |
| [股票篩選](https://deepentropy.github.io/tvscreener/docs/examples/stock-screening/) | 價值、動能、股息策略 |
| [技術分析](https://deepentropy.github.io/tvscreener/docs/examples/technical-analysis/) | RSI、MACD、多時間週期 |
| [API 參考](https://deepentropy.github.io/tvscreener/docs/api/screeners/) | 篩選器、欄位、列舉型別 |

### Jupyter 筆記本

依使用情境組織的互動式範例：

| 筆記本 | 說明 |
|--------|------|
| [01-quickstart.ipynb](docs/notebooks/01-quickstart.ipynb) | 6 種篩選器總覽 |
| [02-stocks.ipynb](docs/notebooks/02-stocks.ipynb) | 股票篩選策略 |
| [03-crypto.ipynb](docs/notebooks/03-crypto.ipynb) | 加密貨幣分析 |
| [04-forex.ipynb](docs/notebooks/04-forex.ipynb) | 外匯配對篩選 |
| [05-bonds-futures.ipynb](docs/notebooks/05-bonds-futures.ipynb) | 債券與期貨 |

---

## Telegram 通知

本專案透過 GitHub Actions 每小時自動發送 BTC/ETH 1H 技術指標通知至 Telegram。

### 訊息範例

```
🕐 2026-02-12 15:00 (台北時間)

【 🔶 BTC $67,374 +320 (+0.48%) 】

⚠️ Tech: Sell
MA: Sell Buy: (4) Sell: (8) ✘
Oscillator: Neutral Buy: (3) Sell: (2)
Fibonacci: S1 $62,501 | R1 $77,292
RSI: 48.0 | MACD: +140.4 ▲ | ADX: 26.1 (Trending)
BB: $66,172 | DC: $65,756 | ATR: 779.5 (~)
VWAP: $67,287 | MFI: 59.6
🗣️ 1H: 📉 Down 震盪偏空
🐻: MA均線空排，RSI 48偏弱，MACD柱狀收斂中，壓力R1($77,292)

📊 TradingView Screener
```

### 訊息欄位說明

#### 價格區塊

| 欄位 | 說明 |
|------|------|
| 🔶 / 🔹 | BTC / ETH 識別 |
| `$67,374` | 當前價格 |
| `+320 (+0.48%)` | 價格變動（絕對值 + 百分比） |

#### 三大評級（對應 TradingView Technicals）

| 欄位 | 來源 | 說明 |
|------|------|------|
| `Tech:` | Technical Rating | MA + Oscillator 綜合評級 |
| `MA:` | Moving Averages Rating | 12 條均線評級（EMA/SMA 10,20,50,100,200 + Hull MA + VWMA） |
| `Oscillator:` | Oscillators Rating | 11 個振盪指標評級 |

評級值：`Strong Buy` / `Buy` / `Neutral` / `Sell` / `Strong Sell`

`Buy: (n)` / `Sell: (n)` — 個別指標的多空計數，未顯示的為 Neutral

`✘` — 當 Sell 數量 > Buy 數量時出現

#### MA Buy/Sell 判定規則（12 個）

| 指標 | Buy | Sell |
|------|-----|------|
| EMA / SMA (10,20,50,100,200) | Price > MA | Price < MA |
| Hull MA (9) | Price > MA | Price < MA |
| VWMA (20) | Price > MA | Price < MA |

#### Oscillator Buy/Sell 判定規則（11 個）

| 指標 | Buy | Sell |
|------|-----|------|
| RSI (14) | < 30 | > 70 |
| Stochastic %K | < 20 | > 80 |
| CCI (20) | < -100 | > 100 |
| ADX (+DI/-DI) | +DI > -DI | +DI < -DI |
| Awesome Oscillator | > 0 | < 0 |
| Momentum (10) | > 0 | < 0 |
| MACD (Level vs Signal) | Level > Signal | Level < Signal |
| Stoch RSI Fast | < 20 | > 80 |
| Williams %R | < -80 | > -20 |
| Bull Bear Power | > 0 | < 0 |
| Ultimate Oscillator | < 30 | > 70 |

#### 支撐 / 壓力

| 欄位 | 說明 |
|------|------|
| `Fibonacci: S1 / R1` | Fibonacci Pivot 支撐1 / 壓力1，**粗體**標示較接近當前價格的一方 |

#### 動能指標

| 欄位 | 說明 |
|------|------|
| `RSI` | 相對強弱指數 (14)。< 30 超賣、> 70 超買 |
| `MACD` | MACD 柱狀圖值（Histogram = Level - Signal） |
| `▲` / `▼` | MACD 柱狀圖方向。`▲` 正值（多方動能）、`▼` 負值（空方動能） |

#### ADX 趨勢強度

| ADX 值 | 標籤 | 意義 |
|--------|------|------|
| >= 25 | `(Trending)` | 趨勢確立，適合順勢操作 |
| < 25 | `(Ranging)` | 盤整區間，適合高賣低買 |

#### 通道與波動

| 欄位 | 說明 |
|------|------|
| `BB:` | Bollinger Band Lower (20) — 布林通道下限，價格接近時為潛在支撐 |
| `DC:` | Donchian Channel Lower (20) — 唐納奇通道下限（**粗體**），20 期最低價，極端支撐 |
| `ATR:` | Average True Range (14) — 平均真實波幅，衡量每根 K 棒的平均波動範圍 |

#### ATR 波動狀態

以 ATR 佔價格百分比判斷：`ATR% = ATR / Price × 100`

| ATR% | 符號 | 意義 |
|------|------|------|
| >= 1.5% | `(~)` | 波動劇烈，行情活躍 |
| < 1.5% | `(-)` | 波動平靜，行情收斂 |

#### 成交量指標

| 欄位 | 說明 |
|------|------|
| `VWAP` | 成交量加權平均價 — 機構參考價格，價格在上方 = 多方控制，下方 = 空方控制 |
| `MFI` | 資金流量指數 — 帶成交量的 RSI。< 20 超賣、> 80 超買 |

#### AI 預測（GitHub Models API）

| 欄位 | 說明 |
|------|------|
| `🗣️ 1H:` | AI 預測方向 + 走勢類型 |
| `📈` / `📉` | 預測方向。📈 Up / 📉 Down |
| `🐂` / `🐻` | 技術分析理由。🐂 多方 / 🐻 空方 |

走勢類型：

| 類型 | 說明 |
|------|------|
| `單邊上漲` | 強勢多頭，大部分指標偏多 |
| `震盪偏多` | 震盪格局但偏多方 |
| `震盪偏空` | 震盪格局但偏空方 |
| `單邊下跌` | 強勢空頭，大部分指標偏空 |

### 設定方式

1. 在 GitHub repo Settings → Secrets 加入：
   - `TELEGRAM_BOT_TOKEN` — 從 @BotFather 取得
   - `TELEGRAM_CHAT_ID` — 你的聊天 ID

2. GitHub Actions 排程 `0 * * * *`（每小時整點，台灣時間每整點發送）

3. 本地測試：
   ```bash
   # 複製 .env
   cp .env.example .env
   # 填入 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID

   # 僅列印不發送
   python scripts/send_tg_notification.py --dry-run

   # 實際發送
   python scripts/send_tg_notification.py
   ```
