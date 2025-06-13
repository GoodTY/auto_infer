#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import time

class InferAnalyzer:
    def __init__(self, project_path: str):
        # WSL 환경 확인
        self.is_wsl = os.path.exists('/proc/version') and 'microsoft' in open('/proc/version').read().lower()
        
        # WSL 환경에서 경로 변환
        if self.is_wsl:
            # Windows 경로를 WSL 경로로 변환
            if project_path.startswith('/mnt/c/'):
                self.project_path = project_path
            else:
                # 상대 경로나 다른 형식의 경로를 절대 경로로 변환
                self.project_path = os.path.abspath(project_path)
        else:
            self.project_path = project_path
            
        self.report_dir = "infer-reports"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_file = f"{self.report_dir}/report_{self.timestamp}.txt"
        
        # 색상 코드
        self.RED = '\033[0;31m'
        self.GREEN = '\033[0;32m'
        self.YELLOW = '\033[1;33m'
        self.NC = '\033[0m'  # No Color

    def check_permissions(self) -> bool:
        """실행 권한을 확인합니다."""
        try:
            # gradlew 파일의 실행 권한 확인 및 설정
            if os.path.exists("./gradlew"):
                os.chmod("./gradlew", 0o755)
            return True
        except Exception as e:
            print(f"{self.RED}권한 설정 중 오류 발생: {e}{self.NC}")
            return False

    def install_maven(self) -> bool:
        """Maven을 최신 버전으로 설치합니다."""
        try:
            print(f"{self.GREEN}Maven 설치를 시작합니다...{self.NC}")
            
            # 임시 디렉토리 생성
            temp_dir = "/tmp/maven_install"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Maven 다운로드 및 설치
            maven_version = "3.9.5"
            maven_url = f"https://archive.apache.org/dist/maven/maven-3/{maven_version}/binaries/apache-maven-{maven_version}-bin.tar.gz"
            maven_tar = f"{temp_dir}/maven.tar.gz"
            
            print(f"Maven {maven_version} 다운로드 중...")
            subprocess.run(["wget", "-O", maven_tar, maven_url], check=True)
            
            print("Maven 압축 해제 중...")
            subprocess.run(["tar", "xzf", maven_tar, "-C", temp_dir], check=True)
            
            # Maven 설치
            maven_dir = f"/opt/maven-{maven_version}"
            print(f"Maven을 {maven_dir}에 설치 중...")
            subprocess.run(["sudo", "mv", f"{temp_dir}/apache-maven-{maven_version}", maven_dir], check=True)
            
            # 심볼릭 링크 생성
            subprocess.run(["sudo", "ln", "-sf", maven_dir, "/opt/maven"], check=True)
            
            # 환경 변수 설정
            maven_profile = """
export M2_HOME=/opt/maven
export PATH=$M2_HOME/bin:$PATH
"""
            with open(os.path.expanduser("~/.bashrc"), "a") as f:
                f.write(maven_profile)
            
            # 현재 세션에 환경 변수 적용
            os.environ["M2_HOME"] = "/opt/maven"
            os.environ["PATH"] = f"/opt/maven/bin:{os.environ['PATH']}"
            
            # 설치 확인
            print("Maven 설치 확인 중...")
            result = subprocess.run(["mvn", "-v"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"{self.RED}Maven 설치 확인 실패: {result.stderr}{self.NC}")
                return False
                
            print(f"{self.GREEN}Maven 설치가 완료되었습니다.{self.NC}")
            print("설치된 Maven 버전:")
            print(result.stdout)
            
            return True
            
        except Exception as e:
            print(f"{self.RED}Maven 설치 중 오류가 발생했습니다: {e}{self.NC}")
            return False

    def check_environment(self) -> bool:
        """환경 설정을 확인합니다."""
        try:
            # Maven 버전 확인
            mvn_version_cmd = ["mvn", "-v"]
            result = subprocess.run(mvn_version_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"{self.RED}Maven이 설치되어 있지 않습니다.{self.NC}")
                print(f"{self.YELLOW}Maven을 설치하려면 다음 명령어를 실행하세요:{self.NC}")
                print("python upgrade_maven.py")
                return False
                
            # Maven 버전 파싱
            version_line = [line for line in result.stdout.split('\n') if 'Apache Maven' in line][0]
            version = version_line.split()[2]  # "Apache Maven 3.x.x" 형식에서 버전 추출
            major_version = int(version.split('.')[1])  # 3.x.x에서 x 추출
            
            if major_version < 8:
                print(f"{self.RED}Maven 버전이 너무 낮습니다. 3.8 이상이 필요합니다. (현재: {version}){self.NC}")
                print(f"{self.YELLOW}Maven을 업그레이드하려면 다음 명령어를 실행하세요:{self.NC}")
                print("python upgrade_maven.py")
                return False
            
            # JAVA_HOME 설정 확인
            java_home = os.environ.get('JAVA_HOME')
            if not java_home:
                print(f"{self.YELLOW}JAVA_HOME이 설정되어 있지 않습니다.{self.NC}")
                print("JAVA_HOME을 설정하려면 다음 명령어를 실행하세요:")
                print("export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64")  # 또는 실제 Java 설치 경로
                return False
            
            return True
            
        except Exception as e:
            print(f"{self.RED}환경 확인 중 오류가 발생했습니다: {e}{self.NC}")
            return False

    def run_infer(self) -> bool:
        """Infer 분석을 실행합니다."""
        try:
            print(f"{self.GREEN}Infer 분석을 시작합니다...{self.NC}")
            print(f"프로젝트 경로: {self.project_path}")

            # 프로젝트 디렉토리로 이동
            if not os.path.exists(self.project_path):
                print(f"{self.RED}Error: 프로젝트 경로가 존재하지 않습니다: {self.project_path}{self.NC}")
                return False
                
            os.chdir(self.project_path)
            
            # 권한 확인
            if not self.check_permissions():
                return False

            # infer-out 디렉토리 정리 (최대 3번 시도)
            infer_out = Path("infer-out")
            for attempt in range(3):
                if infer_out.exists():
                    try:
                        import shutil
                        # 강제로 디렉토리 삭제
                        shutil.rmtree(infer_out, ignore_errors=True)
                        # 디렉토리가 완전히 삭제될 때까지 대기
                        time.sleep(2)
                        
                        # 디렉토리가 실제로 삭제되었는지 확인
                        if not infer_out.exists():
                            break
                        else:
                            print(f"{self.YELLOW}경고: infer-out 디렉토리 삭제 재시도 중... (시도 {attempt + 1}/3){self.NC}")
                            # 추가 정리 시도
                            try:
                                for item in infer_out.glob("*"):
                                    if item.is_file():
                                        item.unlink()
                                    elif item.is_dir():
                                        shutil.rmtree(item, ignore_errors=True)
                            except Exception as e:
                                print(f"{self.YELLOW}경고: 추가 정리 중 오류 발생: {e}{self.NC}")
                    except Exception as e:
                        print(f"{self.YELLOW}경고: infer-out 디렉토리 정리 중 오류 발생: {e}{self.NC}")
                        if attempt == 2:  # 마지막 시도였다면
                            print(f"{self.RED}Error: infer-out 디렉토리를 정리할 수 없습니다.{self.NC}")
                            return False
                        time.sleep(1)  # 다음 시도 전 대기

            # .global.tenv 파일 정리
            tenv_file = Path(".global.tenv")
            if tenv_file.exists():
                try:
                    tenv_file.unlink()
                except Exception as e:
                    print(f"{self.YELLOW}경고: .global.tenv 파일 정리 중 오류 발생: {e}{self.NC}")
                    # 계속 진행

            # 빌드 시스템 감지 및 적절한 명령어 선택
            if os.path.exists("pom.xml"):
                # Maven 프로젝트의 경우
                print("1단계: Maven 컴파일 및 Infer 캡처...")
                cmd = ["infer", "run", "--keep-going", "--", "mvn", "clean", "compile", "-DskipTests"]
            elif os.path.exists("build.gradle"):
                # Gradle 프로젝트의 경우
                print("1단계: Gradle 컴파일 및 Infer 캡처...")
                cmd = ["infer", "run", "--keep-going", "--", "./gradlew", "clean", "compileJava"]
            else:
                print(f"{self.RED}지원되지 않는 프로젝트 구조입니다.{self.NC}")
                return False
                
            # 명령어 실행 전 환경 변수 설정
            env = os.environ.copy()
            env["MAVEN_OPTS"] = "-Xmx4g"  # Maven에 더 많은 메모리 할당
            
            # 명령어 실행
            print(f"실행 명령어: {' '.join(cmd)}")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"{self.YELLOW}컴파일 중 경고가 발생했습니다.{self.NC}")
                print(result.stderr)
                # 계속 진행
            
            # Infer 분석 결과 확인
            if not infer_out.exists():
                print(f"{self.RED}Error: Infer 캡처가 실패했습니다.{self.NC}")
                return False
                
            # 상태 파일 확인 및 생성
            state_file = infer_out / ".infer_runstate.json"
            if not state_file.exists():
                try:
                    state_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(state_file, "w") as f:
                        json.dump({"version": "1.0", "timestamp": time.time()}, f)
                except Exception as e:
                    print(f"{self.YELLOW}경고: 상태 파일 생성 중 오류 발생: {e}{self.NC}")
                    # 계속 진행
                
            # report.json 파일이 없으면 생성 (최대 3번 시도)
            for attempt in range(3):
                if not (infer_out / "report.json").exists():
                    print("Infer 보고서 생성 중...")
                    try:
                        subprocess.run(["infer", "report"], check=True)
                        if (infer_out / "report.json").exists():
                            break
                    except subprocess.CalledProcessError as e:
                        print(f"{self.YELLOW}경고: 보고서 생성 실패 (시도 {attempt + 1}/3){self.NC}")
                        if attempt == 2:  # 마지막 시도였다면
                            print(f"{self.RED}Error: 보고서를 생성할 수 없습니다.{self.NC}")
                            return False
                        time.sleep(1)  # 다음 시도 전 대기
            
            print(f"{self.GREEN}Infer 분석이 완료되었습니다.{self.NC}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{self.RED}Infer 실행 중 오류가 발생했습니다: {e}{self.NC}")
            if hasattr(e, 'stderr'):
                print(f"오류 상세: {e.stderr}")
            return False
        except Exception as e:
            print(f"{self.RED}예상치 못한 오류가 발생했습니다: {e}{self.NC}")
            return False

    def analyze_results(self) -> list:
        """Infer 분석 결과를 분석합니다."""
        try:
            report_file = Path("infer-out/report.json")
            if not report_file.exists():
                print(f"{self.YELLOW}경고: 분석 결과 파일을 찾을 수 없습니다: {report_file}{self.NC}")
                return []
            
            with open(report_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                print(f"{self.YELLOW}경고: 예상치 못한 결과 형식입니다.{self.NC}")
                return []
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"{self.RED}JSON 파싱 오류: {e}{self.NC}")
            return []
        except Exception as e:
            print(f"{self.RED}결과 분석 중 오류가 발생했습니다: {e}{self.NC}")
            return []

    def get_method_code(self, file_path: str, method_name: str, line_number: int) -> str:
        """메서드의 실제 코드를 추출합니다."""
        try:
            if not os.path.exists(file_path):
                return "파일을 찾을 수 없습니다."
                
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 메서드 시작과 끝을 찾기 위한 변수
            start_line = max(0, line_number - 1)  # 0-based index
            end_line = min(len(lines), line_number + 20)  # 최대 20줄까지
            method_code = []
            brace_count = 0
            found_method = False
            
            # 메서드 시작 부분 찾기
            for i in range(start_line, -1, -1):
                if method_name in lines[i]:
                    start_line = i
                    found_method = True
                    break
                    
            if not found_method:
                return "메서드를 찾을 수 없습니다."
                
            # 메서드 코드 추출
            for i in range(start_line, end_line):
                line = lines[i]
                method_code.append(line)
                
                # 중괄호 카운트로 메서드 범위 파악
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0 and i > start_line:
                    break
                    
            return ''.join(method_code)
            
        except Exception as e:
            return f"코드 추출 중 오류 발생: {str(e)}"

    def generate_report(self, issues: List[Dict]) -> str:
        """분석 결과를 보고서 형식으로 생성합니다."""
        if not issues:
            return "발견된 문제가 없습니다."
            
        report = []
        for issue in issues:
            report.append(f"\n문제 유형: {issue['bug_type']}")
            report.append(f"파일: {issue['file']}")
            report.append(f"라인: {issue['line']}")
            report.append(f"메서드: {issue['procedure']}")
            report.append(f"설명: {issue['description']}")
            
            # 메서드 코드 추출
            method_code = self.get_method_code(issue['file'], issue['procedure'], issue['line'])
            report.append("\n관련 코드:")
            report.append("```java")
            report.append(method_code)
            report.append("```")
            report.append("-" * 80)
            
        return "\n".join(report)

    def print_summary(self, issues: List[Dict]) -> None:
        """분석 결과 요약을 출력합니다."""
        print("\n분석이 완료되었습니다.")
        print(f"보고서 위치: {self.report_file}")
        print("\n주요 발견사항:")
        
        if not issues:
            print("발견된 문제가 없습니다.")
        else:
            print(f"총 발견된 문제: {len(issues)}")
            files = set(issue.get('file', '알 수 없음') for issue in issues)
            print("\n문제가 있는 파일 목록:")
            for file in sorted(files):
                print(f"- {file}")

    def run(self) -> bool:
        """Infer 분석을 실행합니다."""
        if self.run_infer():
            issues = self.analyze_results()
            report = self.generate_report(issues)
            
            # 보고서 파일로 저장
            Path(self.report_dir).mkdir(exist_ok=True)
            with open(self.report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self.print_summary(issues)
            return True
        return False

def main():
    if len(sys.argv) != 2:
        print("사용법: python infer_analyzer.py <프로젝트_경로>")
        sys.exit(1)

    analyzer = InferAnalyzer(sys.argv[1])
    analyzer.run()

if __name__ == "__main__":
    main()
