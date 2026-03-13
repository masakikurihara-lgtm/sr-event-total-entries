import requests
import time

def find_event_ids():
    # 探索のヒント情報
    targets = [
        {"vol": 1, "room_id": 553840, "name": "SHOWROOM ビギナーチャレンジ vol.1"},
        {"vol": 2, "room_id": 552276, "name": "SHOWROOM ビギナーチャレンジ vol.2"},
        {"vol": 3, "room_id": 554687, "name": "SHOWROOM ビギナーチャレンジ vol.3"},
        {"vol": 4, "room_id": 554806, "name": "SHOWROOM ビギナーチャレンジ vol.4"},
        {"vol": 5, "room_id": 548165, "name": "SHOWROOM ビギナーチャレンジ vol.5"},
    ]

    # Vol.6が39733なので、そこから少し余裕を見て39700から下に向かって探します
    start_id = 39732
    end_id = 35000  # 十分な範囲
    
    found_results = {}
    
    print(f"探索を開始します (Range: {start_id} down to {end_id})...")
    
    # 計算効率のため、未発見のターゲットがある間ループ
    current_id = start_id
    while current_id >= end_id and len(found_results) < len(targets):
        # ターゲットごとに確認（まだ見つかっていないものだけ）
        for target in targets:
            if target["vol"] in found_results:
                continue
                
            # 貢献ランキングAPIを叩く
            api_url = f"https://www.showroom-live.com/api/event/contribution_ranking?event_id={current_id}&room_id={target['room_id']}"
            
            try:
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # event情報の存在確認
                    event_info = data.get("event", {})
                    actual_name = event_info.get("event_name", "")
                    
                    if target["name"] == actual_name:
                        print(f"【発見！】Vol.{target['vol']} の Event ID は '{current_id}' です。")
                        found_results[target["vol"]] = {
                            "event_id": current_id,
                            "started_at": event_info.get("started_at"),
                            "ended_at": event_info.get("ended_at"),
                            "event_url_key": event_info.get("event_url", "").split("/")[-1]
                        }
            except Exception as e:
                pass
        
        current_id -= 1
        # SHOWROOMのサーバーに負荷をかけすぎないよう少し待機
        if current_id % 10 == 0:
            print(f"現在 {current_id} 付近を探索中...")
            time.sleep(0.5)

    print("\n--- 探索結果まとめ ---")
    for vol in sorted(found_results.keys()):
        res = found_results[vol]
        print(f"Vol.{vol}: ID={res['event_id']}, URL_KEY={res['event_url_key']}, Start={res['started_at']}, End={res['ended_at']}")

if __name__ == "__main__":
    find_event_ids()