1. 코드 수행 방법
cd wiki-assistant-py
.venv\Scripts\python.exe -m scripts.ingest             # 이미 데이터가 있어 생략 가능(둘 다 같은 컬렉션 공유)
.venv\Scripts\python.exe -m src.ask "GOOD과 DEFECT의 차이는 무엇인가?"
.venv\Scripts\python.exe -m src.ask "오늘 서울 날씨 어때?"   # 재시도 루프 확인용(쿼터 여유 있을 때)
