import streamlit as st
import pandas as pd
import openai
import os
from io import StringIO
from dotenv import load_dotenv

# 환경 변수 로드
dotenv_path = ".env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
openai.api_key = os.getenv("OPENAI_API_KEY")

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

# GPT 분석 함수
def explain_ledger_summary(summary_df, vat, income_tax, monthly_avg_income):
    content = "다음은 자영업자의 월별 지출 요약입니다:\n"
    for _, row in summary_df.iterrows():
        content += f"- {row['항목']}: {int(row['총액'])}원\n"

    content += f"\n월 평균 매출액: 약 {monthly_avg_income:,}원\n"
    content += f"예상 부가세: 약 {vat:,}원\n"
    content += f"예상 종합소득세: 약 {income_tax:,}원"

    messages = [
        {"role": "system", "content": "너는 전문 세무사 수준의 AI 컨설턴트야."},
        {"role": "user", "content": content}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.5
    )
    return response['choices'][0]['message']['content']

# Streamlit UI
st.title("📊 세무사 챗봇: 자영업자 장부 분석기")

uploaded_file = st.file_uploader(".txt 형식의 장부 파일을 업로드하세요", type="txt")

if uploaded_file is not None:
    df = parse_text_to_dataframe(uploaded_file)
    st.subheader("📋 원본 장부 데이터")
    st.dataframe(df)

    summary = summarize_ledger(df)
    vat, income_tax = calculate_tax(df)
    monthly_avg_income = calculate_monthly_avg_income(df)
    warnings = generate_warnings(df)

    st.subheader("📌 분류별 지출 요약")
    st.dataframe(summary)

    st.subheader("💸 예상 세금")
    st.write(f"- 부가가치세(VAT): **{vat:,}원**")
    st.write(f"- 종합소득세: **{income_tax:,}원**")
    st.write(f"- 월 평균 매출: **{monthly_avg_income:,}원**")

    if warnings:
        st.subheader("🚨 자동 경고 메시지")
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("경고 사항 없음. 건전한 지출 구조입니다!")

    st.subheader("🤖 GPT 분석 & 절세 피드백")
    with st.spinner("GPT 피드백 생성 중..."):
        explanation = explain_ledger_summary(summary, vat, income_tax, monthly_avg_income)
        st.write(explanation)
