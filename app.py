import streamlit as st
import pandas as pd
import requests
import time

st.title("SHOWROOM ビギナーチャレンジ統計")

# 1. CSVの読み込み
csv_url = "https://mksoul-pro.com/showroom/file/sr-event-archive.csv"

@st.cache_data
def load_and_filter_data(url):
    df = pd.read_csv(url)
    # 「ビギナーチャレンジ」を含むイベントのみ抽出
    return df[df['event_name'].str.contains("ビギナーチャレンジ", na=False)].copy()

df_filtered = load_and_filter_data(csv_url)

if st.button('データ取得開始'):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(df_filtered)
    
    for i, (index, row) in enumerate(df_filtered.iterrows()):
        event_id = row['event_id']
        event_name = row['event_name']
        
        status_text.text(f"取得中: {event_name}...")
        
        api_url = f"https://www.showroom-live.com/api/event/room_list?event_id={event_id}&p=1"
        
        try:
            response = requests.get(api_url, timeout=10)
            data = response.json()
            count = data.get("total_entries", 0)
            
            results.append({
                "vol": event_name.replace("SHOWROOM ビギナーチャレンジ ", ""),
                "event_id": event_id,
                "count": count
            })
        except Exception as e:
            st.error(f"エラー（ID:{event_id}）: {e}")
        
        # 進捗更新
        progress_bar.progress((i + 1) / total)
        time.sleep(0.1) # サーバー負荷軽減

    # 結果の処理
    result_df = pd.DataFrame(results)
    
    # 修正ポイント: 正規表現を (\d+) にし、エラー回避のために errors='coerce' を指定
    result_df['vol_num'] = result_df['vol'].str.extract('(\d+)').astype(float)
    result_df = result_df.dropna(subset=['vol_num']).sort_values('vol_num')
    result_df['vol_num'] = result_df['vol_num'].astype(int)

    status_text.text("取得完了！")
    
    # テーブル表示
    st.write("### 集計結果")
    st.dataframe(result_df[['vol', 'event_id', 'count']], use_container_width=True)
    
    # 折れ線グラフ表示
    st.write("### 参加ルーム数推移")
    st.line_chart(data=result_df, x='vol', y='count')

    # CSVダウンロードボタン
    csv = result_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("結果をCSVでダウンロード", csv, "beginner_challenge_stats.csv", "text/csv")