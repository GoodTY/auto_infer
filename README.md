# auto_infer


실행

---
프로젝트 긁어오기
---
github_trend_cloner.py
이거 github trend에서 긁어오는 겁니다. 
내부 코드 보면 수정할 수 있을 겁니다 star수 fork 수 등등

---
infer 분석
---
infer_analyzer.py
이건 프로젝트 하나 단위로 하는겁니다.
ex.
// python3 infer_analyzer.py 프로젝트 저장 위치
// python3 infer_analyzer.py ./open-source/langchain4j

###
batch_infer_analyzer.py
이건 프로젝트 뭉탱이 있는거 한꺼번에 infer 돌릴 수 있도록 해놨어요
ex.
// python3 batch_infer_analyzer.py 프로젝트 디렉터리 모음 저장 위치
// python3 batch_infer_analyzer.py ./github-trends/java

---
예외 환경 설정
---

upgrade_maven.py
이건 wsl환경에서 maven 부족하면 하는건데 infer_analyzer.py에서 쓰라고하면 쓰면 됩니다. 제 환경 기준이라 ㅎㅎㅎ
---

---
csv 파일 생성
---

generate_bug_report.py
위에서 분석한 infer-out 파일에 있는 json 파일 분석해서
csv 파일로 만들어줘요
method 코드도 다 긁어 오도록 했으니 대충 확인은 했는데 아마 될껄요?
// python3 generate_bug_report.py  ./github-trends/java