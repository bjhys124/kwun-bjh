def generate_warnings(df):
    warnings = []
    monthly_income = df[df['분류'] == '매출']['금액'].sum()
    if monthly_income == 0:
        warnings.append("⚠ 매출 정보가 없습니다. 매출 데이터를 반드시 입력해주세요.")
    
    expenses = df[df['분류'] != '매출'].groupby('분류')['금액'].sum()

    if len(expenses) == 0:
        warnings.append("⚠ 지출 항목이 없습니다. 지출 데이터를 입력해주세요.")

    return warnings
