def answer_with_feedback(question, df):
    try:
        # 기존 코드
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
        
        # GPT 호출
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.5
        )
        return response.choices[0].message.content

    except Exception as e:
        st.error(f"API 호출 중 오류가 발생했습니다: {str(e)}")
        return "GPT 호출에 실패했습니다. 다시 시도해 주세요."
