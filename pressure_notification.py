import requests
import datetime
import time
import os
import json
from dotenv import load_dotenv

# --- 設定項目 ---
load_dotenv()
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "OPENWEATHERMAP_API_KEY")
LATITUDE = float(os.getenv("LATITUDE", "LATITUDE"))  # 品川区役所の緯度
LONGITUDE = float(os.getenv("LONGITUDE", "LONGITUDE")) # 品川区役所の経度
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "DISCORD_WEBHOOK_URL")

print("API KEY:", os.getenv("OPENWEATHERMAP_API_KEY"))

# 通知トリガールール
# severity: 数値が小さいほど深刻度が高い（通知優先度が高い）
# level: 通知メッセージや内部的な識別に使うラベル
# horizon_hours: 監視する時間範囲（時間）
# drop_hpa: 低下量の閾値（hPa）
ALERT_RULES = [
    {"horizon_hours": 3, "drop_hpa": 3, "level": "急速低下(3時間予測)", "severity": 1},
    {"horizon_hours": 12, "drop_hpa": 10, "level": "顕著な低下(12時間予測)", "severity": 1},
    {"horizon_hours": 6, "drop_hpa": 6, "level": "中程度の低下(6時間予測)", "severity": 2},
    {"horizon_hours": 12, "drop_hpa": 6, "level": "中長期の低下(12時間予測)", "severity": 3},
    {"horizon_hours": 24, "drop_hpa": 5, "level": "日単位の変化に注意(24時間予測)", "severity": 4}, # J-STAGE論文考慮
]

# 通知のクールダウン時間 (秒)
NOTIFICATION_COOLDOWN_SECONDS = 3 * 60 * 60  # 3時間

# 最後に通知した情報を保存するファイル
LAST_NOTIFICATION_FILE = "last_notification_status.json"

# --- グローバル変数 (状態管理用) ---
last_notification_info = {
    "timestamp": 0,
    "message_summary": ""
}

def load_last_notification_status():
    global last_notification_info
    if os.path.exists(LAST_NOTIFICATION_FILE):
        try:
            with open(LAST_NOTIFICATION_FILE, 'r') as f:
                loaded_info = json.load(f)
                # キーが存在するか確認し、なければデフォルト値を設定
                last_notification_info["timestamp"] = loaded_info.get("timestamp", 0)
                last_notification_info["message_summary"] = loaded_info.get("message_summary", "")
        except Exception as e:
            print(f"Error loading last notification status: {e}")
            last_notification_info = {"timestamp": 0, "message_summary": ""}

def save_last_notification_status():
    try:
        with open(LAST_NOTIFICATION_FILE, 'w') as f:
            json.dump(last_notification_info, f)
    except Exception as e:
        print(f"Error saving last notification status: {e}")

def get_weather_forecast(api_key, lat, lon):
    api_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,daily,alerts&appid={api_key}&units=metric&lang=ja"
    try:
        response = requests.get(api_url, timeout=15) # タイムアウトを少し延長
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def check_pressure_changes(weather_data):
    if not weather_data or "current" not in weather_data or "hourly" not in weather_data:
        print("Invalid weather data format.")
        return None

    current_pressure = weather_data["current"]["pressure"]
    hourly_forecasts = weather_data["hourly"]

    alerts_found = []
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

    for rule in ALERT_RULES:
        horizon_hours = rule["horizon_hours"]
        threshold_hpa = rule["drop_hpa"]
        
        min_pressure_in_horizon = current_pressure
        time_of_min_pressure_utc_ts = weather_data["current"]["dt"] # 初期値は現在のタイムスタンプ

        # horizon_hours 先までの予報をチェック
        # OpenWeatherMapのhourlyデータは通常48時間分提供される
        for i in range(min(horizon_hours + 1, len(hourly_forecasts))):
            forecast_entry = hourly_forecasts[i]
            forecast_dt_utc = datetime.datetime.fromtimestamp(forecast_entry["dt"], datetime.timezone.utc)
            
            # 予報時刻が現在時刻より後で、かつ指定した horizon_hours 以内か
            # (i=0 は現在の気象情報なので、実質的に i=1 からが未来の予報として意味を持つが、
            #  計算上は current_pressure を使うため、0から回して最低値を探す)
            if (forecast_dt_utc - datetime.datetime.fromtimestamp(weather_data["current"]["dt"], datetime.timezone.utc)).total_seconds() / 3600 <= horizon_hours:
                 if forecast_entry["pressure"] < min_pressure_in_horizon:
                    min_pressure_in_horizon = forecast_entry["pressure"]
                    time_of_min_pressure_utc_ts = forecast_entry["dt"]
        
        pressure_drop = current_pressure - min_pressure_in_horizon

        if pressure_drop >= threshold_hpa:
            time_of_min_pressure_jst = datetime.datetime.fromtimestamp(time_of_min_pressure_utc_ts, datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=9)))
            
            time_diff_str = ""
            if time_of_min_pressure_jst.date() == now_jst.date():
                time_diff_str = f"本日{time_of_min_pressure_jst.strftime('%H:%M頃')}"
            else:
                time_diff_str = f"{time_of_min_pressure_jst.strftime('%m月%d日 %H:%M頃')}"
            
            message = (
                f"【気圧低下注意 - 品川区】({rule['level']})\n"
                f"現在から{time_diff_str}にかけて、気圧が約{pressure_drop:.1f}hPa低下する見込みです。\n"
                f"(現在: {current_pressure:.1f}hPa → {time_of_min_pressure_jst.strftime('%H:%M頃')}の予測最低値: {min_pressure_in_horizon:.1f}hPa)\n"
                f"頭痛や体調不良に注意してください。"
            )
            
            # 優先度: (severity低, pressure_drop高, horizon_hours低 の順で優先)
            priority_key = (rule["severity"], -pressure_drop, rule["horizon_hours"])
            
            alerts_found.append({
                "priority_key": priority_key,
                "message": message,
                "summary": f"{rule['level']}_drop_{pressure_drop:.1f}hPa" # クールダウン判定用
            })

    if not alerts_found:
        return None

    # 最も優先度の高いアラートを選択
    alerts_found.sort(key=lambda x: x["priority_key"]) # severity昇順、drop降順、horizon昇順
    return alerts_found[0]


def send_discord_notification(webhook_url, message):
    payload = {"content": message}
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Discord notification sent successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord notification: {e}")
        return False

def main():
    global last_notification_info
    script_start_time_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    print(f"Script started at {script_start_time_jst.strftime('%Y-%m-%d %H:%M:%S JST')}")

    load_last_notification_status()

    if not OPENWEATHERMAP_API_KEY or OPENWEATHERMAP_API_KEY == "YOUR_OPENWEATHERMAP_API_KEY":
        print("Error: OpenWeatherMap API key is not configured.")
        return
    if not DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URL == "YOUR_DISCORD_WEBHOOK_URL":
        print("Error: Discord Webhook URL is not configured.")
        return

    weather_data = get_weather_forecast(OPENWEATHERMAP_API_KEY, LATITUDE, LONGITUDE)

    if weather_data:
        # print("--- APIレスポンス全体 ---")
        # print(json.dumps(weather_data, ensure_ascii=False, indent=2))
        with open("api_response_debug.json", "w", encoding="utf-8") as f:
            json.dump(weather_data, f, ensure_ascii=False, indent=2)
        alert_info = check_pressure_changes(weather_data)
        
        if alert_info:
            current_time_unix = time.time()
            message = alert_info["message"]
            message_summary = alert_info["summary"]

            print(f"Alert detected: {message_summary}")

            if (current_time_unix - last_notification_info.get("timestamp", 0) > NOTIFICATION_COOLDOWN_SECONDS) or \
               (last_notification_info.get("message_summary") != message_summary):
                
                print(f"Sending notification: {message_summary}")
                if send_discord_notification(DISCORD_WEBHOOK_URL, message):
                    last_notification_info["timestamp"] = current_time_unix
                    last_notification_info["message_summary"] = message_summary
                    save_last_notification_status()
            else:
                print(f"Notification '{message_summary}' (summary: {last_notification_info.get('message_summary')}) is within cooldown period ({NOTIFICATION_COOLDOWN_SECONDS}s) or same as last. Skipping.")
        else:
            print("No significant pressure drop detected based on defined rules.")
            if last_notification_info.get("message_summary", ""): # 以前に何か通知していた場合
                 print(f"Conditions seem to have stabilized or changed. Clearing last notification summary: {last_notification_info.get('message_summary')}")
                 last_notification_info["message_summary"] = "" # 状況が変わったのでサマリークリア
                 save_last_notification_status()
    else:
        print("Could not retrieve weather data to check for pressure changes.")
    
    script_end_time_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    print(f"Script finished at {script_end_time_jst.strftime('%Y-%m-%d %H:%M:%S JST')}. Duration: {(script_end_time_jst - script_start_time_jst).total_seconds():.2f}s")

if __name__ == "__main__":
    main()