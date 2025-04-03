from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_gpt_feedback(summary, vat, income_tax):
    gpt_summary_prompt = "다음은 자영업자의 장부 요약입니다:\n"
    for _, row in summary.iterrows():
        gpt_summary_prompt += f"- {row['항목']}: {int(row['총액']):,}원\n"
    gpt_summary_prompt += f"\n예상 부가세: 약 {vat:,}원\n"
    gpt_summary_prompt += f"예상 종합소득세: 약 {income_tax:,}원"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "너는 전문 세무사 AI야. 지출 요약과 예상 세금 결과를 바탕으로 개선 방향과 리스크를 알려줘."},
                  {"role": "user", "content": gpt_summary_prompt}],
        temperature=0.5
    )

    return response.choices[0].message.content.strip()
