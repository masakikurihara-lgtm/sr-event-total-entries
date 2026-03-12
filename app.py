import pandas as pd
import requests
import time

# 1. CSVの読み込み（パスは実際の場所に合わせて変更してください）
# event_id列が含まれていることを前提としています
csv_url = "https://mksoul-pro.com/showroom/file/sr-event-archive.csv"
df = pd.read_csv(csv_url)

# 「ビギナーチャレンジ」を含むイベントのみ抽出
target_events = df[df['event_name'].str.contains("ビギナーチャレンジ", na=False)].copy()

# 結果を格納するリスト
results = []

print("データ取得を開始します...")

for index, row in target_events.iterrows():
    event_id = row['event_id']
    event_name = row['event_name']
    
    # SHOWROOM API URL
    api_url = f"https://www.showroom-live.com/api/event/room_list?event_id={event_id}&p=1"
    
    try:
        response = requests.get(api_url)
        data = response.json()
        
        # total_entriesを取得
        count = data.get("total_entries", 0)
        results.append({
            "vol": event_name.replace("SHOWROOM ビギナーチャレンジ ", ""),
            "event_id": event_id,
            "count": count
        })
        print(f"取得済み: {event_name} -> {count}ルーム")
        
    except Exception as e:
        print(f"エラー（ID:{event_id}）: {e}")
    
    # サーバー負荷軽減のためわずかに待機
    time.sleep(0.5)

# 2. 結果をデータフレームにして表示
result_df = pd.DataFrame(results)

# volの数値順にソート（文字列なので数値変換してソート）
result_df['vol_num'] = result_df['vol'].str.extract('(\21+)').astype(int)
result_df = result_df.sort_values('vol_num')

print("\n--- 最終集計結果 ---")
print(result_df[['vol', 'event_id', 'count']].to_string(index=False))

# 必要であればCSV保存
# result_df.to_csv("beginner_challenge_stats.csv", index=False, encoding="utf-8-sig")