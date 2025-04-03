import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
from fpdf import FPDF

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

# CSV 파일 파싱 함수
def parse_csv_to_dataframe(uploaded_file):
    return pd.read_csv(uploaded_file)

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

# GPT 기반 분류 해석 함수
def classify_category_with_gpt(category_name):
    system_msg = """
    너는 계정과목 분류 전문가야. 사용자가 입력한 분류명이 어떤 회계 분류에 속하는지 추론해서 적절한 이름의 대표 분류로 제안해줘.
    기존 회계 분류명 외에도 사용자 업종에 맞게 창의적이고 실무적인 계정과목명을 제안할 수 있어. 너무 일반적이거나 모호하지 않게 작성하고, 분류명과 추천명을 한 줄씩 매핑해줘.
    """
    user_msg = f"'{category_name}' 이 항목은 어떤 계정과목으로 분류될 수 있을까?"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

# 경고 생성 함수
def generate_warnings(df):
    warnings = []
    monthly_income = df[df['분류'] == '매출']['금액'].sum()
    if monthly_income == 0:
        warnings.append("⚠ 매출 정보가 없습니다. 매출 데이터를 반드시 입력해주세요.")
    
    expenses = df[df['분류'] != '매출'].groupby('분류')['금액'].sum()

    if len(expenses) == 0:
        warnings.append("⚠ 지출 항목이 없습니다. 지출 데이터를 입력해주세요.")

    return warnings

# PDF 저장 함수
def save_summary_to_pdf(summary, vat, income_tax, feedback):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="장부 요약 리포트", ln=True, align='C')

    pdf.ln(5)
    for _, row in summary.iterrows():
        pdf.cell(200, 10, txt=f"- {row['항목']}: {int(row['총액']):,}원", ln=True)

    pdf.ln(5)
    pdf.cell(200, 10, txt=f"📌 예상 부가세: 약 {vat:,}원", ln=True)
    pdf.cell(200, 10, txt=f"💰 예상 종합소득세: 약 {income_tax:,}원", ln=True)

    pdf.ln(5)
    pdf.multi_cell(0, 10, txt="GPT 세무사 피드백:\n" + feedback)

    filepath = "세무_요약_리포트.pdf"
    pdf.output(filepath)
    return filepath

# Streamlit 실행
st.title("🧾 세무 GPT 챗봇 + 자동 경고 + 세금 계산 + 리포트 저장")

uploaded_file = st.file_uploader("장부 파일을 업로드하세요 (.txt 또는 .csv)", type=["txt", "csv"])
question = st.text_input("세무 관련 질문을 입력하세요 (예: 이번 달 지출은 적절한가요?)")

if uploaded_file:
    if uploaded_file.type == "text/csv":
        df = parse_csv_to_dataframe(uploaded_file)
    else:
        df = parse_text_to_dataframe(uploaded_file)

    st.subheader("📋 원본 장부 데이터")
    st.dataframe(df)

    with st.spinner("📡 GPT 분석 중..."):
        warnings = generate_warnings(df)
        summary = summarize_ledger(df)
        vat, income_tax = calculate_tax(df)

        gpt_summary_prompt = "다음은 자영업자의 장부 요약입니다:\n"
        for _, row in summary.iterrows():
            gpt_summary_prompt += f"- {row['항목']}: {int(row['총액']):,}원\n"
        gpt_summary_prompt += f"\n예상 부가세: 약 {vat:,}원\n"
        gpt_summary_prompt += f"예상 종합소득세: 약 {income_tax:,}원"

        gpt_feedback = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 전문 세무사 AI야. 지출 요약과 예상 세금 결과를 바탕으로 개선 방향과 리스크를 알려줘."},
                {"role": "user", "content": gpt_summary_prompt}
            ],
            temperature=0.5
        ).choices[0].message.content.strip()

    if warnings:
        st.subheader("⚠ 자동 경고 메시지")
        for w in warnings:
            st.write(w)
    else:
        st.success("✅ 위험 경고는 없습니다! 지출이 적절해요.")

    st.subheader("📊 세금 요약")
    st.write(f"📌 예상 부가세: 약 {vat:,}원")
    st.write(f"💰 예상 종합소득세: 약 {income_tax:,}원")

    st.subheader("🧠 GPT 세무사 피드백")
    st.write(gpt_feedback)  # 이 줄을 이제 이 블록 안에 넣음

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
