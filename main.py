# main.py
# ---------------------------------------------------------
# Solar API(solar-open2)를 사용하는 스트림릿 AI 채팅앱
# 스트림릿 클라우드 배포용
# ---------------------------------------------------------

import streamlit as st
from openai import OpenAI

# -----------------------------
# 1) 기본 화면 설정
# -----------------------------
st.set_page_config(page_title="AI 데이터 분석 선생님", page_icon="🧑‍🏫")
st.title("🧑‍🏫 AI 데이터 분석 선생님")

# -----------------------------
# 2) Solar API 클라이언트 만들기
#    - API 키는 코드에 직접 쓰지 않고,
#      스트림릿의 "비밀 금고(secrets)"에서 불러온다.
#    - 스트림릿 클라우드에서는 앱 설정 > Secrets 에
#      SOLAR_API_KEY = "여기에_실제_키" 형태로 등록하면 된다.
# -----------------------------
try:
    api_key = st.secrets["SOLAR_API_KEY"]
except Exception:
    # secrets에 키가 아예 없을 때를 대비한 안전장치
    st.error("⚠️ SOLAR_API_KEY가 설정되어 있지 않아요. 스트림릿 클라우드의 Secrets 설정을 확인해 주세요.")
    st.stop()

# openai 라이브러리를 그대로 쓰되, 주소만 Solar API 주소로 바꿔준다.
client = OpenAI(
    api_key=api_key,
    base_url="https://api.upstage.ai/v1",
)

# -----------------------------
# 3) AI의 성격(시스템 프롬프트) 정하기
#    - 대화 맨 앞에 한 번만 넣어주는 "역할 설명" 메시지
# -----------------------------
SYSTEM_PROMPT = "너는 따뜻하고 친절한 데이터 분석 선생님이야. 반드시 순수 한국어로만 답해."

# -----------------------------
# 4) 대화 기록을 세션에 저장하기
#    - st.session_state는 사용자가 페이지를 새로고침하지 않는 한
#      값을 계속 기억해주는 저장 공간이다.
#    - 여기에 지금까지 주고받은 대화 내용을 리스트로 쌓아둔다.
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # 예: [{"role": "user", "content": "..."}, ...]

# -----------------------------
# 5) 지금까지의 대화를 화면에 말풍선으로 그려주기
#    - system 메시지는 사용자에게 보여줄 필요가 없으므로 화면 표시에서 제외
# -----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------
# 6) 사용자가 채팅 입력창에 메시지를 보내면 실행되는 부분
# -----------------------------
user_input = st.chat_input("궁금한 걸 물어보세요!")

if user_input:
    # 6-1) 사용자가 보낸 메시지를 화면에 먼저 보여주고, 기록에도 저장
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 6-2) AI에게 보낼 전체 메시지 묶음을 만든다.
    #      (시스템 프롬프트 + 지금까지의 대화 전체 = 이전 대화를 기억하며 이어감)
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages

    # 6-3) AI의 답변을 말풍선으로 보여주면서, 실시간 스트리밍으로 글자를 채워나간다.
    with st.chat_message("assistant"):
        placeholder = st.empty()  # 답변 글자가 실시간으로 갱신될 자리
        full_reply = ""           # 지금까지 받은 답변 글자를 계속 이어 붙일 변수

        try:
            # stream=True 로 설정하면, 답변이 통째로 오지 않고
            # 조금씩 나뉘어서(토큰 단위로) 실시간으로 도착한다.
            stream = client.chat.completions.create(
                model="solar-open2",
                messages=api_messages,
                stream=True,
                # temperature가 아니라 reasoning_effort로 "생각(추론)"의 정도를 조절한다.
                # 'none'으로 주면 깊게 생각하지 않고 빠르게 답을 낸다.
                reasoning_effort="none",
            )

            for chunk in stream:
                # chunk 안에 글자 조각(delta)이 들어있으면 이어 붙여서 화면을 갱신
                delta = chunk.choices[0].delta.content
                if delta:
                    full_reply += delta
                    placeholder.markdown(full_reply + "▌")  # 커서 느낌을 위한 막대기

            # 스트리밍이 끝나면 마지막 커서(▌)를 떼고 최종 답변만 표시
            placeholder.markdown(full_reply)

            # 6-4) 완성된 AI 답변을 대화 기록에 저장해서 다음 질문에도 이어지게 함
            st.session_state.messages.append({"role": "assistant", "content": full_reply})

        except Exception:
            # 6-5) API 호출이 실패했을 때, 에러 메시지를 그대로 보여주지 않고
            #      한국어로 친절하게 안내한다.
            friendly_error = (
                "😥 죄송해요, 지금은 답변을 가져오지 못했어요.\n\n"
                "인터넷 연결 상태나 API 키 설정을 확인한 뒤 잠시 후 다시 시도해 주세요."
            )
            placeholder.markdown(friendly_error)
            # 실패한 답변은 대화 기록에 남기지 않아서, 다음 질문에 혼선이 없도록 한다.
