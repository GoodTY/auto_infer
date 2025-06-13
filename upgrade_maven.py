#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil

class MavenUpgrader:
    def __init__(self):
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.NC = '\033[0m'  # No Color

    def check_current_version(self):
        """현재 Maven 버전을 확인합니다."""
        try:
            result = subprocess.run(["mvn", "-v"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"{self.RED}Maven이 설치되어 있지 않습니다.{self.NC}")
                return None
            
            # 버전 정보 파싱
            version_line = [line for line in result.stdout.split('\n') if 'Apache Maven' in line][0]
            version = version_line.split()[2]  # "Apache Maven 3.x.x" 형식에서 버전 추출
            return version
        except Exception as e:
            print(f"{self.RED}Maven 버전 확인 중 오류 발생: {e}{self.NC}")
            return None

    def install_maven(self, version="3.9.5"):
        """Maven을 지정된 버전으로 설치합니다."""
        try:
            print(f"{self.GREEN}Maven {version} 설치를 시작합니다...{self.NC}")
            
            # 임시 디렉토리 생성
            temp_dir = "/tmp/maven_install"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Maven 다운로드
            maven_url = f"https://archive.apache.org/dist/maven/maven-3/{version}/binaries/apache-maven-{version}-bin.tar.gz"
            maven_tar = f"{temp_dir}/maven.tar.gz"
            
            print(f"Maven {version} 다운로드 중...")
            subprocess.run(["wget", "-O", maven_tar, maven_url], check=True)
            
            print("Maven 압축 해제 중...")
            subprocess.run(["tar", "xzf", maven_tar, "-C", temp_dir], check=True)
            
            # 기존 Maven 디렉토리 정리
            maven_dir = f"/opt/maven-{version}"
            if os.path.exists(maven_dir):
                print(f"기존 Maven 디렉토리 제거 중: {maven_dir}")
                subprocess.run(["sudo", "rm", "-rf", maven_dir], check=True)
            
            # Maven 설치
            print(f"Maven을 {maven_dir}에 설치 중...")
            subprocess.run(["sudo", "mv", f"{temp_dir}/apache-maven-{version}", maven_dir], check=True)
            
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
            
            # 임시 디렉토리 정리
            shutil.rmtree(temp_dir)
            
            return True
            
        except Exception as e:
            print(f"{self.RED}Maven 설치 중 오류가 발생했습니다: {e}{self.NC}")
            return False

    def run(self):
        """Maven 업그레이드를 실행합니다."""
        current_version = self.check_current_version()
        if current_version:
            print(f"현재 Maven 버전: {current_version}")
            major_version = int(current_version.split('.')[1])
            if major_version >= 8:
                print(f"{self.GREEN}Maven 버전이 이미 3.8 이상입니다.{self.NC}")
                return True
        
        print(f"{self.YELLOW}Maven을 3.9.5 버전으로 업그레이드하시겠습니까? (y/n){self.NC}")
        response = input().strip().lower()
        if response == 'y':
            return self.install_maven()
        else:
            print("업그레이드를 취소했습니다.")
            return False

def main():
    upgrader = MavenUpgrader()
    success = upgrader.run()
    if success:
        print(f"{upgrader.GREEN}Maven 업그레이드가 완료되었습니다.{upgrader.NC}")
        print("새로운 터미널을 열거나 다음 명령어를 실행하세요:")
        print("source ~/.bashrc")
    else:
        print(f"{upgrader.RED}Maven 업그레이드에 실패했습니다.{upgrader.NC}")
        sys.exit(1)

if __name__ == "__main__":
    main() 