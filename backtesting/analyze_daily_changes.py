import sqlite3
import pandas as pd
from datetime import timedelta
import os

# ============================================================
# Configuration
# ============================================================
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'history.db')
TIMEZONE_OFFSET = 8  # Hours
START_HOUR_TW = 16  # 4 PM Taiwan Time
SYMBOLS = ['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT']

# ============================================================
# Main Logic
# ============================================================
def run_analysis():
    """
    Analyze daily price changes from 16:00 TW to 16:00 TW next day.
    Calculate:
    1. Price difference (Close_End - Close_Start)
    2. Percentage change
    3. Separate statistics for Up days vs Down days
    """
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    print(f"Loading data from: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT collected_at, symbol, price
    FROM technical_indicators 
    WHERE symbol IN ('BINANCE:BTCUSDT', 'BINANCE:ETHUSDT')
    ORDER BY collected_at ASC
    """
    
    try:
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"Database Error: {e}")
        return
    finally:
        conn.close()

    if df.empty:
        print("No data found.")
        return

    # Convert to datetime and TW time
    df['collected_at'] = pd.to_datetime(df['collected_at'])
    df['tw_time'] = df['collected_at'] + timedelta(hours=TIMEZONE_OFFSET)

    print("\n" + "="*80)
    print("DAILY PRICE CHANGE ANALYSIS (16:00 TW to 16:00 TW)")
    print("="*80 + "\n")

    for symbol in SYMBOLS:
        symbol_df = df[df['symbol'] == symbol].sort_values('tw_time')
        
        # Filter for 16:00 TW session points
        session_points = symbol_df[symbol_df['tw_time'].dt.hour == START_HOUR_TW].copy()
        
        if session_points.empty:
            print(f"No valid session start points (16:00 TW) found for {symbol}")
            continue

        points = session_points.to_dict('records')
        
        up_days = []
        down_days = []
        
        # Analyze completed sessions
        for i in range(len(points) - 1):
            start_rec = points[i]
            end_rec = points[i+1]
            
            start_time = start_rec['tw_time']
            end_time = end_rec['tw_time']
            
            # Verify consecutiveness
            if (end_time - start_time) != timedelta(hours=24):
                continue
                
            start_price = start_rec['price']
            end_price = end_rec['price']
            
            # Calculate changes
            price_diff = end_price - start_price
            pct_change = (price_diff / start_price) * 100
            
            session_data = {
                'date': start_time.strftime('%Y-%m-%d'),
                'start_price': start_price,
                'end_price': end_price,
                'price_diff': price_diff,
                'pct_change': pct_change
            }
            
            if price_diff >= 0:
                up_days.append(session_data)
            else:
                down_days.append(session_data)

        # Display Results
        print(f"\n{'='*40} {symbol} {'='*40}")
        
        total_days = len(up_days) + len(down_days)
        print(f"\nTotal Sessions: {total_days}")
        print(f"Up Days: {len(up_days)} ({len(up_days)/total_days*100:.1f}%)")
        print(f"Down Days: {len(down_days)} ({len(down_days)/total_days*100:.1f}%)")
        
        # Up Days Statistics
        if up_days:
            up_df = pd.DataFrame(up_days)
            avg_up_diff = up_df['price_diff'].mean()
            avg_up_pct = up_df['pct_change'].mean()
            
            print(f"\n--- UP DAYS ---")
            print(f"Average Price Gain: {avg_up_diff:+,.2f}")
            print(f"Average % Gain: {avg_up_pct:+.2f}%")
            print(f"\nDetails:")
            for day in up_days:
                print(f"  {day['date']}: {day['start_price']:,.2f} → {day['end_price']:,.2f} "
                      f"({day['price_diff']:+,.2f} / {day['pct_change']:+.2f}%)")
        
        # Down Days Statistics
        if down_days:
            down_df = pd.DataFrame(down_days)
            avg_down_diff = down_df['price_diff'].mean()
            avg_down_pct = down_df['pct_change'].mean()
            
            print(f"\n--- DOWN DAYS ---")
            print(f"Average Price Loss: {avg_down_diff:,.2f}")
            print(f"Average % Loss: {avg_down_pct:.2f}%")
            print(f"\nDetails:")
            for day in down_days:
                print(f"  {day['date']}: {day['start_price']:,.2f} → {day['end_price']:,.2f} "
                      f"({day['price_diff']:,.2f} / {day['pct_change']:.2f}%)")
        
        # Overall Statistics
        if total_days > 0:
            all_days = up_days + down_days
            all_df = pd.DataFrame(all_days)
            overall_avg_diff = all_df['price_diff'].mean()
            overall_avg_pct = all_df['pct_change'].mean()
            
            print(f"\n--- OVERALL ---")
            print(f"Average Daily Change: {overall_avg_diff:+,.2f}")
            print(f"Average Daily % Change: {overall_avg_pct:+.2f}%")

if __name__ == "__main__":
    run_analysis()
