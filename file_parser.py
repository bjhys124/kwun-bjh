import openai
import os
from dotenv import load_dotenv

# 환경 변수 로드
dotenv_path = ".env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

openai.api_key = os.getenv("OPENAI_API_KEY")

# GPT 기반 분류 해석 함수
def classify_using_gpt(data_list):
    prompt = ""
    for entry in data_list:
        prompt += f"날짜: {entry['날짜']}, 내용: {entry['내용']}, 금액: {entry['금액']}\n"

    # GPT 호출
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # 최신 모델 사용
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=150
    )
    
    return response.choices[0].message['content'].strip()

# 텍스트 파일을 파싱하고 GPT를 이용하여 분류하는 함수
def parse_text_to_dataframe(uploaded_file):
    data = []
    for line in uploaded_file.getvalue().decode("utf-8").splitlines():
        parts = [x.strip() for x in line.strip().split("|")]
        if len(parts) == 4:
            date, desc, amount, category = parts
            data.append({"날짜": date, "내용": desc, "금액": int(amount), "분류": category})

    # GPT 분류 사용
    classified_data = classify_using_gpt(data)
    return classified_data
