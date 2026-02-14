import sqlite3
import pandas as pd
from datetime import timedelta, datetime
import os
import sys

# ============================================================
# Configuration
# ============================================================
# Connect to the local database relative to this script
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'history.db')

# Timezone settings: UTC database time to Taiwan Local Time
TIMEZONE_OFFSET = 8  # Hours

# Strategy settings
STRATEGY_NAME = "DC Lower Support Validation (Close)"
SYMBOLS = ['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT']
START_HOUR_TW = 16  # 4 PM Taiwan Time
START_HOUR_UTC = (START_HOUR_TW - TIMEZONE_OFFSET) % 24  # 08:00 UTC

# ============================================================
# Main Logic
# ============================================================
def run_backtest():
    """
    Backtest Logic:
    1. Session N starts at Day N 16:00 TW (08:00 UTC).
    2. We record the 'Donchian Channel Lower Band' at the START of the session.
    3. We check the 'Close Price' at the END of the session (Day N+1 16:00 TW).
    4. Condition: If (Close Price >= Start DC Lower), the support HELD (PASS).
                  If (Close Price < Start DC Lower), the support FAILED (FAIL).
    """
    
    # 1. Check database
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    print(f"Loading data from: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    # 2. Query Data
    placeholders = ','.join('?' for _ in SYMBOLS)
    query = f"""
    SELECT collected_at, symbol, price, donchian_lower 
    FROM technical_indicators 
    WHERE symbol IN ({placeholders})
    ORDER BY collected_at ASC
    """
    
    try:
        df = pd.read_sql_query(query, conn, params=SYMBOLS)
    except Exception as e:
        print(f"Database Error: {e}")
        return
    finally:
        conn.close()

    if df.empty:
        print("No data found.")
        return

    # 3. Preprocess Data
    # Convert 'collected_at' to datetime
    df['collected_at'] = pd.to_datetime(df['collected_at'])
    
    # Convert to Taiwan Time for easier reading/logic
    df['tw_time'] = df['collected_at'] + timedelta(hours=TIMEZONE_OFFSET)

    final_results = []
    
    print("\n" + "="*80)
    print(f"RUNNING BACKTEST: {STRATEGY_NAME}")
    print(f"Rule: IF (Close Price at Next Day 16:00 TW) >= (DC Lower at Start Day 16:00 TW) -> PASS")
    print("="*80 + "\n")

    for symbol in SYMBOLS:
        symbol_df = df[df['symbol'] == symbol].sort_values('tw_time')
        
        # Filter for rows that match the session start time (16:00 TW)
        # Note: We rely on the collected data being exactly on the hour.
        session_points = symbol_df[symbol_df['tw_time'].dt.hour == START_HOUR_TW].copy()
        
        if session_points.empty:
            print(f"No valid session start points (16:00 TW) found for {symbol}")
            continue

        points = session_points.to_dict('records')
        
        # Analyze completed sessions (Start -> Next Start)
        for i in range(len(points) - 1):
            start_rec = points[i]
            end_rec = points[i+1]
            
            start_time = start_rec['tw_time']
            end_time = end_rec['tw_time']
            
            # Verify consecutiveness (must be exactly 24 hours apart)
            if (end_time - start_time) != timedelta(hours=24):
                # Gap in data, skip
                continue
                
            dc_lower_start = start_rec['donchian_lower']
            final_price = end_rec['price']
            
            # The Logic
            is_fail = final_price < dc_lower_start
            diff = final_price - dc_lower_start
            pct = (diff / dc_lower_start) * 100
            
            status = "🔴 FAIL" if is_fail else "🟢 PASS"
            
            final_results.append({
                "Symbol": symbol,
                "Session Start (TW)": start_time.strftime('%Y-%m-%d %H:%M'),
                "Session End (TW)": end_time.strftime('%Y-%m-%d %H:%M'),
                "Support (Start)": dc_lower_start,
                "Close (End)": final_price,
                "Result": status,
                "Buffer/Diff": diff,
                "Buffer %": pct
            })

        # Analyze Current Open Session (Start -> Now)
        # Only if the latest data is after the last full session start
        last_start_rec = points[-1]
        last_start_time = last_start_rec['tw_time']
        current_rec = symbol_df.iloc[-1]
        current_time = current_rec['tw_time']
        
        # Check if we are still within the 24h window of the last start
        # And make sure we haven't already processed this as a full session above
        # (Though logic above relies on next 16:00 existing, so this covers the 'incomplete' one)
        if current_time < (last_start_time + timedelta(hours=24)) and current_time > last_start_time:
             dc_lower_start = last_start_rec['donchian_lower']
             current_price = current_rec['price']
             
             is_fail = current_price < dc_lower_start
             diff = current_price - dc_lower_start
             pct = (diff / dc_lower_start) * 100
             
             status = "🔴 FAIL (Prov)" if is_fail else "🟢 PASS (Prov)"
             
             final_results.append({
                "Symbol": symbol,
                "Session Start (TW)": last_start_time.strftime('%Y-%m-%d %H:%M'),
                "Session End (TW)": "IN PROGRESS",
                "Support (Start)": dc_lower_start,
                "Close (End)": current_price,
                "Result": status,
                "Buffer/Diff": diff,
                "Buffer %": pct
            })

    # 4. Display Results
    if not final_results:
        print("No sessions analyzed.")
        return

    res_df = pd.DataFrame(final_results)
    
    # Reorder columns
    cols = ["Symbol", "Session Start (TW)", "Session End (TW)", "Support (Start)", "Close (End)", "Result", "Buffer %"]
    
    # Format for display
    print(res_df[cols].to_string(index=False, formatters={
        "Support (Start)": lambda x: f"{x:,.2f}",
        "Close (End)": lambda x: f"{x:,.2f}",
        "Buffer %": lambda x: f"{x:+.2f}%"
    }))

    # Summary Stats (Excluding In Progress)
    completed = res_df[res_df['Session End (TW)'] != 'IN PROGRESS']
    if not completed.empty:
        pass_count = len(completed[completed['Result'] == '🟢 PASS'])
        total = len(completed)
        win_rate = (pass_count / total) * 100
        print("\n" + "-"*40)
        print(f"Summary (Completed Sessions Only):")
        print(f"Total Sessions: {total}")
        print(f"Passed: {pass_count}")
        print(f"Failed: {total - pass_count}")
        print(f"Win Rate: {win_rate:.1f}%")
        print("-"*40)

if __name__ == "__main__":
    run_backtest()
