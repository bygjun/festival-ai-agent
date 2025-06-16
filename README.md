## 실행 방법

1. 파이썬 가상환경 생성
python3 -m venv venv

2. 가상환경 활성화
source venv/bin/activate

3. 필수 패키지 설치
pip install -r requirements.txt

4. .env 파일 생성 및 OpenAI API Key 세팅  
프로젝트 루트의 `.env` 파일에 OPENAI_API_KEY 키를 넣어줍니다.

5. 앱 실행
streamlit run ui.py
