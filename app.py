import streamlit as st
import pandas as pd
import requests
import time

st.title("SHOWROOM ビギナーチャレンジ属性分析")

# 各種ソースURL
EVENT_CSV_URL = "https://mksoul-pro.com/showroom/file/sr-event-archive.csv"
ORG_CSV_URL = "https://mksoul-pro.com/showroom/file/organizer_list.csv"

@st.cache_data
def load_master_data():
    events = pd.read_csv(EVENT_CSV_URL)
    orgs = pd.read_csv(ORG_CSV_URL)
    # ビギナーチャレンジのみ抽出
    events = events[events['event_name'].str.contains("ビギナーチャレンジ", na=False)].copy()
    return events, orgs

events_df, org_df = load_master_data()
org_map = dict(zip(org_df.iloc[:, 0].astype(str), org_df.iloc[:, 1]))

if st.button('属性分析を開始'):
    all_summary = []
    
    for _, row in events_df.iterrows():
        eid = row['event_id']
        ename = row['event_name']
        api_url = f"https://www.showroom-live.com/api/event/room_list?event_id={eid}&p=1"
        
        try:
            res = requests.get(api_url, timeout=10).json()
            rooms = res.get("list", [])
            total_entries = res.get("total_entries", 0)
            
            if not rooms: continue

            # 全体の公式・フリー集計
            official_count = sum(1 for r in rooms if r.get("is_official") == 1)
            free_count = total_entries - official_count # 1ページ目以外も考慮した概算

            # 上位10名の分析
            top_10 = []
            for r in rooms[:10]:
                oid = str(r.get("organizer_id"))
                top_10.append({
                    "rank": r.get("rank"),
                    "name": r.get("room_name"),
                    "point": r.get("point"),
                    "org": org_map.get(oid, f"不明({oid})") if r.get("is_official") else "フリー"
                })
            
            all_summary.append({
                "vol": ename.replace("SHOWROOM ビギナーチャレンジ ", ""),
                "total": total_entries,
                "official": official_count,
                "free": free_count,
                "top_10_details": top_10
            })
            
        except Exception as e:
            st.warning(f"ID:{eid} 取得失敗")
        
        time.sleep(0.2)

    # 画面表示
    for data in reversed(all_summary): # 直近から表示
        with st.expander(f"{data['vol']} (全{data['total']}ルーム)"):
            col1, col2 = st.columns(2)
            col1.metric("公式", data['official'])
            col2.metric("フリー", data['free'])
            
            st.write("### 上位10ルーム内訳")
            st.table(pd.DataFrame(data['top_10_details']))