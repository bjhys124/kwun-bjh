import streamlit as st
import pandas as pd
import os
from io import StringIO
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import math

# 환경 변수 로드
dotenv_path = ".env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 텍스트 파일 파싱 함수 (매출 및 비용 데이터)
def parse_text_to_dataframe(uploaded_file):
    data = []
    for line in uploaded_file.getvalue().decode("utf-8").splitlines():
        parts = [x.strip() for x in line.strip().split("|")]
        if len(parts) == 4:
            date, desc, amount, category = parts
            data.append({"날짜": date, "내용": desc, "금액": int(amount), "분류": category})
    return pd.DataFrame(data)

# 매출 순수익 계산 (비용 제외)
def calculate_net_profit(df):
    total_income = df[df['분류'] == '매출']['금액'].sum()  # 매출 합계
    total_expense = df[df['분류'] != '매출']['금액'].sum()  # 비용 합계
    net_profit = total_income - total_expense  # 순수익 = 매출 - 비용
    return net_profit

# 세무 조정 (세법에 따른 조정)
def tax_adjustment(df):
    adjustments = []  # 세무 조정 항목 저장
    
    # 예시: '법인세 조정' - 세법상 불인정 비용을 제외
    # 예시로 '경조사비'는 세법상 인정되지 않으므로 제외
    non_deductible_expenses = df[df['분류'] == '경조사비']['금액'].sum()
    if non_deductible_expenses > 0:
        adjustments.append(f"경조사비: {non_deductible_expenses:,}원을 세법상 불인정 비용으로 조정하여 제외했습니다.")
        # 경조사비를 순수익에서 제외
        df = df[df['분류'] != '경조사비']
    
    # 세무 조정된 순수익 계산
    adjusted_profit = calculate_net_profit(df)
    return adjusted_profit, adjustments, df  # 세무 조정된 장부 반환

# 세액 계산기 (소득공제 및 조세특례제도 적용)
def calculate_tax_with_adjustments(df, adjusted_profit):
    # 기본 공제액 예시 (이 부분은 실제 값에 맞게 설정 필요)
    basic_deduction = 1500000  # 기본공제 (1,500,000원)
    
    # 예시 소득공제 항목 추가 (의료비, 연금보험료 등)
    medical_deduction = 0  # 의료비 공제 (예시)
    pension_deduction = 0  # 연금보험료 공제 (예시)
    children_deduction = 0  # 자녀 세액 공제 (예시)
    
    # 총 소득공제 금액 계산
    total_deductions = basic_deduction + medical_deduction + pension_deduction + children_deduction
    
    # 과세표준 계산
    taxable_income = max(adjusted_profit - total_deductions, 0)
    
    # 과세표준에 따른 소득세율 적용 (단순화된 예시)
    if taxable_income <= 12000000:
        income_tax = taxable_income * 0.06
    elif taxable_income <= 46000000:
        income_tax = taxable_income * 0.15 - 1080000
    else:
        income_tax = taxable_income * 0.24 - 5220000
    
    # 세액 공제 (예: 자녀 세액 공제)
    tax_credits = 0  # 자녀 세액 공제 등 추가
    
    # 최종 납부 세액 계산
    final_tax_due = max(income_tax - tax_credits, 0)
    return final_tax_due, income_tax, taxable_income, total_deductions

# 요약 함수
def summarize_ledger(df):
    summary = df.groupby("분류")["금액"].sum().reset_index()
    summary.columns = ["항목", "총액"]  # 컬럼 이름을 명확히 지정
    return summary

# 세금 계산기
def calculate_tax(df):
    total_income = df[df['분류'] == '매출']['금액'].sum()
    total_expense = df[df['분류'] != '매출']['금액'].sum()
    vat_estimate = max((total_income - total_expense) * 0.1, 0)
    income_tax_base = max((total_income - total_expense - 1500000), 0)
    income_tax_estimate = income_tax_base * 0.06
    return int(vat_estimate), int(income_tax_estimate)

# 소수점 제거 함수 (내림 처리)
def remove_decimal(value):
    return math.floor(value)

# Streamlit 실행
st.title("광운대 22학번 학부연구생 백준현 프로젝트 세무사봇")

uploaded_file = st.file_uploader("장부 파일을 업로드하세요 (.txt)", type="txt")
question = st.text_input("세무 관련 질문을 입력하세요 (예: 이번 달 지출은 적절한가요?)")
if uploaded_file:
    df = parse_text_to_dataframe(uploaded_file)
    st.subheader("📋 원본 장부 데이터")
    st.dataframe(df)
    
    # 매출 순수익 계산
    net_profit = calculate_net_profit(df)
    st.subheader("💰 매출 순수익 (비용 제외):")
    st.write(f"순수익: {remove_decimal(net_profit):,}원")  # 소수점 제거 후 출력

    # 세무 조정
    adjusted_profit, adjustments, adjusted_df = tax_adjustment(df)
    st.subheader("🧾 세무 조정 후 순수익:")
    st.write(f"조정된 순수익: {remove_decimal(adjusted_profit):,}원")  # 소수점 제거 후 출력
    
    # 세무 조정 항목 표시
    if adjustments:
        st.subheader("⚖️ 세무 조정 항목")
        for adjustment in adjustments:
            st.write(adjustment)
    
    # 최종 납부 세액 계산
    final_tax_due, income_tax, taxable_income, total_deductions = calculate_tax_with_adjustments(df, adjusted_profit)

    st.subheader("📊 세금 요약")
    st.write(f"📌 최종 납부 세액: 약 {remove_decimal(final_tax_due):,}원")  # 소수점 제거 후 출력
    st.write(f"📝 총 소득공제: 약 {remove_decimal(total_deductions):,}원")

    # GPT 피드백
    gpt_summary_prompt = "다음은 자영업자의 장부 요약입니다:\n"
    summary = summarize_ledger(adjusted_df)  # 요약 함수에서 컬럼 이름을 명확히 지정
    for _, row in summary.iterrows():
        gpt_summary_prompt += f"- {row['항목']}: {int(row['총액']):,}원\n"  # 총액에 접근할 때 정확한 컬럼 이름 사용
    gpt_feedback = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[ 
            {"role": "system", "content": "너는 전문 세무사 AI야. 지출 요약과 예상 세금 결과를 바탕으로 개선 방향과 리스크를 알려줘."},
            {"role": "user", "content": gpt_summary_prompt}
        ],
        temperature=0.5
    ).choices[0].message.content.strip()

    st.subheader("🧠 GPT 세무사 피드백")
    st.write(gpt_feedback)

    # 질문에 대한 답변
    if question:
        user_question_prompt = gpt_summary_prompt + f"\n\n사용자 질문: {question}"

        followup_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 전문 세무사 AI야. 아래 사용자의 질문에 장부 기반으로 정확히 답해줘."},
                {"role": "user", "content": user_question_prompt}
            ],
            temperature=0.5
        )

        st.subheader("💬 질문에 대한 답변")
        st.write(followup_response.choices[0].message.content.strip())
