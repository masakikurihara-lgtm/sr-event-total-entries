import requests
import time

def find_missing_event_ids():
    # 調査対象のルームIDと期待されるイベント名
    targets = [
        {"vol": 5, "room_id": 548165, "name": "SHOWROOM ビギナーチャレンジ vol.5"},
        {"vol": 4, "room_id": 554806, "name": "SHOWROOM ビギナーチャレンジ vol.4"},
        {"vol": 3, "room_id": 554687, "name": "SHOWROOM ビギナーチャレンジ vol.3"},
        {"vol": 2, "room_id": 552276, "name": "SHOWROOM ビギナーチャレンジ vol.2"},
        {"vol": 1, "room_id": 553840, "name": "SHOWROOM ビギナーチャレンジ vol.1"},
    ]

    # Vol.6が39733なので、そこから1つずつカウントダウンして探します
    current_id = 39732 
    stop_id = 35000  # これ以上遡る必要はないと思われる範囲
    
    found_count = 0
    results = []

    print(f"--- 探索開始: ID {current_id} から遡ります ---")

    while current_id >= stop_id and found_count < len(targets):
        # まだ見つかっていないターゲットの中から確認
        for t in targets:
            if any(r['vol'] == t['vol'] for r in results):
                continue
            
            # 貢献ランキングAPIを叩く
            url = f"https://www.showroom-live.com/api/event/contribution_ranking?event_id={current_id}&room_id={t['room_id']}"
            
            try:
                res = requests.get(url, timeout=5).json()
                event_data = res.get("event", {})
                actual_name = event_data.get("event_name", "")

                # イベント名が合致したら確定
                if t['name'] == actual_name:
                    found_info = {
                        "vol": t['vol'],
                        "event_id": current_id,
                        "event_name": actual_name,
                        "event_url_key": event_data.get("event_url", "").split("/")[-1],
                        "started_at": event_data.get("started_at"),
                        "ended_at": event_data.get("ended_at")
                    }
                    results.append(found_info)
                    found_count += 1
                    print(f"✅ 【発見】Vol.{t['vol']} => ID: {current_id}")
            except:
                pass
        
        current_id -= 1
        
        # 進捗表示
        if current_id % 100 == 0:
            print(f"... ID {current_id} 付近を調査中 ...")
        
        # サーバー負荷軽減
        time.sleep(0.02)

    print("\n--- 探索完了！イベントアーカイブ用データ ---")
    # Vol順に並び替えて表示
    for r in sorted(results, key=lambda x: x['vol']):
        print(f"{r['event_id']},{r['event_name']},{r['event_url_key']},{r['started_at']},{r['ended_at']}")

if __name__ == "__main__":
    find_missing_event_ids()