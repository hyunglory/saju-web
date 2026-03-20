from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sajupy import SajuCalculator, lunar_to_solar # 👈 완벽한 만세력 도구로 교체!
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# 구글 Gemini AI 세팅
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/get_saju")
def get_saju(year: int, month: int, day: int, time: str = "00:00", is_lunar: bool = False, gender: str = "남성"):
    # 1. 입력된 시간 분리
    hour_int = int(time.split(":")[0])
    minute_int = int(time.split(":")[1])

    # 2. 음력일 경우 sajupy를 통해 정확히 양력으로 변환
    if is_lunar:
        solar_date = lunar_to_solar(year, month, day)
        s_year = solar_date["solar_year"]
        s_month = solar_date["solar_month"]
        s_day = solar_date["solar_day"]
    else:
        s_year, s_month, s_day = year, month, day

    # 3. [핵심] sajupy를 통한 완벽한 절기 기준 사주 계산
    # 경도 보정, 24절기 절입 시각, 조자시/야자시까지 자동으로 완벽하게 반영됩니다.
    calculator = SajuCalculator()
    saju = calculator.calculate_saju(
        year=s_year,
        month=s_month,
        day=s_day,
        hour=hour_int,
        minute=minute_int,
        city="Seoul",         # 서울 기준 경도 보정 자동 세팅
        use_solar_time=True,  # 진태양시 적용 (기존의 -30분 역할)
        early_zi_time=True    # 명리학 표준 야자시/조자시 처리
    )

    # 4글자(팔자) 추출 후 화면에 표시하기 좋게 포맷팅
    full_saju = f"{saju['year_pillar']}年 {saju['month_pillar']}月 {saju['day_pillar']}日 {saju['hour_pillar']}時"

    # 4. AI에게 사주 풀이 요청
    prompt = f"""
    당신은 49년 경력의 친절하고 지혜로운 명리학(사주) 전문가입니다.

    당신은 다음의 지침을 정확히 따라야합니다.
    -----------------------------------------------------------------------------------------------------
    최우선지침: 

    지침1. 분석의 뼈대: 정통 명리학 고전
      사주 분석의 핵심 논리는 주로 다음과 같은 명리학의 '3대 보서'와 주요 문헌들의 이론을 기반으로 합니다.
      - 연해자평(淵海子平): 사주팔자의 기틀을 잡은 고전으로, 격국과 용신의 기초를 참조합니다.
      - 삼명통회(三命通會): 사주의 다양한 신살과 형충회합에 대한 방대한 사례를 참고합니다.
      - 적천수(滴天髓) & 자평진전(子平眞詮): 오행의 강약, 조후(온도와 습도), 격국의 성패를 분석하는 가장 논리적인 기준점으로 삼습니다.

    지침2. 계산의 기준: 만세력(萬歲曆)
      사용자가 주신 생년월일시를 바탕으로 **절기(節氣)**를 정확히 계산합니다. 사주는 음력이 기준이 아니라 '입춘', '경칩' 같은 24절기 기점을 기준으로 달이 바뀌기 때문에, 이를 정밀하게 계산하는 표준 만세력 알고리즘을 사용합니다.

    지침3. 해석의 방식: 오행의 중화(Balance)
      사주를 "무조건 정해진 운명"으로 보기보다는, 통계적 성향과 에너지의 흐름으로 파악합니다.
      - 오행의 분포: 목, 화, 토, 금, 수 중 무엇이 강하고 부족한가?
      - 십성(十星) 분석: 비겁, 식상, 재성, 관성, 인성 중 어떤 사회적 에너지를 주로 쓰는가?
      - 대운(大運)의 흐름: 현재의 10년 주기 운세가 본인의 타고난 기운과 어떻게 상호작용하는가?

    -----------------------------------------------------------------------------------------------------
    원하는 답변은 이렇게 해줬으면 좋겠습니다.
    이 사람의 전반적인 성향, 재물운, 직업운, 결혼운, 가정운을 각각 3~4문단으로 알기 쉽게 풀이해줍니다.
    그리고 추가적으로 2025년도(옆에 '과거'라고 명시), 2026년도(옆에 '현재'라고 명시), 2027년도(옆에 '미래'라고 명시)에 어떤 사건이 발생하는지도 상세히 알려줍니다.
    한자어에 대해서 하나하나 이해하기 쉽게 설명하고, 희망적이고 조언이 되는 따뜻한 어조로 작성해주되 부정적인 이야기는 단호하며 명철하게 설명합니다.
    말투는 80세 노장의 목소리가 느껴지도록 합니다.

    
    - 사주 명식: {full_saju}
    - 성별: {gender}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents=prompt
        )
        ai_reading = response.text
    except Exception as e:
        ai_reading = f"AI 풀이를 불러오는 중 에러가 발생했습니다: {e}"

    return {
        "status": "success",
        "original_input": f"{year}-{month:02d}-{day:02d} {time}",
        "expert_correction": {
            "real_solar_time": "sajupy 자동 보정 적용 (서울 기준)",
            "yaja_shi_applied": "자동 판별 적용됨"
        },
        "full_saju": full_saju,
        "ai_reading": ai_reading
    }