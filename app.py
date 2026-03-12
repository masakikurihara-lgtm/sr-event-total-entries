import streamlit as st
import pandas as pd
import requests
import time

# ① レイアウトをワイドに設定
st.set_page_config(layout="wide", page_title="SHOWROOM属性分析ツール")

st.title("SHOWROOM ビギナーチャレンジ属性分析（全件精査版）")

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
# オーガナイザーIDをキーにした辞書作成
org_map = dict(zip(org_df.iloc[:, 0].astype(str), org_df.iloc[:, 1]))

if st.button('全件属性分析を開始'):
    all_summary = []
    
    # イベントのリストを降順ソート
    target_events = events_df.sort_values('event_id', ascending=False)
    total_events = len(target_events)
    
    # ④ プログレスバー
    st.write("### 取得進捗")
    overall_progress = st.progress(0)
    status_text = st.empty()
    
    for index, (_, event_data) in enumerate(target_events.iterrows()):
        eid = event_data['event_id']
        ename = event_data['event_name']
        
        status_text.text(f"処理中 ({index+1}/{total_events}): {ename}")
        
        all_rooms = []
        page = 1
        
        # イベント内の全ページ取得
        while True:
            api_url = f"https://www.showroom-live.com/api/event/room_list?event_id={eid}&p={page}"
            try:
                res = requests.get(api_url, timeout=10).json()
                rooms = res.get("list", [])
                
                if not rooms:
                    break
                
                all_rooms.extend(rooms)
                
                if res.get("next_page") is None:
                    break
                page += 1
                time.sleep(0.05)
            except:
                break
        
        if not all_rooms:
            overall_progress.progress((index + 1) / total_events)
            continue

        # 集計
        total_count = len(all_rooms)
        official_count = sum(1 for r in all_rooms if r.get("is_official") == 1)
        free_count = total_count - official_count

        # 上位10名のデータ整形
        top_10 = []
        for r in all_rooms[:10]:
            oid = str(r.get("organizer_id"))
            is_off = r.get("is_official") == 1
            rid = str(r.get("room_id"))
            rname = r.get("room_name")
            
            # ルームIDに直接プロフィールURLを格納
            profile_url = f"https://www.showroom-live.com/room/profile?room_id={rid}"
            
            top_10.append({
                "順位": r.get("rank"),
                "ルーム名": rname,    # 名前をテキストとして保持
                "ルームID": profile_url, # URLを保持
                "ポイント": f"{r.get('point', 0):,}",
                "公式 or フリー": "公式" if is_off else "フリー",
                "所属先": org_map.get(oid, f"不明({oid})") if is_off else ""
            })
        
        all_summary.append({
            "vol": ename.replace("SHOWROOM ビギナーチャレンジ ", ""),
            "total": total_count,
            "official": official_count,
            "free": free_count,
            "top_10_details": top_10
        })
        
        overall_progress.progress((index + 1) / total_events)

    status_text.text("すべてのデータの取得が完了しました。")
    st.write("---")

    # --- 画面表示 ---
    for data in all_summary:
        with st.expander(f"{data['vol']} (全 {data['total']} ルーム)"):
            c1, c2, c3 = st.columns(3)
            c1.metric("総数", data['total'])
            c2.metric("公式", data['official'])
            c3.metric("フリー", data['free'])
            
            st.write("#### 上位10ルーム内訳")
            
            df_top10 = pd.DataFrame(data['top_10_details'])
            
            # DataFrameの表示設定
            st.dataframe(
                df_top10,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ルーム名": st.column_config.TextColumn("ルーム名"),
                    "ルームID": st.column_config.LinkColumn(
                        "ルームID",
                        # URLの末尾にある数字（room_id）だけを抜き出して表示する正規表現
                        display_text=r"room_id=(\d+)$"
                    ),
                    "ポイント": st.column_config.TextColumn("ポイント"),
                }
            )