"""알프레도 전용 데이터 수집기 모음.

Top3 팀 수집기(`~/01_Projects/Cripto analysis/02_데이터수집`)와는 코드·설정·DB·로그·스케줄을 분리한다.
Top3 DB(`market.db`)는 읽기 전용으로만 연결한다(쓰기·ATTACH·VACUUM 금지, 설계서 02 §path_var).
"""
