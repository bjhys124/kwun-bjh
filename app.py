import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
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
    non_deductible_expenses = df[df['분류'] == '경조사비']['금액'].sum()
    if non_deductible_expenses > 0:
        adjustments.append(f"경조사비: {non_deductible_expenses:,}원을 세법상 불인정 비용으로 조정하여 제외했습니다.")
        df = df[df['분류'] != '경조사비']
    
    adjusted_profit = calculate_net_profit(df)
    return adjusted_profit, adjustments, df  # 세무 조정된 장부 반환

# 세액 계산기 (소득공제 및 조세특례제도 적용)
def calculate_tax_with_adjustments(df, adjusted_profit):
    basic_deduction = 1500000  # 기본공제 (1,500,000원)
    medical_deduction = 1000000  # 의료비 공제 (예시 값)
    pension_deduction = 500000  # 연금보험료 공제 (예시 값)
    children_deduction = 0  # 자녀 세액 공제 (예시 값)
    
    # 총 소득공제 금액 계산
    total_deductions = basic_deduction + medical_deduction + pension_deduction + children_deduction
    
    taxable_income = max(adjusted_profit - total_deductions, 0)  # 과세표준
    
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
    return final_tax_due

# 세액 최적화 (세액 공제 및 조정)
def apply_tax_relief(df, adjusted_profit):
    basic_deduction = 1500000  # 기본공제
    medical_deduction = 1000000  # 의료비 공제 (예시 값)
    pension_deduction = 500000  # 연금보험료 공제 (예시 값)
    children_deduction = 0  # 자녀 세액 공제 (예시 값)
    
    # 총 소득공제 금액 계산
    total_deductions = basic_deduction + medical_deduction + pension_deduction + children_deduction
    taxable_income = max(adjusted_profit - total_deductions, 0)
    
    # 세액 공제 (자녀 세액 공제 등)
    tax_credits = 0  # 자녀 세액 공제 등 추가
    
    # 최종 납부 세액 계산
    final_tax_due = max(taxable_income * 0.24 - 5220000 - tax_credits, 0)  # 24% 세율 예시
    return final_tax_due

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
    
    # df 내용 출력 (디버깅용)
    st.write(df)  # 데이터가 제대로 로드됐는지 확인
    
    # 데이터 유효성 체크
    try:
        vat, income_tax = calculate_tax(df)
        st.subheader("📊 세금 계산")
        st.write(f"📌 예상 부가세: 약 {remove_decimal(vat):,}원")
        st.write(f"💰 예상 종합소득세: 약 {remove_decimal(income_tax):,}원")
    except Exception as e:
        st.error(f"세금 계산 중 오류 발생: {str(e)}")

    # 개인정보 (인적 공제 항목) 묻기
    st.subheader("👨‍👩‍👧‍👦 개인정보 입력")
    num_children = st.number_input("자녀 수를 입력하세요.", min_value=0, max_value=10, step=1)
    parent_age = st.number_input("부모님 중 60세 이상의 분 수를 입력하세요.", min_value=0, max_value=10, step=1)

    # 입력된 인적 공제 항목 반영
    children_deduction = num_children * 1500000  # 자녀 세액 공제 (예시: 150만 원씩)
    parent_deduction = parent_age * 1000000  # 부모님 공제 (예시: 100만 원씩)

    # 세액 계산 (인적 공제 적용 후)
    adjusted_profit, adjustments, adjusted_df = tax_adjustment(df)
    final_tax_due = apply_tax_relief(adjusted_df, adjusted_profit)
    
    # 세금 재계산
    final_tax_due_with_deductions = final_tax_due - (children_deduction + parent_deduction)
    final_tax_due_with_deductions = max(final_tax_due_with_deductions, 0)  # 세액이 음수가 되지 않도록 처리

    # 결과 출력
    st.subheader("📊 최종 납부 세액")
    st.write(f"최종 납부 세액: 약 {remove_decimal(final_tax_due_with_deductions):,}원")

    # GPT 피드백
    gpt_summary_prompt = "다음은 자영업자의 장부 요약입니다:\n"
    summary = summarize_ledger(adjusted_df)  # 요약 함수에서 컬럼 이름을 명확히 지정
    for _, row in summary.iterrows():
        gpt_summary_prompt += f"- {row['항목']}: {int(row['총액']):,}원\n"  # 총액에 접근할 때 정확한 컬럼 이름 사용

    gpt_summary_prompt += f"\n📌 예상 부가세: 약 {remove_decimal(vat):,}원\n"
    gpt_summary_prompt += f"💰 예상 종합소득세: 약 {remove_decimal(income_tax):,}원\n"
    gpt_summary_prompt += f"\n💸 최종 납부 세액: 약 {remove_decimal(final_tax_due_with_deductions):,}원"

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
