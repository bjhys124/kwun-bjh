def generate_warnings(df):
    warnings = []
    monthly_income = df[df['분류'] == '매출']['금액'].sum()
    if monthly_income == 0:
        return ["⚠ 매출 정보가 없습니다. 매출 데이터를 반드시 입력해주세요."]

    expenses = df[df['분류'] != '매출'].groupby('분류')['금액'].sum()

    # 예시: 경고 기준 추가
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
