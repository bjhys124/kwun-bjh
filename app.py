import pandas as pd
import os
from io import StringIO
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from fpdf import FPDF

# 환경 변수 로드
dotenv_path = ".env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 텍스트 파일 또는 CSV, 엑셀 파일 파싱 함수
def parse_file_to_dataframe(uploaded_file):
    file_type = uploaded_file.name.split('.')[-1].lower()

    if file_type == 'txt':
        data = []
        for line in uploaded_file.getvalue().decode("utf-8").splitlines():
            parts = [x.strip() for x in line.strip().split("|")]
            if len(parts) == 4:
                date, desc, amount, category = parts
                data.append({"날짜": date, "내용": desc, "금액": int(amount), "분류": category})
        return pd.DataFrame(data)
    
    elif file_type in ['xls', 'xlsx']:
        df = pd.read_excel(uploaded_file, header=None)
        df.columns = ['날짜', '내용', '금액', '분류']  # 여기에 원하는 컬럼명을 설정
        return df
    
    elif file_type == 'csv':
        df = pd.read_csv(uploaded_file)
        if '날짜' not in df.columns or '내용' not in df.columns or '금액' not in df.columns or '분류' not in df.columns:
            df.columns = ['날짜', '내용', '금액', '분류']  # CSV 파일에서 헤더가 다를 수 있으니 여기에 맞춰 컬럼명 설정
        return df
    else:
        raise ValueError("지원하지 않는 파일 형식입니다.")

# 데이터 검증 함수 (자동 형식 맞추기)
def validate_dataframe(df):
    # 날짜 형식 변환 (날짜가 잘못된 경우 처리)
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')  # 잘못된 날짜는 NaT (Not a Time)
    
    # 금액이 숫자가 아닌 경우 처리
    df['금액'] = pd.to_numeric(df['금액'], errors='coerce')

    # 잘못된 데이터가 있으면 에러 메시지 출력
    if df['날짜'].isnull().any():
        st.warning("날짜 형식이 잘못된 항목이 있습니다.")
    
    if df['금액'].isnull().any():
        st.warning("금액 형식이 잘못된 항목이 있습니다.")
    
    return df

# 나머지 코드 (요약, 세금 계산, GPT 분석 등) 그대로 유지

# Streamlit 실행
st.title("🧾 세무 GPT 챗봇 + 자동 경고 + 세금 계산 + 리포트 저장")

uploaded_file = st.file_uploader("장부 파일을 업로드하세요 (.txt, .xls, .xlsx, .csv)", type=["txt", "xls", "xlsx", "csv"])
question = st.text_input("세무 관련 질문을 입력하세요 (예: 이번 달 지출은 적절한가요?)")

# 파일 업로드가 있으면 처리
if uploaded_file:
    df = parse_file_to_dataframe(uploaded_file)
    df = validate_dataframe(df)  # 데이터 검증 추가
    st.subheader("📋 원본 장부 데이터")
    st.dataframe(df)

if question:
    # 질문만 있을 경우 처리
    gpt_summary_prompt = f"사용자의 질문: {question}"

    followup_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "너는 전문 세무사 AI야. 아래 사용자의 질문에 장부 기반으로 정확히 답해줘."},
            {"role": "user", "content": gpt_summary_prompt}
        ],
        temperature=0.5
    )

    st.subheader("💬 질문에 대한 답변")
    st.write(followup_response.choices[0].message.content.strip())
