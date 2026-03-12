import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

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
    
    # プログレスバー
    st.write("### 取得進捗")
    overall_progress = st.progress(0)
    status_text = st.empty()
    
    for index, (_, event_data) in enumerate(target_events.iterrows()):
        eid = event_data['event_id']
        ename = event_data['event_name']
        
        # イベントURLの生成
        event_url = f"https://www.showroom-live.com/event/{event_data['event_url_key']}"
        
        # 期間の変換
        start_dt = datetime.fromtimestamp(event_data['started_at']).strftime('%Y/%m/%d %H:%M')
        end_dt = datetime.fromtimestamp(event_data['ended_at']).strftime('%Y/%m/%d %H:%M')
        event_period = f"{start_dt} - {end_dt}"
        
        status_text.text(f"処理中 ({index+1}/{total_events}): {ename}")
        
        all_rooms = []
        page = 1
        
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

        total_count = len(all_rooms)
        official_count = sum(1 for r in all_rooms if r.get("is_official") == 1)
        free_count = total_count - official_count
        
        off_ratio = (official_count / total_count * 100) if total_count > 0 else 0
        free_ratio = (free_count / total_count * 100) if total_count > 0 else 0

        top_10 = []
        for r in all_rooms[:10]:
            oid = str(r.get("organizer_id"))
            is_off = r.get("is_official") == 1
            rid = str(r.get("room_id"))
            profile_url = f"https://www.showroom-live.com/room/profile?room_id={rid}"
            
            top_10.append({
                "順位": r.get("rank"),
                "ルーム名": r.get("room_name"),
                "ルームID": profile_url,
                "ポイント": f"{r.get('point', 0):,}",
                "公式 or フリー": "公式" if is_off else "フリー",
                "所属先": org_map.get(oid, f"不明({oid})") if is_off else ""
            })
        
        all_summary.append({
            "full_name": ename,
            "short_name": ename.replace("SHOWROOM ビギナーチャレンジ ", "Vol."), # グラフのラベル用
            "event_url": event_url,
            "period": event_period,
            "total": total_count,
            "official": official_count,
            "off_ratio": off_ratio,
            "free": free_count,
            "free_ratio": free_ratio,
            "top_10_details": top_10
        })
        
        overall_progress.progress((index + 1) / total_events)

    status_text.text("すべてのデータの取得が完了しました。")
    st.write("---")

    if all_summary:
        # --- グラフ表示セクション ---
        st.write("### 属性推移グラフ")
        
        # グラフ用データの作成（時系列順にするためリバース）
        chart_data = pd.DataFrame(all_summary[::-1])
        
        # 折れ線グラフの表示
        st.line_chart(
            chart_data,
            x="short_name",
            y=["total", "official", "free"],
            color=["#000000", "#FF4B4B", "#0083B8"] # 黒:総数, 赤:公式, 青:フリー
        )
        st.write("---")

    # --- アコーディオン表示 ---
    for data in all_summary:
        with st.expander(f"{data['full_name']} (全 {data['total']} ルーム)"):
            st.markdown(f"🔗 [イベント詳細を表示]({data['event_url']})")
            st.caption(f"期間: {data['period']}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("総数", data['total'])
            
            c2.markdown(
                f"""<p style='margin-bottom:0px;color:rgba(49, 51, 63, 0.6);font-size:14px;'>公式</p>
                <p style='font-size:28px;font-weight:600;'>{data['official']} <span style='font-size:16px;font-weight:400;color:gray;'>({data['off_ratio']:.1f}%)</span></p>""",
                unsafe_allow_html=True
            )
            
            c3.markdown(
                f"""<p style='margin-bottom:0px;color:rgba(49, 51, 63, 0.6);font-size:14px;'>フリー</p>
                <p style='font-size:28px;font-weight:600;'>{data['free']} <span style='font-size:16px;font-weight:400;color:gray;'>({data['free_ratio']:.1f}%)</span></p>""",
                unsafe_allow_html=True
            )
            
            st.write("#### 上位10ルーム内訳")
            df_top10 = pd.DataFrame(data['top_10_details'])
            st.dataframe(
                df_top10,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ルーム名": st.column_config.TextColumn("ルーム名"),
                    "ルームID": st.column_config.LinkColumn(
                        "ルームID",
                        display_text=r"room_id=(\d+)$"
                    ),
                    "ポイント": st.column_config.TextColumn("ポイント"),
                }
            )