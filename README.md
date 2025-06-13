# auto_infer


# 실행

---
프로젝트 긁어오기
---
github_trend_cloner.py <br><br>
이거 github trend에서 긁어오는 겁니다. <br>
내부 코드 보면 수정할 수 있을 겁니다 star수 fork 수 등등<br>
ex.<br>
// python3 github_trend_cloner.py

---
infer 분석
---
infer_analyzer.py<br><br>
이건 프로젝트 하나 단위로 하는겁니다.<br>
ex.<br>
// python3 infer_analyzer.py 프로젝트 저장 위치<br>
// python3 infer_analyzer.py ./open-source/langchain4j<br>

batch_infer_analyzer.py<br><br>
이건 프로젝트 뭉탱이 있는거 한꺼번에 infer 돌릴 수 있도록 해놨어요<br>
ex.<br>
// python3 batch_infer_analyzer.py 프로젝트 디렉터리 모음 저장 위치<br>
// python3 batch_infer_analyzer.py ./github-trends/java<br>

---
csv 파일 생성
---

generate_bug_report.py<br><br>
위에서 분석한 infer-out 파일에 있는 json 파일 분석해서<br>
csv 파일로 만들어줘요<br>
method 코드도 다 긁어 오도록 했으니 대충 확인은 했는데 아마 될껄요?<br>
ex.<br>
// python3 generate_bug_report.py  프로젝트 뭉텅이 있는 디렉터리 위치 최종으로 원하는 파일 저장 위치 <br>
// python3 generate_bug_report.py ./github-trends/java ./total_report


---
예외 환경 설정
---

upgrade_maven.py <br><br>
이건 wsl환경에서 maven 부족하면 하는건데 infer_analyzer.py에서 쓰라고하면 쓰면 됩니다.<br>
제 환경 기준이라 ㅎㅎㅎ<br>
