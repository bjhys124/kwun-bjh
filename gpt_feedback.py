def get_gpt_feedback(summary, vat, income_tax):
    feedback_prompt = "다음은 자영업자의 장부 요약입니다. 이 정보를 바탕으로 피드백을 제공해주세요:\n\n"
    
    for _, row in summary.iterrows():
        feedback_prompt += f"- {row['항목']}: {int(row['총액']):,}원\n"
    
    feedback_prompt += f"\n예상 부가세: 약 {vat:,}원\n"
    feedback_prompt += f"예상 종합소득세: 약 {income_tax:,}원\n"
    
    response = openai.Completion.create(
        model="gpt-3.5-turbo",
        prompt=feedback_prompt,
        temperature=0.5,
        max_tokens=150
    )
    return response.choices[0].text.strip()
