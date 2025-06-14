# auto_infer


# 실행

---
프로젝트 긁어오기
---
github_trend_cloner.py <br><br>
이거 github trend에서 긁어오는 겁니다. <br>
star수 fork 수 등등 내부 코드 보면 수정할 수 있을 겁니다. 계속 똑같은 프로젝트 갖고 오갈랴랴 그냥 처음 찾은 프로젝트 중에 랜덤으로 지정한 갯수 만큼 갖고 오도록 해놨습니다.<br>
ex.<br>
// python3 github_trend_cloner.py

---
infer 분석
---
infer_analyzer.py<br><br>
이건 프로젝트 하나 단위로 하는겁니다.<br>
ex.<br>
// python3 infer_analyzer.py <프로젝트 저장 위치><br>
// python3 infer_analyzer.py ./open-source/langchain4j<br>

batch_infer_analyzer.py<br><br>
이건 프로젝트 뭉탱이 있는거 한꺼번에 infer 돌릴 수 있도록 해놨어요. <br>
문제는 빌드 자동화가 종속 문제 때문에 해당 java 버전이나 gradle 등 개인 환경에 달려있어서 되는 것만 일단 진행 하시죠.<br>
ex.<br>
// python3 batch_infer_analyzer.py <프로젝트 디렉터리 모음 저장 위치><br>
// python3 batch_infer_analyzer.py ./github-trends/java<br>

---
json 파일 생성
---

generate_bug_report.py<br><br>
위에서 분석한 infer-out 파일에 있는 json 파일 분석해서<br>
json 파일로 만들어줘요<br>
method 코드도 다 긁어 오도록 했으니 대충 확인은 했는데 아마 될껄요?<br>
ex.<br>
// python3 generate_bug_report.py  <프로젝트 뭉텅이 있는 디렉터리 위치> <최종으로 원하는 파일 저장 위치> <br>
// python3 generate_bug_report.py ./github-trends/java ./bug-reports

---
CodeT5 자동화 시작
---

conver_to_codet5_trans_files.py<br>

generate_bug_report에서 생성된 all_bugs.json을 사용해서<br>
VJBench-trans 폴더에 들어갈 전처리 데이터 자동 생성<br>
buggy_lines.json, *_original_method.java 생성<br>
아래 저장할 디렉터리 위치에 파일이 저장되는데 제가 그냥 옮기기만 하면 CodeT5 돌아갈 수 있게 해놨어요 작동하는 것까지 확인했습니다.<br>

// python3 convert_to_codet5_trans_files.py <bug-reports/all_bugs.json> <저장할 디렉터리 위치>
// python3 convert_to_codet5_trans_files.py bug-reports/all_bugs.json codet5-output


---
llm-vul 적용하기
---

convert_to_codet5_trans_files.py로 만든 데이터들 <br> 
llm-vul의 VJBench-trans에 복사 붙여넣기 하시고 <br>
1. /scripts/util.py 쪽에서 범위, 숫자 지정 이것만 해주시면 됩니다.
2-1. /scripts/CodeT5/prepare_input.py
2-2. /scripts/fine-tuned_CodeT5/prepare_input.py
하시고 generate_output하시면 rename, structure, rename+structure 제외한 original은 잘 돌아갑니다. <br>


---
예외 환경 설정
---

upgrade_maven.py <br><br>
이건 wsl환경에서 maven 부족하면 하는건데 infer_analyzer.py에서 쓰라고하면 쓰면 됩니다.<br>
제 환경 기준이라 ㅎㅎㅎ<br>
