# 復盤機制（Review / Backtest Mechanism）

> 本專案在 `tvscreener` 函式庫之上，額外建立了一套加密貨幣（BTC/ETH）與貴金屬（黃金/白銀）的
> **每小時技術指標復盤系統**。本文說明整套機制如何運作（HOW），以及各腳本與資料如何串接。
>
> 實際運行的交易策略（WHAT — 進出場規則、勝率）請見 [交易策略說明](trading-strategies.md)。

---

## 一句話總結

**每小時把 TradingView 的 1H 技術指標快照進「版控化的 SQLite」，累積成長期歷史；再用圖表做視覺復盤、用歷史資料跑統計回測驗證策略勝率，最後把驗證過的規則回饋到 Telegram 即時通知。**

它的關鍵在於：**資料庫本身被 commit 進 Git**，所以每一小時的市場狀態都有不可竄改的版本歷史，任何策略都能拿同一份資料重現回測。

---

## 資料流總覽

```
TradingView (1H 技術指標)
        │  每小時抓取
        ▼
collect_to_db.py ──► data/history.db (SQLite，累積長期歷史)
        │                    │
   GitHub Actions       ┌────┴──────────────────┐
   每小時 commit 回 repo  ▼                       ▼
                  chart_rating_signals.py   send_tg_notification.py
                  (視覺復盤)                 (即時訊號 + AI 預測 → Telegram)
                        │
                  README 的統計回測結論
                  (勝率 / 守住率 / 期望值)
```

---

## 1. 資料收集層 — 累積「可復盤的歷史」

核心腳本：`scripts/collect_to_db.py`

- 每次抓取 BTC/ETH 的 **1H 全套技術指標**（評級、震盪指標、均線、通道、Pivot、K 線型態…共約 100 欄），寫入 `data/history.db` 的 `technical_indicators` 表。
- 時間戳 `collected_at` 對齊整點（`datetime.now(timezone.utc).replace(minute=0, second=0, ...)`）。
- 以 `UNIQUE INDEX (symbol, collected_at)` + `INSERT OR IGNORE` 保證 **同一小時只存一筆、可重跑不重複** —— 這是復盤資料乾淨的關鍵。
- 由 **GitHub Actions 每小時排程**執行（`.github/workflows/collect-crypto-data.yml`、`collect-crypto-4h-data.yml`、`collect-metals-data.yml`），並把更新後的 DB **commit 回 repo**（git log 中的 `data: hourly crypto snapshot` 即為此）。

> 結果：資料庫持續累積逐時歷史，涵蓋 BTC、ETH、黃金(COMEX:GC1!)、白銀(COMEX:SI1!)。這份逐時歷史就是所有「復盤」的原料。

### 資料表結構重點

| 欄位群 | 說明 |
|--------|------|
| `collected_at`, `symbol` | 主鍵組合（UNIQUE），整點時間 + 標的 |
| `price / open / high / low / volume` | 基本行情 |
| `technical_rating` + `technical_rating_signal` | 綜合評級「數值 + 可讀訊號」 |
| `ma_rating` / `oscillators_rating`（同上，各含 signal） | 均線 / 震盪評級 |
| 各類指標欄（RSI、MACD、ADX、BB、KC、DC、Ichimoku、Pivot、ATR…） | 供回測與通知使用 |
| `candle_*` | K 線型態旗標（0/1） |

## 2. 訊號衍生層 — 把數值轉成可讀訊號

`collect_to_db.py` 的 `rating_signal()` 在**寫入當下**就把 TradingView 的 −1~+1 數值評級轉成文字訊號，一併存進 DB：

| 數值區間 | 訊號 |
|---------|------|
| `>= 0.5` | Strong Buy |
| `>= 0.1` | Buy |
| `> -0.1` | Neutral |
| `> -0.5` | Sell |
| 其餘 | Strong Sell |

復盤時直接讀 `technical_rating_signal` 等欄位，不需重算。

## 3. 視覺復盤層 — 眼睛對照價格 vs 訊號

核心腳本：`scripts/chart_rating_signals.py`

```bash
python scripts/chart_rating_signals.py            # BTC
python scripts/chart_rating_signals.py ETHUSDT    # ETH
```

- 上方嵌入 TradingView 1H K 線 widget，下方以 Plotly 畫 **price 走勢 + 三條評級色帶**（Technical / MA / Oscillator），綠買紅賣。
- 疊加 **DC(S) 階梯支撐線**：取每日台北時間 16:00 的 Donchian Lower(20) × 緩衝倍數（加密 0.97），形成階梯狀支撐參考。
- 輸出為 HTML 並自動開啟瀏覽器。
- 用途：**視覺化檢查「當時的評級訊號有沒有跟上價格轉折」**，屬人工復盤。

## 4. 統計回測層 — 用數據驗證策略

`scripts/README.md` 記錄了對這批歷史資料跑出的**量化回測結論**，是復盤機制真正產出的「策略證據」：

### DC(S) 緩衝倍數校準（6 個月全樣本回測）

DC(S) 是停損導向支撐 `DC Lower(20) × 緩衝倍數`。緩衝倍數依資產波動度分開校準：

| 資產 | 緩衝倍數 | 依據 |
|------|:---:|------|
| 加密（1H / 4H BTC/ETH） | **× 0.97（−3%）** | 停損級 ≥90% 盤中守住須覆蓋較波動的 ETH |
| 金屬（GOLD / SILVER） | **× 0.98（−2%）** | 波動低，原始 DC Lower 盤中已守住 92-93% |

各倍數的 Close 守住率 / **盤中守住率**：

| 路徑 | ×1.00 | ×0.98 | ×0.97 |
|------|-------|-------|-------|
| 1H BTC | 80/54 | 94/91 | 97/95 |
| 1H ETH | 81/56 | 90/**85** | 95/**90** |
| 4H BTC | 88/80 | 95/93 | 98/97 |
| 4H ETH | 90/80 | 96/91 | 97/96 |
| 金屬 GOLD | 95/92 | 98/98 | 99/98 |
| 金屬 SILVER | 95/93 | 97/97 | 98/97 |

> **關鍵結論**：不能「全部改 0.97」。加密改 0.97 是為了讓同一常數同時覆蓋 BTC 與 ETH 的停損級（ETH 在 0.98 盤中只有 85%）；金屬維持 0.98，因為金屬原始 DC Lower 盤中就守住 92-93%，再深的緩衝只會讓支撐離現價太遠而失去實用價值。這說明**回測必須分資產類別，不能跨資產套用結論**。

### Fibonacci S1 多單入場策略（2026-02-10 ~ 03-29，1H 資料）

| 幣種 | 勝率 | 每筆期望值 |
|------|------|-----------|
| ETH | **91.3%** | +2.65R |
| BTC | **89.9%** | +2.60R |

> 3:1 盈虧比的損益平衡勝率為 25%，兩者均大幅超越門檻。

### 分區勝率洞察

- **RSI 40–70** 為最佳開倉區間；RSI < 30 雖仍正期望值但勝率明顯下降。
- **最高風險組合**：`Sell 訊號 + RSI < 35 + 價格在 EMA50 下方`，停損案例幾乎都集中於此，建議觀望。
- Tech 訊號與策略方向無關（Sell 時照樣能止盈），僅供參考，不應作為開倉過濾條件。

> 完整分布表（Tech 訊號 / RSI 分區）詳見 `scripts/README.md`。

## 5. 回饋層 — 復盤結論回到即時通知

核心腳本：`scripts/send_tg_notification.py`

讀取同一個 `data/history.db`，把復盤驗證過的規則轉成**即時 Telegram 訊號**，並加上 GitHub Models（GPT-4.1）的 AI 預測：

| 訊號元件 | 復盤依據 |
|---------|---------|
| MA 評級 + 連續持續小時數（🔥） | 持續性判斷 |
| Squeeze ON（BB 收進 KC 內側） | 波動壓縮蓄力，即將方向性突破 |
| DC(S) 支撐位 | 加密 ×0.97 / 金屬 ×0.98，6 個月回測校準 |
| `1️⃣` 多單入場提示 | Fibonacci S1 策略（勝率 ~90%） |

> 訊息格式與粗體規則詳見 `scripts/README.md`。

---

## 為什麼這樣設計？

1. **版控化資料庫**：DB 被 commit 進 Git，每小時市場狀態都有不可竄改的歷史，任何策略都能拿**同一份資料**重現回測，避免「事後選資料」偏誤。
2. **收集即衍生訊號**：評級文字在寫入時就算好，復盤與通知讀取一致，不會因重算邏輯差異產生偏移。
3. **冪等收集**：UNIQUE + `INSERT OR IGNORE` 讓排程可安全重跑、補跑，資料不重複。
4. **一份資料多種用途**：同一個 DB 同時支撐「視覺復盤」「統計回測」「即時通知」三條下游。

## 相關檔案

| 檔案 | 角色 |
|------|------|
| `scripts/collect_to_db.py` | 每小時收集 → 寫入 SQLite |
| `scripts/crypto_1h_technicals.py` | 單次查詢/列印 1H 指標（收集欄位的來源參考） |
| `scripts/chart_rating_signals.py` | 視覺復盤圖表 |
| `scripts/send_tg_notification.py` | 即時 Telegram 通知 + AI 預測 |
| `scripts/README.md` | 訊號格式與回測結論的完整說明 |
| `data/history.db` | 累積的逐時歷史資料庫 |
| `.github/workflows/collect-*.yml` | 每小時排程與自動 commit |
