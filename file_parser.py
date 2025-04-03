import openai

# GPT를 이용한 분류 처리 함수
def classify_using_gpt(data_list):
    prompt = "다음은 자영업자의 장부 데이터입니다. 각 항목에 대해 적절한 회계 분류를 제시해주세요. '금액'에 대한 정보를 통해 분류를 예측해주세요.\n\n"
    for entry in data_list:
        prompt += f"날짜: {entry['날짜']}, 내용: {entry['내용']}, 금액: {entry['금액']}\n"

    prompt += "\n위 데이터를 기반으로 각 항목에 대한 적절한 분류를 제시해주세요."

    # OpenAI GPT-3.5 Turbo API 호출 (Chat API 사용)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "너는 회계 전문가야. 주어진 데이터를 통해 적절한 회계 분류를 제공해야 해."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    # GPT 응답에서 분류된 데이터를 추출하여 반환
    return response.choices[0].message['content'].strip()

# 텍스트 파일 파싱 및 GPT로 분류 요청
def parse_text_to_dataframe(uploaded_file):
    data = []
    for line in uploaded_file.getvalue().decode("utf-8").splitlines():
        parts = [x.strip() for x in line.strip().split("|")]
        if len(parts) == 4:
            date, desc, amount, category = parts
            data.append({"날짜": date, "내용": desc, "금액": amount})

    # GPT로 자동 분류 요청
    classified_data = classify_using_gpt(data)
    
    # 반환된 분류 정보를 데이터에 추가
    for i, entry in enumerate(data):
        entry["분류"] = classified_data[i]  # GPT가 반환한 분류값을 추가
    
    return pd.DataFrame(data)

# CSV 파싱 (추가된 기능)
def parse_csv_to_dataframe(uploaded_file):
    import pandas as pd
    df = pd.read_csv(uploaded_file)
    
    # GPT 분류 수행
    df['분류'] = df.apply(lambda row: classify_using_gpt([row]), axis=1)
    return df
