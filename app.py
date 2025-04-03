import streamlit as st
import pandas as pd
import os
from io import StringIO
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

# 환경 변수 로드
dotenv_path = ".env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 텍스트 파일 파싱 함수
def parse_text_to_dataframe(uploaded_file):
    data = []
    for line in uploaded_file.getvalue().decode("utf-8").splitlines():
        parts = [x.strip() for x in line.strip().split("|")]
        if len(parts) == 4:
            date, desc, amount, category = parts
            data.append({"날짜": date, "내용": desc, "금액": int(amount), "분류": category})
    return pd.DataFrame(data)

# GPT 호출 함수 (질문 + 월말 피드백 포함)
def answer_with_feedback(question, df):
    now_month = datetime.now().strftime("%Y-%m")
    last_feedback_month = st.session_state.get("last_feedback_month")

    summary = summarize_ledger(df)
    vat, income_tax = calculate_tax(df)
    monthly_avg_income = calculate_monthly_avg_income(df)
    warnings = generate_warnings(df)

    content = f"사용자 질문: {question}\n\n"
    content += "이번 달(자동 감지) 장부 분석 결과입니다:\n"
    for _, row in summary.iterrows():
        content += f"- {row['항목']}: {int(row['총액'])}원\n"
    content += f"\n월 평균 매출액: 약 {monthly_avg_income:,}원\n"
    content += f"예상 부가세: 약 {vat:,}원\n"
    content += f"예상 종합소득세: 약 {income_tax:,}원\n"
    if warnings:
        content += "\n경고 항목:\n"
        for w in warnings:
            content += f"- {w}\n"

    if last_feedback_month != now_month:
        st.session_state["last_feedback_month"] = now_month
        include_feedback = True
    else:
        include_feedback = False

    system_prompt = """
    너는 전문 세무사 AI야. 사용자의 질문에 답변을 주면서, 추가로 이번 달 요약 피드백도 포함해줘.
    단, 월말 피드백은 한 달에 한 번만 포함하고, 이후 질문에는 생략해도 돼.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.5
    )
    return response.choices[0].message.content

# Streamlit UI
st.title("🤖 세무사 GPT 챗봇 + 월말 피드백")

# 장부 파일 업로드
uploaded_file = st.file_uploader(".txt 형식의 장부 파일을 업로드하세요", type="txt")

# 질문 입력창
question = st.text_input("세무 질문을 입력하세요 (예: 이번 달 어땠나요?)")

if uploaded_file is not None:
    df = parse_text_to_dataframe(uploaded_file)
    st.subheader("📋 원본 장부 데이터")
    st.dataframe(df)

    if question:
        with st.spinner("AI 세무사 답변 생성 중..."):
            answer = answer_with_feedback(question, df)
            st.subheader("🤖 챗봇 응답")
            st.write(answer)
else:
    st.info("장부 파일을 업로드하면 GPT 분석이 가능해요. 위에 .txt 파일을 업로드해주세요!")
