import pandas as pd
import openai
import os
from dotenv import load_dotenv

# 1. 환경 변수에서 API 키 불러오기
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 2. 텍스트 파일 파싱 함수 (메모장)
def parse_text_to_dataframe(txt_path):
    data = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = [x.strip() for x in line.strip().split("|")]
            if len(parts) == 4:
                date, desc, amount, category = parts
                data.append({"날짜": date, "내용": desc, "금액": int(amount), "분류": category})
    return pd.DataFrame(data)

# 3. 장부 요약 함수
def summarize_ledger(df):
    summary = df.groupby("분류")["금액"].sum().reset_index()
    summary.columns = ["항목", "총액"]
    return summary

# 4. 예상 세금 계산기
def calculate_tax(df):
    total_income = df[df['분류'] == '매출']['금액'].sum()
    business_expense = df[df['분류'] != '매출']
    total_expense = business_expense['금액'].sum()

    # 부가세 = (매출 - 매입) * 10%
    vat_estimate = max((total_income - total_expense) * 0.1, 0)

    # 종합소득세 = (소득금액 - 기본공제) * 단순 세율 (기본공제 150만원, 세율 6%)
    income_tax_base = max((total_income - total_expense - 1500000), 0)
    income_tax_estimate = income_tax_base * 0.06

    return int(vat_estimate), int(income_tax_estimate)

# 5. 경고 메시지 생성 함수
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
                    warnings.append(f"⚠ {category} 비중이 {ratio:.1%}로 너무 낮습니다. 과소 신고 리스크 있음.")
                elif ratio > max_ratio:
                    warnings.append(f"⚠ {category} 비중이 {ratio:.1%}로 높습니다. 원가 절감 필요.")

            elif category == '경조사비':
                if expense_amount > 200000:
                    warnings.append(f"⚠ 경조사비가 건당 20만원을 초과했습니다. 경비 인정이 어렵습니다.")

            elif ratio > threshold:
                warnings.append(f"⚠ {category} 지출이 매출 대비 {ratio:.1%}로 과다합니다. 관리 필요.")

    return warnings

# 6. 월 평균 매출 계산 함수
def calculate_monthly_avg_income(df):
    total_income = df[df['분류'] == '매출']['금액'].sum()
    months = df['날짜'].apply(lambda x: x[:7]).nunique()
    if months == 0:
        return 0
    return total_income // months

# 7. GPT 분석 + 세금 설명
def explain_ledger_summary(summary_df, vat, income_tax, monthly_avg_income):
    content = "다음은 자영업자의 월별 지출 요약입니다:\n"
    for _, row in summary_df.iterrows():
        content += f"- {row['항목']}: {int(row['총액'])}원\n"

    content += f"\n월 평균 매출액: 약 {monthly_avg_income:,}원\n"
    content += f"예상 부가세: 약 {vat:,}원\n"
    content += f"예상 종합소득세: 약 {income_tax:,}원"

    messages = [
        {"role": "system", "content": "너는 전문 세무사 수준의 AI 컨설턴트야. 자영업자의 지출 요약을 바탕으로:\n- 과다 지출 항목 경고\n- 효율적인 절세 전략 제안\n- 항목별 개선 방향 설명\n- 예상 부가세와 종합소득세를 구체적으로 안내\n\n※ 세무사 없이도 스스로 판단할 수 있도록 명확하고 단호하게 말해줘."},
        {"role": "user", "content": content}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.5
    )
    return response['choices'][0]['message']['content']

# 메인 실행 코드
if __name__ == "__main__":
    txt_path = input("분석할 메모장(txt) 파일명을 입력하세요: ")
    df = parse_text_to_dataframe(txt_path)
    summary = summarize_ledger(df)
    vat, income_tax = calculate_tax(df)
    monthly_avg_income = calculate_monthly_avg_income(df)
    warnings = generate_warnings(df)

    if warnings:
        print("\n🚨 [AI 경고 시스템] 자동 경고 메시지:")
        for warning in warnings:
            print(warning)
    else:
        print("\n✅ 특별한 경고사항이 없습니다.")

    explanation = explain_ledger_summary(summary, vat, income_tax, monthly_avg_income)

    print("\n📊 요약 결과:")
    print(summary)
    print(f"\n📌 월 평균 매출액: 약 {monthly_avg_income:,}원")
    print(f"💸 예상 부가세: 약 {vat:,}원")
    print(f"💰 예상 종합소득세: 약 {income_tax:,}원")

    print("\n🤖 GPT 분석 & 피드백:")
    print(explanation)
