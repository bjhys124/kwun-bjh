import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
import math
from fpdf import FPDF
from datetime import datetime

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
            try:
                amount = int(amount.replace(",", "").replace(" ", ""))
            except ValueError:
                amount = 0
            data.append({"날짜": date, "내용": desc, "금액": amount, "분류": category})
    return pd.DataFrame(data)

# 1년치 여부 확인 함수
def check_full_year_data(df):
    try:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        month_list = df['날짜'].dt.to_period("M").drop_duplicates().sort_values()

        if len(month_list) < 12:
            return False

        for i in range(len(month_list) - 11):
            month_start = month_list[i]
            month_end = month_list[i + 11]
            if month_end.ordinal - month_start.ordinal == 11:
                return True
        return False
    except Exception as e:
        st.error(f"📛 check_full_year_data 오류: {str(e)}")
        return False



# 매출 순수익 계산
def calculate_net_profit(df):
    total_income = df[df['분류'] == '매출']['금액'].sum()
    total_expense = df[df['분류'] != '매출']['금액'].sum()
    return total_income - total_expense

# 세무 조정
def tax_adjustment(df):
    adjustments = []
    non_deductible_expenses = df[df['분류'] == '경조사비']['금액'].sum()
    if non_deductible_expenses > 0:
        adjustments.append(f"경조사비: {non_deductible_expenses:,}원을 세법상 불인정 비용으로 조정하여 제외했습니다.")
        df = df[df['분류'] != '경조사비']
    adjusted_profit = calculate_net_profit(df)
    return adjusted_profit, adjustments, df

# 세액 계산기
def calculate_tax(df):
    try:
        df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0)
        total_income = df[df['분류'] == '매출']['금액'].sum()
        total_expense = df[df['분류'] != '매출']['금액'].sum()
        vat_estimate = max((total_income - total_expense) * 0.1, 0)
        income_tax_base = max((total_income - total_expense - 1500000), 0)
        income_tax_estimate = income_tax_base * 0.06
        return vat_estimate, income_tax_estimate
    except Exception as e:
        raise ValueError(f"calculate_tax 오류: {str(e)}")

# 연간 추정 계산 함수 (부분 자료 보정)
def extrapolate_annual_estimate(df):
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    existing_months = df['날짜'].dt.month.nunique()
    if existing_months == 0:
        return 0, 0
    total_income = df[df['분류'] == '매출']['금액'].sum()
    total_expense = df[df['분류'] != '매출']['금액'].sum()
    annual_income = (total_income / existing_months) * 12
    annual_expense = (total_expense / existing_months) * 12
    return annual_income, annual_expense

# 소수점 제거
def remove_decimal(value):
    if value is None or not isinstance(value, (int, float)):
        return 0
    return math.floor(value)

# 세액 최적화
def apply_tax_relief(adjusted_df, adjusted_profit):
    basic_deduction = 1500000
    medical_deduction = 1000000
    pension_deduction = 500000
    children_deduction = 0
    total_deductions = basic_deduction + medical_deduction + pension_deduction + children_deduction
    taxable_income = max(adjusted_profit - total_deductions, 0)
    tax_credits = 0
    return max(taxable_income * 0.24 - 5220000 - tax_credits, 0)

# 요약 함수
def summarize_ledger(df):
    summary = df.groupby("분류")["금액"].sum().reset_index()
    summary.columns = ["항목", "총액"]
    return summary

# PDF 생성 함수
def export_pdf(summary_text, user_name="사용자"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"{user_name}님의 세무 요약 리포트", ln=True)
    pdf.ln(5)
    for line in summary_text.split("\n"):
        pdf.multi_cell(0, 10, txt=line)
    today = datetime.today().strftime("%Y%m%d")
    file_name = f"세무요약_{user_name}_{today}.pdf"
    output_path = os.path.join(os.getcwd(), file_name)
    pdf.output(output_path)
    return output_path, file_name

# Streamlit 실행
st.title("광운대 22학번 학부연구생 백준현 프로젝트 세무사봇")

uploaded_file = st.file_uploader("장부 파일을 업로드하세요 (.txt)", type="txt")
question = st.text_input("세무 관련 질문을 입력하세요 (예: 이번 달 지출은 적절한가요?)")

if uploaded_file:
    is_full_year = False
    vat = 0
    income_tax = 0
    df = parse_text_to_dataframe(uploaded_file)
    st.subheader("📋 원본 장부 데이터")
    st.write(df)

    try:
        is_full_year = check_full_year_data(df)
        if not is_full_year:
            st.warning("⚠️ 업로드된 데이터가 1년치가 아닙니다. 현재 출력되는 세금은 '예상치'일 수 있으며 실제 신고 시 정확하지 않을 수 있습니다.\n\n아래 계산은 현재까지의 데이터를 바탕으로 연간 추정값을 적용한 결과입니다.")
            estimated_income, estimated_expense = extrapolate_annual_estimate(df)
            df_estimated = pd.DataFrame({
                '분류': ['매출', '비용'],
                '금액': [estimated_income, estimated_expense]
            })
            vat, income_tax = calculate_tax(df_estimated)
        else:
            vat, income_tax = calculate_tax(df)

        st.subheader("📊 세금 계산")
        st.write(f"📌 예상 부가세: 약 {remove_decimal(vat):,}원")
        st.write(f"💰 예상 종합소득세: 약 {remove_decimal(income_tax):,}원")
    except Exception as e:
        st.error(f"세금 계산 중 오류 발생: {str(e)}")

    st.subheader("👨‍👩‍👧‍👦 개인정보 입력")
    num_children = st.number_input("자녀 수를 입력하세요.", min_value=0, max_value=10, step=1)
    parent_age = st.number_input("부모님 중 60세 이상의 분 수를 입력하세요.", min_value=0, max_value=10, step=1)

    children_deduction = num_children * 1500000
    parent_deduction = parent_age * 1000000

    adjusted_profit, adjustments, adjusted_df = tax_adjustment(df)
    final_tax_due = apply_tax_relief(adjusted_df, adjusted_profit)
    final_tax_due_with_deductions = max(final_tax_due - (children_deduction + parent_deduction), 0)

    st.subheader("📊 최종 납부 세액")
    st.write(f"최종 납부 세액: 약 {remove_decimal(final_tax_due_with_deductions):,}원")

    gpt_summary_prompt = "다음은 자영업자의 장부 요약입니다:\n"
    summary = summarize_ledger(adjusted_df)
    for _, row in summary.iterrows():
        gpt_summary_prompt += f"- {row['항목']}: {int(row['총액']):,}원\n"

    gpt_summary_prompt += f"\n📌 예상 부가세: 약 {remove_decimal(vat):,}원\n"
    gpt_summary_prompt += f"💰 예상 종합소득세: 약 {remove_decimal(income_tax):,}원\n"
    gpt_summary_prompt += f"\n💸 최종 납부 세액: 약 {remove_decimal(final_tax_due_with_deductions):,}원"

    if not is_full_year:
        gpt_summary_prompt += "\n\n⚠️ 참고: 이 장부는 1년치 전체 데이터가 아니므로 GPT가 제공하는 세무 피드백은 참고용입니다."

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

    # PDF 출력 + 다운로드
    st.subheader("📄 PDF 리포트 저장")
    user_name_input = st.text_input("리포트에 표시할 이름을 입력하세요 (선택)", value="사용자")
    if st.button("📄 세무 요약 PDF로 저장"):
        pdf_path, file_name = export_pdf(gpt_summary_prompt + "\n\n" + gpt_feedback, user_name_input)
        st.success("PDF가 생성되었습니다.")
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 PDF 다운로드",
                data=f,
                file_name=file_name,
                mime="application/pdf"
            )
