import pandas as pd

# 텍스트 파일 파싱 함수
def parse_text_to_dataframe(uploaded_file):
    data = []
    for line in uploaded_file.getvalue().decode("utf-8").splitlines():
        parts = [x.strip() for x in line.strip().split("|")]
        if len(parts) == 4:
            date, desc, amount, category = parts
            data.append({"날짜": date, "내용": desc, "금액": int(amount), "분류": category})
    return pd.DataFrame(data)

# CSV 파일 파싱 함수
def parse_csv_to_dataframe(uploaded_file):
    return pd.read_csv(uploaded_file)
