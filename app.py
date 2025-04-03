import streamlit as st
import pandas as pd
import os
from io import StringIO
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
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
        warnings.append("⚠ 매출 정보가 없습니다. 매출 데이터를 반드시 입력해주세요.")

    expenses = df[df['분류'] != '매출'].groupby('분류')['금액'].sum()
    thresholds = {
        '원재료비': (0.3, 0.5),
        '인건비': 0.3,
        '광고선전비': 0.1,
        '소모품비': 0.05,
    }

    for category, threshold in thresholds.items():
        if category in expenses:
            expense_amount = expenses[category]
            ratio = expense_amount / monthly_income
            if ratio < threshold[0]:
                warnings.append(f"⚠ {category} 비중이 {ratio:.1%}로 너무 낮습니다.")
            elif ratio > threshold[1]:
                warnings.append(f"⚠ {category} 비중이 {ratio:.1%}로 높습니다.")

    return warnings

# 월 평균 매출 계산
def calculate_monthly_avg_income(df):
    total_income = df[df['분류'] == '매출']['금액'].sum()
    months = df
