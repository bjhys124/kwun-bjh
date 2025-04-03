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

# 요약 함수
def summarize_ledger(df):
    summary = df.groupby("분류")["금액"].sum().reset_index()
    summary.columns = ["항목", "총액"]
    return summary

# 세금 계산기
def calculate_tax(df):
    total_income = df[df['분류'] == '매출']['금액'].sum()
    total_expense = df[df['분류'] != '매출']['금액'].sum()
    vat_estimate = max((total_income - total_expense) * 0.1, 0)
    income_tax_base = max((total_income - total_expense - 1500000), 0)
    income_tax_estimate = income_tax_base * 0.06
    return int(vat_estimate), int(income_tax_estimate)

# 경고 생성
def generate_warnings(df):
    warnings = []
    monthly_income = df[df['분류'] == '매출']['금액'].sum()
    if monthly_income == 0:
        return ["⚠ 매출 정보가 없습니다. 매출 데이터를 반드시 입력해주세요."]

    expenses = df[df['분류'] != '매출'].groupby('분류')['금액'].sum()
    thresholds = {
        '원재료비': (0.3, 0.5),
        '인건비': 0.3,
        '광고선전비': 0.1,
        '복리후생비': 0.05,
        '공과금': 0.06,
        '소모품비': 0.05,
        '지급수수료': 0.03,
        '통신비': 0.02,
        '차량유지비': 0.05,
        '수선비': 0.05,
        '보험료': 0.03,
        '운반비': 0.03,
        '대출이자': 0.05,
        '경조사비': None
    }

    for category, threshold in thresholds.items():
        if category in expenses:
            expense_amount = expenses[category]
            ratio = expense_amount / monthly_income

            if category == '원재료비':
                min_ratio, max_ratio = threshold
                if ratio < min_ratio:
                    warnings.append(f"⚠ {category} 비중이 {ratio:.1%}로 너무 낮습니다.")
                elif ratio > max_ratio:
                    warnings.append(f"⚠ {category} 비중이 {ratio:.1%}로 높습니다.")

            elif category == '경조사비':
                if expense_amount > 200000:
                    warnings.append(f"⚠ 경조사비가 건당 20만원을 초과했습니다.")

            elif ratio > threshold:
                warnings.append(f"⚠ {category} 지출이 매출 대비 {ratio:.1%}로 과다합니다.")

    return warnings

# 월 평균 매출 계산
def calculate_monthly_avg_income(df):
    total_income = df[df['분류'] == '매출']['금액'].sum()
    months = df['날짜'].apply(lambda x: x[:7]).nunique()
    return total_income // months if months else 0

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

uploaded_file = st.file_uploader(".txt 형식의 장부 파일을 업로드하세요", type="txt")

if uploaded_file is not None:
    df = parse_text_to_dataframe(uploaded_file)
    st.subheader("📋 원본 장부 데이터")
    st.dataframe(df)

    question = st.text_input("세무 질문을 입력하세요 (예: 이번 달 어땠나요?)")
    if question:
        with st.spinner("AI 세무사 답변 생성 중..."):
            answer = answer_with_feedback(question, df)
            st.subheader("🤖 챗봇 응답")
            st.write(answer)
