import streamlit as st
from file_parser import parse_text_to_dataframe, parse_csv_to_dataframe
from tax_calculator import calculate_tax
from warning_generator import generate_warnings
from gpt_feedback import get_gpt_feedback

# Streamlit UI 설정
st.title("세무 GPT 챗봇 + 자동 경고 + 세금 계산 + 리포트 저장")

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
        summary = df.groupby("분류")["금액"].sum().reset_index()
        vat, income_tax = calculate_tax(df)

        gpt_feedback = get_gpt_feedback(summary, vat, income_tax)

    # 경고 메시지 출력
    if warnings:
        st.subheader("⚠ 자동 경고 메시지")
        for w in warnings:
            st.write(w)
    else:
        st.success("✅ 위험 경고는 없습니다! 지출이 적절해요.")

    # 세금 계산 결과 출력
    st.subheader("📊 세금 요약")
    st.write(f"📌 예상 부가세: 약 {vat:,}원")
    st.write(f"💰 예상 종합소득세: 약 {income_tax:,}원")

    # GPT 피드백 출력
    st.subheader("🧠 GPT 세무사 피드백")
    st.write(gpt_feedback)

    # 세무 관련 질문 응답 처리
    if question:
        user_question_prompt = f"사용자 질문: {question}"

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
