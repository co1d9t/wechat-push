import requests
import os
import sys
from datetime import datetime, timedelta, date

# ================= 1. 读取配置 =================
APP_ID = os.environ["APP_ID"]
APP_SECRET = os.environ["APP_SECRET"]
# 这里获取到的可能是 "ID1,ID2" 这样的字符串
USER_ID_STRING = os.environ["USER_ID"] 
TEMPLATE_MORNING = os.environ["TEMPLATE_MORNING"]
TEMPLATE_NIGHT = os.environ["TEMPLATE_NIGHT"]
WEATHER_KEY = os.environ["WEATHER_KEY"]
CITY_CODE = os.environ["CITY_CODE"]
LOVE_START_DATE = os.environ["LOVE_START_DATE"]
PET_START_DATE = os.environ["PET_START_DATE"]

# ================= 2. 工具函数 =================

def get_beijing_time():
    """获取北京时间"""
    utc_now = datetime.utcnow()
    beijing_now = utc_now + timedelta(hours=8)
    return beijing_now

def get_weather():
    """获取高德天气"""
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={CITY_CODE}&key={WEATHER_KEY}&extensions=all"
    try:
        res = requests.get(url).json()
        if res["status"] == "1" and res["forecasts"]:
            today = res["forecasts"][0]["casts"][0]
            url_base = f"https://restapi.amap.com/v3/weather/weatherInfo?city={CITY_CODE}&key={WEATHER_KEY}&extensions=base"
            res_base = requests.get(url_base).json()
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
        print(f"天气获取错误: {e}")
    return None

def get_ciba():
    """获取每日金句"""
    try:
        url = "http://open.iciba.com/dsapi/"
        res = requests.get(url).json()
        return res["content"], res["note"]
    except:
        return "Every day is a new beginning.", "每一天都是新的开始。"

def calculate_days(start_date_str):
    """计算天数"""
    try:
        today = get_beijing_time().date()
        start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        return (today - start).days
    except:
        return 0

def get_token():
    """获取微信Token"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    res = requests.get(url).json()
    return res.get("access_token")

# ================= 3. 发送主逻辑 (已修改支持多人) =================
def send_msg(mode):
    token = get_token()
    beijing_now = get_beijing_time()
    today_str = beijing_now.strftime("%Y-%m-%d %A")
    
    data = {}
    template_id = ""

    # --- 准备数据 (只获取一次，避免重复请求API) ---
    if mode == "morning":
        print(">>> 正在准备早安数据...")
        template_id = TEMPLATE_MORNING
        weather = get_weather()
        note_en, note_ch = get_ciba()
        
        if not weather:
            print("❌ 天气获取失败，终止发送")
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
            "pet_days": {"value": calculate_days(PET_START_DATE)},
            "note_en": {"value": note_en},
            "note_ch": {"value": note_ch}
        }
        
    elif mode == "night":
        print(">>> 正在准备晚安数据...")
        template_id = TEMPLATE_NIGHT
        data = {
            "date": {"value": today_str}
        }

    # --- 循环发送给列表里的每个人 ---
    
    # 1. 用逗号分割字符串，变成列表
    user_list = USER_ID_STRING.split(",")
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    
    # 2. 遍历列表发送
    for user in user_list:
        user = user.strip() # 去除可能存在的空格
        if not user: continue # 如果是空的就跳过
        
        payload = {
            "touser": user,
            "template_id": template_id,
            "data": data
        }
        
        try:
            res = requests.post(url, json=payload).json()
            print(f"📤 发送给 [{user}] 结果: {res}")
        except Exception as e:
            print(f"❌ 发送给 [{user}] 失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1] 
        send_msg(mode)
    else:
        print("❌ 错误：请指定模式 (morning/night)")
