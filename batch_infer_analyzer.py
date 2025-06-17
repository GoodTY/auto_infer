#!/usr/bin/env python3
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import concurrent.futures
from infer_analyzer import InferAnalyzer
import shutil
import re

class BatchInferAnalyzer:
    def __init__(self, max_workers: int = 2):
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.NC = '\033[0m'  # No Color
        
        self.max_workers = max_workers
        self.log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.results_dir = os.path.join(os.getcwd(), "infer-results")
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 결과 저장을 위한 파일
        self.summary_file = os.path.join(self.results_dir, f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
    def find_java_projects(self, directory: str) -> List[str]:
        """Java 프로젝트 디렉토리 찾기"""
        java_projects = []
        try:
            # 기준 디렉토리의 절대 경로
            base_dir = os.path.abspath(directory)
            
            # 이미 처리된 경로를 추적
            processed_paths = set()
            
            for root, dirs, files in os.walk(directory):
                # Android 프로젝트 제외
                if "android" in root.lower():
                    continue
                    
                # build.gradle 또는 pom.xml이 있는 디렉토리 찾기
                if "build.gradle" in files or "pom.xml" in files:
                    abs_path = os.path.abspath(root)
                    
                    # 이미 처리된 경로의 하위 디렉토리인지 확인
                    if any(abs_path.startswith(p) for p in processed_paths):
                        continue
                        
                    # 최상위 프로젝트 디렉토리 찾기
                    current_dir = root
                    while current_dir != base_dir:
                        parent_dir = os.path.dirname(current_dir)
                        if os.path.exists(os.path.join(parent_dir, "build.gradle")) or \
                           os.path.exists(os.path.join(parent_dir, "pom.xml")):
                            current_dir = parent_dir
                        else:
                            break
                    
                    abs_path = os.path.abspath(current_dir)
                    if abs_path not in processed_paths:
                        java_projects.append(abs_path)
                        processed_paths.add(abs_path)
                        print(f"프로젝트 발견: {abs_path}")
                        
        except Exception as e:
            print(f"프로젝트 검색 중 오류 발생: {str(e)}")
        return java_projects
        
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

    def analyze_project(self, project_path: str) -> Dict[str, str]:
        """프로젝트 분석"""
        try:
            print(f"\n프로젝트 분석 시작: {project_path}")
            
            # Java 버전 감지
            java_version = self.detect_java_version(project_path)
            print(f"감지된 Java 버전: {java_version}")
            
            # Java 환경 설정
            env = os.environ.copy()
            java_home = f"/usr/lib/jvm/java-{java_version}-openjdk-amd64"
            env["JAVA_HOME"] = java_home
            env["PATH"] = f"{java_home}/bin:{env['PATH']}"
            
            # Gradle 프로젝트 분석
            if os.path.exists(os.path.join(project_path, "gradlew")):
                print("Gradle 프로젝트 분석 시작...")
                gradle_cmd = ["infer", "run", "--", "./gradlew", "clean", "build", "--no-daemon", "-DskipTests"]
                process = subprocess.run(
                    gradle_cmd,
                    cwd=project_path,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if process.returncode != 0:
                    return {
                        "project": project_path,
                        "status": "error",
                        "error": f"Gradle 빌드/분석 실패. 로그: {process.stderr}"
                    }
                
                print("Gradle 프로젝트 분석 완료")
            
            # Maven 프로젝트 분석
            if os.path.exists(os.path.join(project_path, "pom.xml")):
                print(f"Running Maven analysis for {project_path}...")
                try:
                    # Run Maven build with Infer
                    maven_cmd = ["infer", "run", "--", "mvn", "clean", "compile", "-DskipTests"]
                    result = subprocess.run(maven_cmd, 
                                         env=env,
                                         cwd=project_path,
                                         capture_output=True,
                                         text=True)
                    
                    if result.returncode != 0:
                        print(f"Error during Maven analysis: {result.stderr}")
                        return {
                            "project": project_path,
                            "status": "error",
                            "error": f"Maven 빌드/분석 실패. 로그: {result.stderr}"
                        }
                        
                    print(f"Maven analysis completed for {project_path}")
                    return {
                        "project": project_path,
                        "status": "success",
                        "error": None
                    }
                    
                except Exception as e:
                    print(f"Error during Maven analysis: {str(e)}")
                    return {
                        "project": project_path,
                        "status": "error",
                        "error": str(e)
                    }
            else:
                return {
                    "project": project_path,
                    "status": "error",
                    "error": "빌드 파일을 찾을 수 없습니다."
                }
            
            return {
                "project": project_path,
                "status": "success",
                "error": None
            }
            
        except Exception as e:
            return {
                "project": project_path,
                "status": "error",
                "error": str(e)
            }

    def detect_java_version(self, project_path: str) -> Optional[str]:
        """프로젝트의 Java 버전 요구사항을 확인합니다."""
        try:
            # build.gradle 파일 확인
            gradle_file = os.path.join(project_path, "build.gradle")
            if os.path.exists(gradle_file):
                with open(gradle_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # sourceCompatibility 또는 targetCompatibility 확인
                    if 'sourceCompatibility' in content:
                        match = re.search(r'sourceCompatibility\s*=\s*[\'"]?(\d+)[\'"]?', content)
                        if match:
                            return match.group(1)
                    if 'targetCompatibility' in content:
                        match = re.search(r'targetCompatibility\s*=\s*[\'"]?(\d+)[\'"]?', content)
                        if match:
                            return match.group(1)

            # pom.xml 파일 확인
            pom_file = os.path.join(project_path, "pom.xml")
            if os.path.exists(pom_file):
                with open(pom_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # maven.compiler.source 또는 maven.compiler.target 확인
                    if 'maven.compiler.source' in content:
                        match = re.search(r'<maven\.compiler\.source>(\d+)</maven\.compiler\.source>', content)
                        if match:
                            return match.group(1)
                    if 'maven.compiler.target' in content:
                        match = re.search(r'<maven\.compiler\.target>(\d+)</maven\.compiler\.target>', content)
                        if match:
                            return match.group(1)

            # 기본값으로 Java 21 반환
            return "21"
        except Exception as e:
            print(f"Java 버전 확인 중 오류 발생: {str(e)}")
            return "21"  # 오류 발생 시 기본값으로 Java 21 반환

    def save_summary(self, results: List[Dict]) -> str:
        """분석 결과를 요약하여 저장합니다."""
        try:
            # 결과 디렉토리 생성
            os.makedirs("infer-results", exist_ok=True)
            
            # 타임스탬프로 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = f"infer-results/batch_summary_{timestamp}.json"
            
            # 결과 저장
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            print(f"\n{self.GREEN}분석 결과가 저장되었습니다: {summary_file}{self.NC}")
            return summary_file
            
        except Exception as e:
            print(f"{self.RED}결과 저장 중 오류가 발생했습니다: {e}{self.NC}")
            # 임시 파일로 저장 시도
            try:
                temp_file = f"batch_summary_{timestamp}.json"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"{self.YELLOW}결과가 현재 디렉토리에 저장되었습니다: {temp_file}{self.NC}")
                return temp_file
            except Exception as e2:
                print(f"{self.RED}임시 파일 저장도 실패했습니다: {e2}{self.NC}")
                return None
    
    def print_summary(self, results: List[Dict]) -> None:
        """분석 결과를 출력합니다."""
        print("\n=== 분석 결과 요약 ===")
        
        total_projects = len(results)
        successful = sum(1 for r in results if r["status"] == "success")
        failed = total_projects - successful
        
        print(f"\n총 프로젝트 수: {total_projects}")
        print(f"성공: {successful}")
        print(f"실패: {failed}")
        
        print("\n=== 상세 결과 ===")
        for result in results:
            print(f"\n프로젝트: {result['project']}")
            print(f"상태: {result['status']}")
            
            if result["status"] == "success":
                issues = result["issues"]
                print(f"발견된 문제 수: {len(issues)}")
                
                if issues:
                    print("\n문제 상세:")
                    for issue in issues:
                        print(f"\n문제 유형: {issue.get('bug_type', '알 수 없음')}")
                        print(f"파일: {issue.get('file', '알 수 없음')}")
                        print(f"라인: {issue.get('line', 0)}")
                        print(f"메서드: {issue.get('procedure', '알 수 없음')}")
                        print(f"설명: {issue.get('description', '설명 없음')}")
                        
                        if 'method_code' in issue:
                            print("\n관련 코드:")
                            print("```java")
                            print(issue['method_code'])
                            print("```")
                        print("-" * 80)
            else:
                print(f"오류: {result.get('error', '알 수 없음')}")
            print("=" * 80)
    
    def run_analysis(self, directory: str) -> None:
        """프로젝트 분석 실행"""
        try:
            # Java 프로젝트 찾기
            java_projects = self.find_java_projects(directory)
            if not java_projects:
                print("분석할 Java 프로젝트를 찾을 수 없습니다.")
                return

            # Java 버전별로 프로젝트 그룹화
            projects_by_java_version = {}
            for project in java_projects:
                java_version = self.detect_java_version(project)
                if java_version not in projects_by_java_version:
                    projects_by_java_version[java_version] = []
                projects_by_java_version[java_version].append(project)

            # 각 Java 버전별로 분석 실행
            all_results = []
            for java_version, projects in projects_by_java_version.items():
                print(f"\nJava {java_version} 프로젝트 분석 시작 (총 {len(projects)}개)")
                
                # Java 버전 설정
                java_home = f"/usr/lib/jvm/java-{java_version}-openjdk-amd64"
                if not os.path.exists(java_home):
                    print(f"Java {java_version}이 설치되어 있지 않습니다. {java_home} 경로를 확인해주세요.")
                    continue
                
                # 환경 변수 설정
                os.environ["JAVA_HOME"] = java_home
                os.environ["PATH"] = f"{java_home}/bin:" + os.environ["PATH"]
                print(f"JAVA_HOME 설정: {java_home}")

                # 해당 Java 버전의 프로젝트들을 병렬로 분석
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_project = {executor.submit(self.analyze_project, project): project for project in projects}
                    for future in concurrent.futures.as_completed(future_to_project):
                        project = future_to_project[future]
                        try:
                            result = future.result()
                            all_results.append(result)
                            print(f"프로젝트 분석 완료: {project}")
                        except Exception as e:
                            print(f"프로젝트 분석 중 오류 발생: {project} - {str(e)}")
                            all_results.append({
                                "project": project,
                                "status": "error",
                                "error": str(e)
                            })

            # 결과 저장
            summary_file = self.save_summary(all_results)
            print(f"\n분석 결과가 저장되었습니다: {summary_file}")

        except Exception as e:
            print(f"분석 실행 중 오류 발생: {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("사용법: python batch_infer_analyzer.py <프로젝트_디렉토리>")
        sys.exit(1)
    
    # 프로젝트 디렉토리
    directory = sys.argv[1]
    
    # 배치 분석기 실행
    analyzer = BatchInferAnalyzer(max_workers=2)  # 동시 실행 수 조정 가능
    analyzer.run_analysis(directory)

if __name__ == "__main__":
    main() 