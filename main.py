from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
from korean_lunar_calendar import KoreanLunarCalendar
from google import genai
import os # [추가] 시스템에 접근하는 도구
from dotenv import load_dotenv # [추가] 금고 여는 도구

# 금고(.env) 열기!
load_dotenv()

app = FastAPI()

# 🔑 [가장 안전한 방식] 금고에서 키를 가져옵니다. 코드에는 키가 보이지 않습니다!
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

CHEONGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
JIJI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/get_saju")
def get_saju(year: int, month: int, day: int, time: str = "00:00", is_lunar: bool = False):
    birth_dt = datetime.strptime(f"{year}-{month:02d}-{day:02d} {time}", "%Y-%m-%d %H:%M")
    
    # [1] 경도 보정 및 야자시 판별
    real_solar_time = birth_dt - timedelta(minutes=30)
    
    if real_solar_time.hour >= 23:
        saju_date = real_solar_time + timedelta(days=1)
        yaja_shi_applied = True
    else:
        saju_date = real_solar_time
        yaja_shi_applied = False

    # [2] 년/월/일 6글자 뽑기
    calendar = KoreanLunarCalendar()
    if is_lunar:
        calendar.setLunarDate(saju_date.year, saju_date.month, saju_date.day, False)
    else:
        calendar.setSolarDate(saju_date.year, saju_date.month, saju_date.day)

    base_saju = calendar.getChineseGapJaString()
    
    # [3] 시주 계산 (시두법)
    time_index = (real_solar_time.hour + 1) // 2 % 12
    time_jiji = JIJI[time_index]
    
    day_pillar = base_saju.split(" ")[2]
    day_stem = day_pillar[0]
    day_stem_idx = CHEONGAN.index(day_stem)
    
    start_stem_idx = (day_stem_idx % 5) * 2 % 10
    time_stem_idx = (start_stem_idx + time_index) % 10
    time_cheongan = CHEONGAN[time_stem_idx]
    
    time_pillar = f"{time_cheongan}{time_jiji}時"
    full_saju = f"{base_saju} {time_pillar}"

    # 🤖 [4] AI에게 사주 풀이 시키기 (새로운 문법 적용!)
    prompt = f"""
    당신은 20년 경력의 친절하고 지혜로운 명리학(사주) 전문가입니다.
    다음 사주팔자를 바탕으로 이 사람의 전반적인 성향, 재물운, 직업운을 3~4문단으로 알기 쉽게 풀이해주세요.
    너무 어려운 한자어는 피하고, 희망적이고 조언이 되는 따뜻한 어조로 작성해주세요.
    
    사주 명식: {full_saju}
    """
    
    try:
        # [변경] 새로운 라이브러리의 호출 방식입니다.
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        ai_reading = response.text
    except Exception as e:
        ai_reading = f"AI 풀이를 불러오는 중 에러가 발생했습니다: {e}"

    return {
        "status": "success",
        "original_input": birth_dt.strftime("%Y-%m-%d %H:%M"),
        "expert_correction": {
            "real_solar_time": real_solar_time.strftime("%H:%M"),
            "yaja_shi_applied": yaja_shi_applied
        },
        "full_saju": full_saju,
        "ai_reading": ai_reading
    }