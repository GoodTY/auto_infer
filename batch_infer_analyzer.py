#!/usr/bin/env python3
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import subprocess
import concurrent.futures
from infer_analyzer import InferAnalyzer

class BatchInferAnalyzer:
    def __init__(self, max_workers: int = 2):
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.NC = '\033[0m'  # No Color
        
        self.max_workers = max_workers
        self.results_dir = Path("infer-results")
        self.results_dir.mkdir(exist_ok=True)
        
        # 결과 저장을 위한 파일
        self.summary_file = self.results_dir / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    def find_java_projects(self, directory: str) -> List[str]:
        """디렉토리 내의 Java 프로젝트를 찾습니다."""
        java_projects = []
        directory_path = Path(directory)
        
        print(f"{self.GREEN}Java 프로젝트 검색 중: {directory}{self.NC}")
        
        # 디렉토리가 존재하는지 확인
        if not directory_path.exists():
            print(f"{self.RED}Error: 디렉토리가 존재하지 않습니다: {directory}{self.NC}")
            return []
            
        # 디렉토리 내의 모든 하위 디렉토리 검사
        for root, dirs, files in os.walk(directory):
            # Maven 프로젝트 확인
            if "pom.xml" in files:
                project_path = str(Path(root))
                print(f"{self.GREEN}Maven 프로젝트 발견: {project_path}{self.NC}")
                java_projects.append(project_path)
                # 하위 디렉토리 검색 중단 (중복 방지)
                dirs[:] = []
            # Gradle 프로젝트 확인
            elif "build.gradle" in files:
                project_path = str(Path(root))
                print(f"{self.GREEN}Gradle 프로젝트 발견: {project_path}{self.NC}")
                java_projects.append(project_path)
                # 하위 디렉토리 검색 중단 (중복 방지)
                dirs[:] = []
        
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

    def analyze_project(self, project_path: str) -> Dict:
        """단일 프로젝트를 분석합니다."""
        try:
            print(f"\n분석 시작: {project_path}")
            
            # 프로젝트 경로로 이동
            os.chdir(project_path)
            
            # Infer 분석 실행
            analyzer = InferAnalyzer(project_path)
            if not analyzer.run_infer():
                return {
                    "project": project_path,
                    "status": "error",
                    "error": "Infer 분석 실패",
                    "issues": []
                }
            
            # 결과 분석
            issues = analyzer.analyze_results()
            
            # 각 이슈에 메서드 코드 추가
            processed_issues = []
            for issue in issues:
                try:
                    processed_issue = {
                        "bug_type": issue.get("bug_type", "알 수 없음"),
                        "file": issue.get("file", "알 수 없음"),
                        "line": issue.get("line", 0),
                        "procedure": issue.get("procedure", "알 수 없음"),
                        "description": issue.get("description", "설명 없음")
                    }
                    
                    # 메서드 코드 추출
                    if all(k in processed_issue for k in ["file", "procedure", "line"]):
                        processed_issue["method_code"] = self.get_method_code(
                            processed_issue["file"],
                            processed_issue["procedure"],
                            processed_issue["line"]
                        )
                    
                    processed_issues.append(processed_issue)
                except Exception as e:
                    print(f"{self.YELLOW}경고: 이슈 처리 중 오류 발생: {e}{self.NC}")
                    continue
            
            return {
                "project": project_path,
                "status": "success",
                "issues": processed_issues
            }
            
        except Exception as e:
            return {
                "project": project_path,
                "status": "error",
                "error": str(e),
                "issues": []
            }

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
    
    def run(self, directory: str) -> None:
        """지정된 디렉토리의 모든 Java 프로젝트를 분석합니다."""
        try:
            # Java 프로젝트 찾기
            print(f"Java 프로젝트 검색 중: {directory}")
            projects = self.find_java_projects(directory)
            
            if not projects:
                print(f"{self.YELLOW}분석할 Java 프로젝트를 찾을 수 없습니다.{self.NC}")
                return
                
            print(f"\n배치 Infer 분석을 시작합니다...")
            print(f"분석할 프로젝트 수: {len(projects)}")
            print(f"동시 실행 수: {self.max_workers}")
            
            # ThreadPoolExecutor로 병렬 처리
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_project = {executor.submit(self.analyze_project, project): project for project in projects}
                
                for future in concurrent.futures.as_completed(future_to_project):
                    project = future_to_project[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        print(f"{self.RED}프로젝트 분석 중 오류 발생: {project} - {e}{self.NC}")
                        results.append({
                            "project": project,
                            "status": "error",
                            "error": str(e),
                            "issues": []
                        })
            
            # 결과 저장
            summary_file = self.save_summary(results)
            if summary_file:
                # 결과 출력
                self.print_summary(results)
            else:
                print(f"{self.RED}결과를 저장할 수 없어 분석 결과만 출력합니다.{self.NC}")
                self.print_summary(results)
                
        except Exception as e:
            print(f"{self.RED}배치 분석 중 오류가 발생했습니다: {e}{self.NC}")
            raise

def main():
    if len(sys.argv) != 2:
        print("사용법: python batch_infer_analyzer.py <프로젝트_디렉토리>")
        sys.exit(1)
    
    # 프로젝트 디렉토리
    directory = sys.argv[1]
    
    # 배치 분석기 실행
    analyzer = BatchInferAnalyzer(max_workers=2)  # 동시 실행 수 조정 가능
    analyzer.run(directory)

if __name__ == "__main__":
    main() 