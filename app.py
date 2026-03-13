import streamlit as st
import requests
import time

st.title("Vol.1〜5 イベントID特定ツール")
st.write("Vol.6のID (39733) から遡って、APIを照合します。")

# 探索設定
targets = [
    {"vol": 5, "room_id": 548165, "name": "SHOWROOM ビギナーチャレンジ vol.5"},
    {"vol": 4, "room_id": 554806, "name": "SHOWROOM ビギナーチャレンジ vol.4"},
    {"vol": 3, "room_id": 554687, "name": "SHOWROOM ビギナーチャレンジ vol.3"},
    {"vol": 2, "room_id": 552276, "name": "SHOWROOM ビギナーチャレンジ vol.2"},
    {"vol": 1, "room_id": 553840, "name": "SHOWROOM ビギナーチャレンジ vol.1"},
]

if st.button("ID探索を開始"):
    found_results = []
    status_area = st.empty()
    progress_bar = st.progress(0)
    result_area = st.container()
    
    current_id = 39732
    # 探索範囲（Vol.1がさらに数千下にある可能性を考慮）
    start_range = 39732
    end_range = 34000 
    
    total_to_find = len(targets)
    
    while current_id >= end_range and len(found_results) < total_to_find:
        # 進捗表示
        percent = min(100, int((start_range - current_id) / (start_range - end_range) * 100))
        progress_bar.progress(percent)
        status_area.text(f"調査中... 現在のEvent ID: {current_id}")
        
        for t in targets:
            # 既に見つかったVolはスキップ
            if any(r['vol'] == t['vol'] for r in found_results):
                continue
                
            url = f"https://www.showroom-live.com/api/event/contribution_ranking?event_id={current_id}&room_id={t['room_id']}"
            
            try:
                res = requests.get(url, timeout=3).json()
                event_data = res.get("event", {})
                actual_name = event_data.get("event_name", "")

                if t['name'] == actual_name:
                    info = {
                        "vol": t['vol'],
                        "event_id": current_id,
                        "event_name": actual_name,
                        "event_url_key": event_data.get("event_url", "").split("/")[-1],
                        "started_at": event_data.get("started_at"),
                        "ended_at": event_data.get("ended_at")
                    }
                    found_results.append(info)
                    st.success(f"✅ Vol.{t['vol']} 発見！ ID: {current_id}")
            except:
                pass
        
        current_id -= 1
        # 負荷対策
        if current_id % 5 == 0:
            time.sleep(0.01)

    st.divider()
    st.write("### 探索完了！ CSV追加用データ")
    if found_results:
        # Vol順にソート
        found_results.sort(key=lambda x: x['vol'])
        csv_lines = []
        for r in found_results:
            line = f"{r['event_id']},{r['event_name']},{r['event_url_key']},{r['started_at']},{r['ended_at']}"
            csv_lines.append(line)
        
        st.code("\n".join(csv_lines), language="text")
        st.write("上記の行をコピーして、sr-event-archive.csv の末尾に貼り付けてください。")
    else:
        st.error("指定範囲内でIDが見つかりませんでした。範囲を広げる必要があります。")