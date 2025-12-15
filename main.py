import requests
import os
import sys
from datetime import datetime, timedelta, date

# ================= 1. 配置读取 =================
APP_ID = os.environ["APP_ID"]
APP_SECRET = os.environ["APP_SECRET"]
USER_ID_STRING = os.environ["USER_ID"] 
TEMPLATE_MORNING = os.environ["TEMPLATE_MORNING"]
TEMPLATE_NIGHT = os.environ["TEMPLATE_NIGHT"]
WEATHER_KEY = os.environ["WEATHER_KEY"]
CITY_CODE = os.environ["CITY_CODE"]
LOVE_START_DATE = os.environ["LOVE_START_DATE"]
PET_START_DATE = os.environ["PET_START_DATE"]

# ================= 2. 核心函数 =================

def get_beijing_time():
    """获取北京时间"""
    utc_now = datetime.utcnow()
    beijing_now = utc_now + timedelta(hours=8)
    return beijing_now

def get_weather():
    """获取天气"""
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={CITY_CODE}&key={WEATHER_KEY}&extensions=all"
    try:
        res = requests.get(url, timeout=5).json()
        if res["status"] == "1" and res["forecasts"]:
            today = res["forecasts"][0]["casts"][0]
            # 获取湿度
            url_base = f"https://restapi.amap.com/v3/weather/weatherInfo?city={CITY_CODE}&key={WEATHER_KEY}&extensions=base"
            res_base = requests.get(url_base, timeout=5).json()
            humidity = "适宜"
            if res_base["status"] == "1" and res_base["lives"]:
                humidity = res_base["lives"][0]["humidity"] + "%"

            return {
                "weather": today["dayweather"],
                "min_temp": today["nighttemp"] + "℃",
                "max_temp": today["daytemp"] + "℃",
                "wind_dir": today["daywind"],
                "wind_class": today["daypower"] + "级",
                "humidity": humidity,
                "city": res["forecasts"][0]["city"]
            }
    except Exception as e:
        print(f"❌ 天气获取失败: {e}")
        return None

def calculate_days(start_date_str):
    try:
        today = get_beijing_time().date()
        start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        return (today - start).days
    except:
        return 0

def get_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    res = requests.get(url).json()
    return res.get("access_token")

# ================= 3. 发送逻辑 =================
def send_msg(mode):
    token = get_token()
    beijing_now = get_beijing_time()
    today_str = beijing_now.strftime("%Y-%m-%d %A")
    
    data = {}
    template_id = ""

    if mode == "morning":
        print(">>> 正在准备早安数据...")
        template_id = TEMPLATE_MORNING
        weather = get_weather()
        
        if not weather:
            print("❌ 天气失败，停止")
            return

        data = {
            "date": {"value": today_str},
            "city": {"value": weather["city"]},
            "weather": {"value": weather["weather"]},
            "min_temp": {"value": weather["min_temp"]},
            "max_temp": {"value": weather["max_temp"]},
            "wind_dir": {"value": weather["wind_dir"]},
            "wind_class": {"value": weather["wind_class"]},
            "humidity": {"value": weather["humidity"]},
            "love_days": {"value": calculate_days(LOVE_START_DATE)},
            "pet_days": {"value": calculate_days(PET_START_DATE)}
            # 删除了 words 相关代码
        }
        
    elif mode == "night":
        print(">>> 正在准备晚安数据...")
        template_id = TEMPLATE_NIGHT
        data = {"date": {"value": today_str}}

    # 发送
    user_list = USER_ID_STRING.split(",")
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    
    for user in user_list:
        user = user.strip()
        if not user: continue
        
        payload = {
            "touser": user,
            "template_id": template_id,
            "data": data
        }
        res = requests.post(url, json=payload).json()
        print(f"📤 发送给 [{user}] 结果: {res}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_msg(sys.argv[1])
    else:
        print("❌ 请指定参数: morning 或 night")
