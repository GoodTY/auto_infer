#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

class GitHubTrendCloner:
    def __init__(self):
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.NC = '\033[0m'  # No Color
        
        # GitHub API 설정
        self.api_url = "https://api.github.com/search/repositories"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        # 저장소 저장 경로
        self.base_dir = Path("github-trends")
        self.java_dir = self.base_dir / "java"
        
        # GitHub API 요청 제한을 위한 딜레이 (초)
        self.delay = 2
        
        # 안전 설정
        self.max_repos = 10  # 최대 클론할 저장소 수
        self.min_stars = 500  # 최소 별표 수 (1000에서 500으로 감소)
        self.max_size_mb = 100  # 최대 저장소 크기 (MB)
        self.safe_extensions = {'.java', '.kt', '.gradle', '.xml', '.md', '.txt', '.json', '.yml', '.yaml', '.properties'}

    def print_warning(self):
        """보안 경고 메시지를 출력합니다."""
        print(f"\n{self.YELLOW}=== 보안 경고 ==={self.NC}")
        print("이 스크립트는 GitHub의 트렌딩 Java 저장소를 클론합니다.")
        print("주의사항:")
        print("1. 클론된 코드는 검증되지 않은 외부 코드입니다.")
        print("2. 코드를 실행하기 전에 반드시 검토하세요.")
        print("3. 빌드나 실행은 별도의 격리된 환경에서 하세요.")
        print("4. 시스템에 영향을 주는 명령어가 포함될 수 있습니다.")
        print(f"{self.YELLOW}================{self.NC}\n")
        
        response = input("계속 진행하시겠습니까? (y/n): ").strip().lower()
        return response == 'y'

    def is_safe_repo(self, repo: dict) -> bool:
        """저장소가 안전한지 확인합니다."""
        # 최소 별표 수 확인
        if repo['stargazers_count'] < self.min_stars:
            return False
            
        # 저장소 크기 확인 (MB)
        size_mb = repo['size'] / 1024  # KB to MB
        if size_mb > self.max_size_mb:
            return False
            
        return True

    def get_trending_repos(self, days: int = 30) -> list:
        """GitHub Trending Java 저장소 목록을 가져옵니다."""
        try:
            # 검색 쿼리 구성
            query = {
                "q": f"language:java created:>{datetime.now() - timedelta(days=days):%Y-%m-%d} stars:>={self.min_stars}",
                "sort": "stars",
                "order": "desc",
                "per_page": 100
            }
            
            print(f"{self.GREEN}GitHub Trending Java 저장소를 가져오는 중...{self.NC}")
            print(f"검색 기간: 최근 {days}일")
            print(f"최소 스타 수: {self.min_stars:,}개")
            
            response = requests.get(self.api_url, headers=self.headers, params=query)
            response.raise_for_status()
            
            repos = response.json()["items"]
            print(f"{self.GREEN}총 {len(repos)}개의 저장소를 찾았습니다.{self.NC}")
            
            if len(repos) == 0:
                print(f"{self.YELLOW}저장소를 찾지 못했습니다. 검색 조건을 완화해보겠습니다...{self.NC}")
                # 검색 조건 완화
                query["q"] = f"language:java stars:>={self.min_stars}"  # 생성일 제한 제거
                response = requests.get(self.api_url, headers=self.headers, params=query)
                response.raise_for_status()
                repos = response.json()["items"]
                print(f"{self.GREEN}조건 완화 후 {len(repos)}개의 저장소를 찾았습니다.{self.NC}")
            
            # 안전한 저장소만 필터링
            safe_repos = [repo for repo in repos if self.is_safe_repo(repo)]
            print(f"안전 기준을 통과한 저장소: {len(safe_repos)}개")
            
            # 최대 개수 제한
            return safe_repos[:self.max_repos]
            
        except requests.exceptions.RequestException as e:
            print(f"{self.RED}GitHub API 요청 중 오류 발생: {e}{self.NC}")
            return []

    def clone_repository(self, repo: dict) -> bool:
        """저장소를 클론합니다."""
        try:
            repo_name = repo["full_name"]
            clone_url = repo["clone_url"]
            target_dir = self.java_dir / repo_name.replace("/", "_")
            
            if target_dir.exists():
                print(f"{self.YELLOW}이미 존재하는 저장소: {repo_name}{self.NC}")
                return True
            
            print(f"\n{self.GREEN}클론 중: {repo_name}{self.NC}")
            print(f"설명: {repo.get('description', '설명 없음')}")
            print(f"별표: {repo['stargazers_count']:,}개")
            print(f"포크: {repo['forks_count']:,}개")
            print(f"크기: {repo['size'] / 1024:.1f} MB")
            print(f"생성일: {repo['created_at']}")
            print(f"최근 업데이트: {repo['updated_at']}")
            print(f"URL: {repo['html_url']}")
            
            # 얕은 클론 (최신 커밋만)
            subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(target_dir)],
                check=True,
                capture_output=True,
                text=True
            )
            
            # 저장소 정보 저장
            info_file = target_dir / "repo_info.json"
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump({
                    "name": repo["full_name"],
                    "description": repo.get("description", ""),
                    "stars": repo["stargazers_count"],
                    "forks": repo["forks_count"],
                    "language": repo["language"],
                    "created_at": repo["created_at"],
                    "updated_at": repo["updated_at"],
                    "clone_time": datetime.now().isoformat(),
                    "url": repo["html_url"],
                    "warning": "이 저장소의 코드는 검증되지 않았습니다. 실행하기 전에 반드시 검토하세요."
                }, f, indent=2, ensure_ascii=False)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{self.RED}클론 실패: {repo_name}{self.NC}")
            print(f"오류: {e.stderr}")
            return False
        except Exception as e:
            print(f"{self.RED}예상치 못한 오류 발생: {e}{self.NC}")
            return False

    def run(self, days: int = 30):
        """트렌딩 저장소 클론을 실행합니다."""
        # 보안 경고 표시
        if not self.print_warning():
            print("작업이 취소되었습니다.")
            return
            
        # 디렉토리 생성
        self.java_dir.mkdir(parents=True, exist_ok=True)
        
        # 저장소 목록 가져오기
        repos = self.get_trending_repos(days)
        if not repos:
            return
        
        # 각 저장소 클론
        success_count = 0
        for repo in repos:
            if self.clone_repository(repo):
                success_count += 1
            time.sleep(self.delay)  # API 요청 제한 방지
        
        # 결과 출력
        print(f"\n{self.GREEN}클론 완료!{self.NC}")
        print(f"성공: {success_count}/{len(repos)}")
        print(f"저장 위치: {self.java_dir}")
        print(f"\n{self.YELLOW}주의: 클론된 코드는 검증되지 않았습니다.{self.NC}")
        print("코드를 실행하기 전에 반드시 검토하세요.")

def main():
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print("Error: 날짜는 정수여야 합니다.")
            sys.exit(1)
    else:
        days = 30  # 기본값을 30일로 변경
    
    cloner = GitHubTrendCloner()
    cloner.run(days)

if __name__ == "__main__":
    main() 