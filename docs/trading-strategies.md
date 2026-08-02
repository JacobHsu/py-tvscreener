# 交易策略說明（Trading Strategies）

> 本文說明本專案 Telegram 通知背後**實際運行的交易策略**：進出場規則、風險控制與回測實績。
> 策略如何被驗證（資料收集、回測機制、緩衝校準）請見 [復盤機制](review-mechanism.md)。

> ⚠️ **免責聲明**：以下內容為技術指標的歷史統計，非投資建議。加密貨幣與期貨波動極大，過去績效不代表未來結果，請自負盈虧。

---

## 策略總覽

| 策略 | 用途 | 適用標的 | 回測勝率 |
|------|------|---------|:---:|
| **DC(S) 停損支撐** | 動態停損 / 承接參考 | 加密、金屬 | 盤中守住 90-98% |
| **Fibonacci S1 多單入場（1️⃣）** | 長多進場 | BTC / ETH | ~90% |
| **Squeeze 蓄力突破** | 突破預警 | 全部 | 方向預警 |

---

## 1. DC(S) 停損支撐

停損導向的動態支撐線：

```
DC(S) = Donchian Lower(20) × 緩衝倍數
```

緩衝倍數**依資產波動度分開校準**（不是單一固定值）：

| 資產 | 緩衝倍數 | 依據 |
|------|:---:|------|
| 加密（1H / 4H BTC/ETH） | **× 0.97（−3%）** | 停損級 ≥90% 盤中守住須覆蓋較波動的 ETH |
| 金屬（GOLD / SILVER） | **× 0.98（−2%）** | 波動低，原始 DC Lower 盤中已守住 92-93% |

### 6 個月全樣本回測（Close 守住率 / **盤中守住率**）

| 路徑 | ×1.00 | ×0.98 | ×0.97 |
|------|-------|-------|-------|
| 1H BTC | 80/54 | 94/91 | 97/95 |
| 1H ETH | 81/56 | 90/**85** | 95/**90** |
| 4H BTC | 88/80 | 95/93 | 98/97 |
| 4H ETH | 90/80 | 96/91 | 97/96 |
| 金屬 GOLD | 95/92 | 98/98 | 99/98 |
| 金屬 SILVER | 95/93 | 97/97 | 98/97 |

**為什麼加密與金屬用不同倍數？**
加密改 0.97 是為了讓同一常數同時覆蓋 BTC 與 ETH 的停損級（ETH 在 0.98 盤中只有 85%）；金屬維持 0.98，因為金屬原始 DC Lower 盤中就守住 92-93%，再深的緩衝只會讓支撐離現價太遠而失去實用價值。

> 校準方法與可重跑的回測腳本見 [復盤機制 — 統計回測層](review-mechanism.md)。

---

## 2. Fibonacci S1 多單入場（1️⃣）

當通知標題出現 `1️⃣`，表示當前價格已進入 **Fibonacci S1 長多入場區間**。

### 策略邏輯

```
入場價 = Fibonacci S1 + offset
停損價 = Fibonacci S1
止盈價 = 入場價 + 3 × offset   （盈虧比 3:1）
```

| 幣種 | Offset | 入場條件 | 止盈距離 |
|------|--------|---------|---------|
| ETH | 30 點 | price ≥ S1 + 30 | +90 點 |
| BTC | 300 點 | price ≥ S1 + 300 | +900 點 |

### 回測結果（2026-02-10 ~ 03-29，1H 資料）

| 幣種 | 勝率 | 每筆期望值 |
|------|------|-----------|
| ETH | **91.3%** | +2.65R |
| BTC | **89.9%** | +2.60R |

> 3:1 盈虧比的損益平衡勝率為 25%，兩者均大幅超越門檻。

### 開倉優先條件（回測洞察）

- ✅ **RSI 40–70** 為最佳開倉區間（勝率最高）。
- ⚠️ RSI < 30 雖仍正期望值，但勝率明顯下降，需謹慎。
- 🔴 **最高風險組合**：`Sell 訊號 + RSI < 35 + 價格在 EMA50 下方` —— 停損案例幾乎都集中於此，建議觀望而非開倉。
- ℹ️ Tech 訊號與策略方向無關（Sell 時照樣能止盈），**僅供參考，不應作為開倉過濾條件**。

> **注意**：`1️⃣` 僅表示價格已達入場區間，**不代表自動開倉**。完整 Tech / RSI 分區勝率表見 [`scripts/README.md`](https://github.com/deepentropy/tvscreener/blob/main/scripts/README.md)。

---

## 3. Squeeze 蓄力突破

偵測波動度極度壓縮、行情蓄力、即將出現方向性突破的狀態。

```
Squeeze ON = (BB Upper < KC Upper) 且 (BB Lower > KC Lower)
```

當 Bollinger Bands 完全收縮進入 Keltner Channels 內側，代表波動度極低。通知中會將 BB 與 KC 數值**同時以粗體**顯示。

- **意義**：Squeeze ON 是「暴風雨前的寧靜」，突破方向需搭配其他動能指標（MACD、ADX）判斷。
- **參考**：John Carter / LazyBear Squeeze Momentum。

---

## 策略如何整合進通知

以上策略的即時計算與呈現，由 `scripts/send_tg_notification.py`（1H 加密）、`send_4h_tg_notification.py`（4H 加密）、`send_metals_notification.py`（金屬）產生，每小時透過 GitHub Actions 發送至 Telegram。訊息各欄位的完整格式與粗體規則見 [`scripts/README.md`](https://github.com/deepentropy/tvscreener/blob/main/scripts/README.md)。

## 相關文件

- [復盤機制](review-mechanism.md) — 資料收集、回測機制、緩衝校準（策略如何被驗證）
- [`scripts/README.md`](https://github.com/deepentropy/tvscreener/blob/main/scripts/README.md) — 通知訊息欄位與格式細節
