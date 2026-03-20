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
    events = events[events['event_name'].str.contains("ビギナーチャレンジ", na=False)].copy()
    events = events.sort_values('event_id', ascending=False)
    return events, orgs

events_df, org_df = load_master_data()
org_map = dict(zip(org_df.iloc[:, 0].astype(str), org_df.iloc[:, 1]))

# --- UI：メインエリアでの選択設定 ---
st.write("#### 取得・分析の設定")
c_ui1, c_ui2 = st.columns([1, 3])

with c_ui1:
    mode = st.radio("取得モード", ["全件取得", "個別選択"], index=1)

with c_ui2:
    if mode == "全件取得":
        selected_event_names = events_df['event_name'].tolist()
        st.info(f"全 {len(selected_event_names)} 件のイベントを処理対象にします。")
    else:
        selected_event_names = st.multiselect(
            "分析対象のイベントを選択してください（複数選択可）",
            options=events_df['event_name'].tolist(),
            default=events_df['event_name'].tolist()[0] if not events_df.empty else None
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
        
        start_ts = event_data['started_at']
        end_ts = event_data['ended_at']
        start_dt = datetime.fromtimestamp(start_ts, timezone.utc).astimezone(JST).strftime('%Y/%m/%d %H:%M')
        end_dt = datetime.fromtimestamp(end_ts, timezone.utc).astimezone(JST).strftime('%Y/%m/%d %H:%M')
        event_period = f"{start_dt} - {end_dt}"
        
        all_rooms_data = [] # 生データ保持用
        seen_room_ids = set() # 重複排除用
        page = 1
        total_entries_const = 0 # APIの総数を保持
        
        while True:
            api_url = f"https://www.showroom-live.com/api/event/room_list?event_id={eid}&p={page}"
            try:
                res = requests.get(api_url, timeout=10).json()
                
                # 1ページ目で、マスターとなる総数を取得
                if page == 1:
                    total_entries_const = int(res.get("total_entries", 0))
                
                rooms = res.get("list", [])
                if not rooms:
                    break
                
                # 重複を排除しながらデータを蓄積
                for r in rooms:
                    rid = r.get("room_id")
                    if rid not in seen_room_ids:
                        seen_room_ids.add(rid)
                        all_rooms_data.append(r)
                
                status_text.text(f"処理中 ({index+1}/{total_events}): {ename} ({len(all_rooms_data)}/{total_entries_const})")
                
                # 全件取得、あるいは次ページがなければ終了
                if len(all_rooms_data) >= total_entries_const or res.get("next_page") is None:
                    break
                
                page += 1
                time.sleep(0.05)
            except:
                break
        
        if total_entries_const == 0 and not all_rooms_data:
            overall_progress.progress((index + 1) / total_events)
            continue

        # --- 集計ロジックの修正 ---
        # 1. 総数はAPIの数字をそのまま使う
        total_count = total_entries_const
        
        # 2. 公式数は、実際に取得できたデータから判定（重複排除済み）
        official_count = sum(1 for r in all_rooms_data if r.get("is_official") == 1)
        
        # 3. フリー数は、総数から公式数を引いた「差分」とする（整合性重視）
        free_count = total_count - official_count
        
        # 比率計算
        off_ratio = (official_count / total_count * 100) if total_count > 0 else 0
        free_ratio = (free_count / total_count * 100) if total_count > 0 else 0

        # 上位10ルーム（表示用）
        top_10 = []
        for r in all_rooms_data[:10]:
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
            "event_id": eid,
            "full_name": ename,
            # "short_name": ename.replace("SHOWROOM ビギナーチャレンジ ", "Vol."),
            "short_name": ename.replace("SHOWROOM ビギナーチャレンジ ", ""),
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
        st.write("#### 属性推移グラフ")
        chart_df = pd.DataFrame(all_summary).sort_values('event_id', ascending=True)
        plot_data = chart_df.melt(id_vars=['short_name', 'event_id'], value_vars=['total', 'official', 'free'], var_name='category', value_name='count')

        chart = alt.Chart(plot_data).mark_line(point=True).encode(
            x=alt.X('short_name:N', sort=alt.SortField('event_id', order='ascending'), title='イベント'),
            y=alt.Y('count:Q', title='ルーム数'),
            color=alt.Color('category:N', scale=alt.Scale(domain=['total', 'official', 'free'], range=['#000000', '#FF4B4B', '#0083B8']), title='属性'),
            tooltip=['short_name', 'category', 'count']
        ).properties(height=400).interactive()

        st.altair_chart(chart, use_container_width=True)
        st.write("---")

        display_summary = sorted(all_summary, key=lambda x: x['event_id'], reverse=True)
        for data in display_summary:
            with st.expander(f"{data['full_name']} (全 {data['total']} ルーム)"):
                st.markdown(f"🔗 [イベント詳細を表示]({data['event_url']})")
                st.caption(f"期間: {data['period']}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("総数", data['total'])
                c2.markdown(f"<p style='margin-bottom:0px;color:gray;font-size:14px;'>公式</p><p style='font-size:28px;font-weight:600;'>{data['official']} <span style='font-size:16px;font-weight:400;color:gray;'>({data['off_ratio']:.1f}%)</span></p>", unsafe_allow_html=True)
                c3.markdown(f"<p style='margin-bottom:0px;color:gray;font-size:14px;'>フリー</p><p style='font-size:28px;font-weight:600;'>{data['free']} <span style='font-size:16px;font-weight:400;color:gray;'>({data['free_ratio']:.1f}%)</span></p>", unsafe_allow_html=True)
                
                st.write("#### 上位10ルーム内訳")
                df_top10 = pd.DataFrame(data['top_10_details'])
                st.dataframe(df_top10, use_container_width=True, hide_index=True, column_config={"ルームID": st.column_config.LinkColumn("ルームID", display_text=r"room_id=(\d+)$")})

elif not selected_event_names and mode == "個別選択":
    st.warning("対象のイベントを1つ以上選択してください。")