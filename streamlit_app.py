import streamlit as st
from openai import OpenAI

# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="건강 메모 챗봇",
    page_icon="🩺",
)

st.title("🩺 건강 메모 챗봇")
st.write(
    "아픈 증상을 말로 풀기 어려울 때, 병원에 가기 전 내 상태를 정리해드릴게요."
)

st.warning(
    "이 챗봇은 의료진을 대체하지 않으며, 진단이나 처방을 제공하지 않습니다. "
    "응급 증상이 있다면 즉시 119 또는 가까운 응급실에 연락하세요."
)

# =========================
# 사이드바 설정
# =========================

with st.sidebar:
    st.header("설정")

    openai_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="OpenAI API 키를 입력하세요."
    )

    mode = st.radio(
        "어떤 도움이 필요하신가요?",
        [
            "증상 정리",
            "병원 방문 가이드",
            "건강검진 결과 설명",
            "생활습관 코칭"
        ]
    )

    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()


# =========================
# 응급 키워드 감지
# =========================

emergency_keywords = [
    "가슴 통증",
    "흉통",
    "숨이 안 쉬",
    "숨쉬기 힘들",
    "호흡곤란",
    "의식 없음",
    "의식이 없어",
    "기절",
    "실신",
    "마비",
    "말이 어눌",
    "말이 안 나와",
    "극심한 두통",
    "갑자기 머리",
    "피를 토",
    "피 토",
    "경련",
    "발작",
    "죽고 싶",
    "자살",
    "극단적 선택",
    "심한 출혈",
    "피가 안 멈",
    "고열",
    "목이 심하게 부음",
    "삼키기 힘들",
]


def check_emergency(text):
    """
    사용자의 입력에 응급 가능성이 있는 표현이 있는지 확인합니다.
    실제 의료 판단이 아니라, 안전 안내를 위한 단순 키워드 감지입니다.
    """
    return any(keyword in text for keyword in emergency_keywords)


# =========================
# 건강 챗봇 시스템 프롬프트
# =========================

base_system_prompt = """
너는 '건강 메모 챗봇'이다.
너는 의사, 약사, 간호사 등 의료 전문가가 아니며,
진단, 처방, 약 복용량 결정, 치료법 확정을 해서는 안 된다.

너의 역할은 다음과 같다.
1. 사용자의 증상이나 건강 고민을 쉽게 정리한다.
2. 병원에 가기 전 의사에게 설명할 내용을 구조화한다.
3. 일반적인 건강 정보를 쉬운 한국어로 설명한다.
4. 위험 신호가 보이면 즉시 119 또는 응급실 방문을 안내한다.
5. 확정적인 병명 표현을 피하고, 가능성 중심으로 조심스럽게 말한다.
6. 약 이름이 나오더라도 복용량을 임의로 지시하지 않는다.
7. 사용자가 불안해하면 차분하고 다정하게 대응한다.

반드시 포함해야 하는 안전 원칙:
- "정확한 진단은 의료진의 진료가 필요합니다"라는 취지를 자연스럽게 포함한다.
- 응급 가능성이 있으면 "즉시 119 또는 가까운 응급실"을 안내한다.
- 사용자의 증상이 가볍다고 단정하지 않는다.
- 미성년자, 임산부, 노인, 만성질환자, 면역저하자라면 더 신중하게 진료 권유를 한다.

답변 형식:
- 너무 길게 쓰지 않는다.
- 사용자가 이해하기 쉬운 말로 쓴다.
- 필요한 경우 질문을 3~5개 정도 한다.
- 가능하면 마지막에 '병원에 말하면 좋은 요약'을 만들어준다.
"""


mode_prompts = {
    "증상 정리": """
현재 모드는 '증상 정리'이다.
사용자의 증상을 아래 항목으로 정리해줘.

- 주요 증상
- 시작 시점
- 증상 위치
- 동반 증상
- 최근 변화
- 복용한 약 또는 기존 질환
- 병원에 말하면 좋은 요약

진단하지 말고, 추가로 확인하면 좋은 질문을 제안해줘.
""",
    "병원 방문 가이드": """
현재 모드는 '병원 방문 가이드'이다.
사용자의 증상에서 위험 신호가 있는지 조심스럽게 확인해줘.

다만 병원에 가야 한다/안 가도 된다고 단정하지 말고,
아래처럼 안내해줘.

- 바로 진료가 필요할 수 있는 경우
- 빠른 시일 내 진료를 권할 수 있는 경우
- 집에서 경과를 보더라도 주의해야 할 변화

응급 가능성이 있으면 즉시 119 또는 응급실을 안내해줘.
""",
    "건강검진 결과 설명": """
현재 모드는 '건강검진 결과 설명'이다.
사용자가 입력한 검사 수치나 용어를 쉽게 설명해줘.

단, 수치 하나만으로 병을 진단하지 말고,
검사 결과는 나이, 성별, 병력, 복용 약, 다른 검사와 함께 해석해야 한다고 안내해줘.

가능하면 아래 형식으로 답해줘.
- 이 항목이 의미하는 것
- 높거나 낮을 때 일반적으로 확인하는 것
- 병원에서 물어보면 좋은 질문
""",
    "생활습관 코칭": """
현재 모드는 '생활습관 코칭'이다.
수면, 식사, 운동, 스트레스, 물 섭취, 카페인, 음주 등 생활습관을 점검해줘.

너무 빡센 계획을 제안하지 말고,
사용자가 오늘 바로 할 수 있는 작은 행동 1~3개를 제안해줘.
"""
}


def get_system_prompt(selected_mode):
    return base_system_prompt + "\n\n" + mode_prompts[selected_mode]


# =========================
# OpenAI 응답 스트리밍 함수
# =========================

def stream_openai_response(client, messages):
    """
    OpenAI 응답을 Streamlit 화면에 한 글자씩 흘려보내기 위한 generator.
    """
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


# =========================
# API 키 확인
# =========================

if not openai_api_key:
    st.info("왼쪽 사이드바에 OpenAI API 키를 입력하면 챗봇을 사용할 수 있어요.", icon="🗝️")
    st.stop()

client = OpenAI(api_key=openai_api_key)


# =========================
# 세션 상태 초기화
# =========================

if "messages" not in st.session_state:
    st.session_state.messages = []


# =========================
# 기존 대화 출력
# =========================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# =========================
# 사용자 입력 처리
# =========================

placeholder_text = {
    "증상 정리": "예: 어제부터 목이 아프고 열이 조금 나요.",
    "병원 방문 가이드": "예: 배가 너무 아픈데 병원에 가야 할까요?",
    "건강검진 결과 설명": "예: LDL 콜레스테롤이 150이라고 나왔어요.",
    "생활습관 코칭": "예: 요즘 잠을 잘 못 자고 너무 피곤해요.",
}

prompt = st.chat_input(placeholder_text[mode])

if prompt:
    # 사용자 메시지 저장
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    # 사용자 메시지 화면 출력
    with st.chat_message("user"):
        st.markdown(prompt)

    # 응급 키워드 감지 시 먼저 경고 표시
    if check_emergency(prompt):
        st.error(
            "입력하신 내용에는 응급 상황일 수 있는 표현이 포함되어 있어요. "
            "증상이 실제로 심하거나 갑작스럽다면 즉시 119 또는 가까운 응급실에 연락하세요. "
            "저는 진단을 할 수 없기 때문에, 안전을 위해 의료진의 도움을 받는 것이 가장 중요합니다."
        )

    # OpenAI에 보낼 메시지 구성
    api_messages = [
        {"role": "system", "content": get_system_prompt(mode)}
    ]

    for m in st.session_state.messages:
        api_messages.append(
            {"role": m["role"], "content": m["content"]}
        )

    # assistant 응답 생성
    with st.chat_message("assistant"):
        response = st.write_stream(
            stream_openai_response(client, api_messages)
        )

    # assistant 응답 저장
    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )
