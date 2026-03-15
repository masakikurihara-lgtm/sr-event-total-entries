import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timezone, timedelta
import altair as alt

# ① レイアウト設定
st.set_page_config(layout="wide", page_title="SHOWROOM ビギチャレ属性分析ツール")

st.markdown(
    "<h1 style='font-size:28px; text-align:center; color:#1f2937;'>SHOWROOM ビギナーチャレンジ属性分析</h1>",
    unsafe_allow_html=True
)

st.markdown("---")

EVENT_CSV_URL = "https://mksoul-pro.com/showroom/file/sr-event-archive.csv"
ORG_CSV_URL = "https://mksoul-pro.com/showroom/file/organizer_list.csv"

# 日本時間(JST)の定義
JST = timezone(timedelta(hours=9))

@st.cache_data
def load_master_data():
    events = pd.read_csv(EVENT_CSV_URL)
    orgs = pd.read_csv(ORG_CSV_URL)
    # ビギナーチャレンジのみ抽出（最新順）
    events = events[events['event_name'].str.contains("ビギナーチャレンジ", na=False)].copy()
    events = events.sort_values('event_id', ascending=False)
    return events, orgs

events_df, org_df = load_master_data()
org_map = dict(zip(org_df.iloc[:, 0].astype(str), org_df.iloc[:, 1]))

# --- UI：設定エリア ---
st.write("#### 取得・分析の設定")
c_ui1, c_ui2 = st.columns([1, 3])

with c_ui1:
    mode = st.radio("取得モード", ["全件取得", "個別選択"], index=1)

with c_ui2:
    if mode == "全件取得":
        selected_event_names = events_df['event_name'].tolist()
        st.info(f"全 {len(selected_event_names)} 件のイベントを処理対象にします。")
    else:
        default_val = [events_df['event_name'].tolist()[0]] if not events_df.empty else []
        selected_event_names = st.multiselect(
            "分析対象のイベントを選択してください（複数選択可）",
            options=events_df['event_name'].tolist(),
            default=default_val
        )

# 実行ボタン
if st.button('属性分析を開始', type='primary') and selected_event_names:
    all_summary = []
    target_events = events_df[events_df['event_name'].isin(selected_event_names)]
    total_events = len(target_events)
    
    st.write(f"---")
    st.write(f"#### 取得進捗 ({total_events}件)")
    overall_progress = st.progress(0)
    status_text = st.empty()
    
    for index, (_, event_data) in enumerate(target_events.iterrows()):
        eid = event_data['event_id']
        ename = event_data['event_name']
        event_url = f"https://www.showroom-live.com/event/{event_data['event_url_key']}"
        
        # 期間変換
        start_ts = event_data['started_at']
        end_ts = event_data['ended_at']
        start_dt = datetime.fromtimestamp(start_ts, timezone.utc).astimezone(JST).strftime('%Y/%m/%d %H:%M')
        end_dt = datetime.fromtimestamp(end_ts, timezone.utc).astimezone(JST).strftime('%Y/%m/%d %H:%M')
        event_period = f"{start_dt} - {end_dt}"
        
        all_rooms = []
        page = 1
        expected_total = 0
        retry_count = 0
        
        # --- 強化された全ページ取得ロジック ---
        while True:
            api_url = f"https://www.showroom-live.com/api/event/room_list?event_id={eid}&p={page}"
            try:
                res = requests.get(api_url, timeout=10).json()
                rooms = res.get("list", [])
                
                # 初回リクエスト時に期待される総数を取得
                if page == 1:
                    expected_total = int(res.get("total_entries", 0))
                
                if not rooms:
                    # まだ総数に達していないのに空リストが返った場合、3回までリトライ
                    if len(all_rooms) < expected_total and retry_count < 3:
                        retry_count += 1
                        time.sleep(1)
                        continue
                    else:
                        break
                
                all_rooms.extend(rooms)
                retry_count = 0 # 取得できたらリトライカウントをリセット
                
                status_text.text(f"取得中 ({index+1}/{total_events}): {ename} ({len(all_rooms)}/{expected_total})")
                
                # 取得済み数が期待総数に達したら終了
                if len(all_rooms) >= expected_total:
                    break
                
                page += 1
                time.sleep(0.05)
            except Exception:
                break
        
        if not all_rooms:
            overall_progress.progress((index + 1) / total_events)
            continue

        total_count = len(all_rooms)
        official_count = sum(1 for r in all_rooms if r.get("is_official") == 1)
        free_count = total_count - official_count
        
        off_ratio = (official_count / total_count * 100) if total_count > 0 else 0
        free_ratio = (free_count / total_count * 100) if total_count > 0 else 0

        # 上位10ルーム
        top_10 = []
        for r in all_rooms[:10]:
            oid = str(r.get("organizer_id"))
            is_off = r.get("is_official") == 1
            rid = str(r.get("room_id"))
            top_10.append({
                "順位": r.get("rank"),
                "ルーム名": r.get("room_name"),
                "リンク": f"https://www.showroom-live.com/room/profile?room_id={rid}",
                "ポイント": f"{r.get('point', 0):,}",
                "属性": "公式" if is_off else "フリー",
                "所属先": org_map.get(oid, f"不明({oid})") if is_off else ""
            })
        
        all_summary.append({
            "event_id": eid,
            "full_name": ename,
            "short_name": ename.replace("SHOWROOM ビギナーチャレンジ ", "Vol."),
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

    status_text.text("完了しました。")

    if all_summary:
        # 属性推移グラフ
        chart_df = pd.DataFrame(all_summary).sort_values('event_id')
        plot_data = chart_df.melt(id_vars=['short_name', 'event_id'], value_vars=['total', 'official', 'free'], var_name='属性', value_name='件数')

        chart = alt.Chart(plot_data).mark_line(point=True).encode(
            x=alt.X('short_name:N', sort=alt.SortField('event_id', order='ascending'), title='Vol.'),
            y=alt.Y('件数:Q'),
            color=alt.Color('属性:N', scale=alt.Scale(domain=['total', 'official', 'free'], range=['#000000', '#FF4B4B', '#0083B8'])),
            tooltip=['short_name', '属性', '件数']
        ).properties(height=400).interactive()

        st.altair_chart(chart, use_container_width=True)

        # 詳細カード表示
        for data in sorted(all_summary, key=lambda x: x['event_id'], reverse=True):
            with st.expander(f"{data['full_name']} (計 {data['total']} ルーム)"):
                st.markdown(f"🔗 [イベントページ]({data['event_url']}) | 期間: {data['period']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("総数", data['total'])
                c2.metric("公式", f"{data['official']} ({data['off_ratio']:.1f}%)")
                c3.metric("フリー", f"{data['free']} ({data['free_ratio']:.1f}%)")
                
                st.dataframe(
                    pd.DataFrame(data['top_10_details']),
                    hide_index=True,
                    use_container_width=True,
                    column_config={"リンク": st.column_config.LinkColumn(display_text="開く")}
                )

elif not selected_event_names and mode == "個別選択":
    st.warning("イベントを選択してください。")