import streamlit as st
import pandas as pd
import requests
import time

st.title("SHOWROOM ビギナーチャレンジ属性分析（全件精査版）")

EVENT_CSV_URL = "https://mksoul-pro.com/showroom/file/sr-event-archive.csv"
ORG_CSV_URL = "https://mksoul-pro.com/showroom/file/organizer_list.csv"

@st.cache_data
def load_master_data():
    events = pd.read_csv(EVENT_CSV_URL)
    orgs = pd.read_csv(ORG_CSV_URL)
    events = events[events['event_name'].str.contains("ビギナーチャレンジ", na=False)].copy()
    return events, orgs

events_df, org_df = load_master_data()
org_map = dict(zip(org_df.iloc[:, 0].astype(str), org_df.iloc[:, 1]))

if st.button('全件属性分析を開始'):
    all_summary = []
    
    # 直近のイベントから順に処理
    for _, row in events_df.sort_values('event_id', ascending=False).iterrows():
        eid = row['event_id']
        ename = row['event_name']
        
        all_rooms = []
        page = 1
        
        # --- 全ページループして全ルーム情報を取得 ---
        with st.spinner(f'{ename} の全データを取得中...'):
            while True:
                api_url = f"https://www.showroom-live.com/api/event/room_list?event_id={eid}&p={page}"
                res = requests.get(api_url, timeout=10).json()
                rooms = res.get("list", [])
                
                if not rooms:
                    break
                
                all_rooms.extend(rooms)
                
                if res.get("next_page") is None:
                    break
                page += 1
                time.sleep(0.1) # サーバー負荷軽減
        
        if not all_rooms: continue

        # --- 全件ベースで集計 ---
        total_count = len(all_rooms)
        official_count = sum(1 for r in all_rooms if r.get("is_official") == 1)
        free_count = total_count - official_count

        # 上位10名の分析
        top_10 = []
        for r in all_rooms[:10]:
            oid = str(r.get("organizer_id"))
            top_10.append({
                "順位": r.get("rank"),
                "ルーム名": r.get("room_name"),
                "ポイント": f"{r.get('point'):,}",
                "区分": "公式" if r.get("is_official") == 1 else "フリー",
                "所属先": org_map.get(oid, f"不明({oid})") if r.get("is_official") == 1 else "-"
            })
        
        all_summary.append({
            "vol": ename.replace("SHOWROOM ビギナーチャレンジ ", ""),
            "total": total_count,
            "official": official_count,
            "free": free_count,
            "top_10_details": top_10
        })

    # 画面表示
    for data in all_summary:
        with st.expander(f"{data['vol']} (取得数: {data['total']}ルーム)"):
            c1, c2, c3 = st.columns(3)
            c1.metric("総数", data['total'])
            c2.metric("公式", data['official'])
            c3.metric("フリー", data['free'])
            
            st.write("### 上位10ルーム内訳")
            st.table(pd.DataFrame(data['top_10_details']))