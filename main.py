import requests
import os
import sys
import random # 新增随机库
from datetime import datetime, timedelta, date

# ================= 1. 读取配置 =================
APP_ID = os.environ["APP_ID"]
APP_SECRET = os.environ["APP_SECRET"]
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
        res = requests.get(url, timeout=5).json()
        if res["status"] == "1" and res["forecasts"]:
            today = res["forecasts"][0]["casts"][0]
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
        print(f"❌ 天气获取错误: {e}")
    return None

def get_ciba():
    """获取每日金句 (增强版)"""
    # 备用金句库，如果接口挂了就用这里的
    backups = [
        ("Love represents a pleasant state of mind.", "爱代表一种令人愉悦的精神状态。"),
        ("Where there is love, there are always miracles.", "哪里有爱，哪里就有奇迹。"),
        ("You make my heart smile.", "你让我的心微笑。"),
        ("To the world you may be one person, but to me you are the world.", "对于世界而言，你是一个人；但是对于我而言，你是整个世界。"),
        ("Every day is a new beginning.", "每一天都是新的开始。")
    ]
    
    try:
        # 尝试使用 HTTPS 请求，设置5秒超时
        url = "https://open.iciba.com/dsapi/"
        res = requests.get(url, timeout=5, verify=False).json() # verify=False忽略证书报错
        content = res.get("content")
        note = res.get("note")
        
        # 确保真的取到了文字
        if content and note:
            return content, note
        else:
            raise Exception("API返回空数据")
            
    except Exception as e:
        print(f"⚠️ 金句接口报错: {e}，已切换为本地备用句。")
        return random.choice(backups) # 随机返回一句

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
    try:
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
        res = requests.get(url, timeout=10).json()
        return res.get("access_token")
    except Exception as e:
        print(f"❌ Token获取失败: {e}")
        return None

# ================= 3. 发送主逻辑 =================
def send_msg(mode):
    token = get_token()
    if not token:
        print("❌ 无法获取Token，任务终止")
        return

    beijing_now = get_beijing_time()
    today_str = beijing_now.strftime("%Y-%m-%d %A")
    
    data = {}
    template_id = ""

    if mode == "morning":
        print(">>> 正在准备早安数据...")
        template_id = TEMPLATE_MORNING
        weather = get_weather()
        note_en, note_ch = get_ciba() # 这里调用了新的增强版函数
        
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
            "note_en": {"value": note_en}, # 注意这里的变量名
            "note_ch": {"value": note_ch}  # 必须和模板里的{{note_ch.DATA}}对应
        }
        
    elif mode == "night":
        print(">>> 正在准备晚安数据...")
        template_id = TEMPLATE_NIGHT
        data = {
            "date": {"value": today_str}
        }

    # 循环发送
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
        
        try:
            res = requests.post(url, json=payload, timeout=10).json()
            print(f"📤 发送给 [{user}] 结果: {res}")
        except Exception as e:
            print(f"❌ 发送给 [{user}] 失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1] 
        send_msg(mode)
    else:
        print("❌ 错误：请指定模式 (morning/night)")
