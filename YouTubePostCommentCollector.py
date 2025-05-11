# Standard library imports
import os
import re
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from datetime import datetime
import queue
import subprocess

# Third party imports
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import lxml


class YouTubePostCommentCollector:
    def __init__(self, root):
        self.root = root
        self.root.title("유튜브 게시물 댓글 수집기 v2025.05.12")
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        # 변수 설정
        self.version = "2025-05-12 00:00:00"
        self.user = os.getlogin()
        self.is_running = False
        self.driver = None
        self.log_queue = queue.Queue()
        self.default_save_path = os.path.join(os.path.expanduser("~"), "Desktop", "유튜브게시물댓글수집.xlsx")
        self.screenshot_folder = os.path.join(os.path.expanduser("~"), "Desktop", "screenshots")

        # 스타일 설정
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TLabel", padding=6)
        style.configure("TFrame", padding=10)

        self.create_widgets()
        self.setup_logging()

    def create_widgets(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # URL 입력 섹션
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=5)

        ttk.Label(url_frame, text="유튜브 게시물 URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 파일 저장 위치 섹션
        save_frame = ttk.Frame(main_frame)
        save_frame.pack(fill=tk.X, pady=5)

        ttk.Label(save_frame, text="저장 위치:").pack(side=tk.LEFT)
        self.save_path_var = tk.StringVar(value=self.default_save_path)
        self.save_path_entry = ttk.Entry(save_frame, textvariable=self.save_path_var, width=50)
        self.save_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        browse_btn = ttk.Button(save_frame, text="찾아보기", command=self.browse_save_location)
        browse_btn.pack(side=tk.LEFT, padx=5)

        # 로그 창
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Label(log_frame, text="로그:").pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        # 버튼 섹션
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(button_frame, text="실행", command=self.start_collection)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="중지", command=self.stop_collection, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.open_file_btn = ttk.Button(button_frame, text="파일 위치 열기", command=self.open_file_location,
                                        state=tk.DISABLED)
        self.open_file_btn.pack(side=tk.LEFT, padx=5)

        # 상태 표시줄
        self.status_var = tk.StringVar(value="준비됨")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_logging(self):
        # 로그 업데이트 함수
        def update_log():
            while True:
                try:
                    record = self.log_queue.get(block=False)
                    self.log_text.config(state=tk.NORMAL)
                    self.log_text.insert(tk.END, record + "\n")
                    self.log_text.see(tk.END)
                    self.log_text.config(state=tk.DISABLED)
                    self.log_queue.task_done()
                except queue.Empty:
                    break
            self.root.after(100, update_log)

        # 로그 업데이트 시작
        self.root.after(100, update_log)

    def log(self, message):
        self.log_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def browse_save_location(self):
        filename = filedialog.asksaveasfilename(
            initialdir=os.path.dirname(self.save_path_var.get()),
            initialfile=os.path.basename(self.save_path_var.get()),
            defaultextension=".xlsx",
            filetypes=[("Excel 파일", "*.xlsx"), ("모든 파일", "*.*")]
        )
        if filename:
            self.save_path_var.set(filename)

    def start_collection(self):
        if not self.url_entry.get().strip():
            self.log("오류: URL을 입력해주세요.")
            return

        # URL 형식 검증
        url = self.url_entry.get().strip()
        if not self.validate_youtube_post_url(url):
            self.log("오류: 지원하지 않는 URL 형식입니다.")
            self.log("지원하는 URL 형식:")
            self.log("게시물 탭(구 커뮤니티 탭): https://www.youtube.com/channel/{채널소유자고유값}/community?lb={게시글고유값}")
            return

        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.open_file_btn.config(state=tk.DISABLED)
        self.status_var.set("실행 중...")

        # 별도 스레드에서 실행
        threading.Thread(target=self.collect_comments, daemon=True).start()

    def validate_youtube_post_url(self, url):
        # 게시물 탭(구 커뮤니티 탭) URL 패턴만 허용
        community_pattern = r'https?://(?:www\.)?youtube\.com/channel/[A-Za-z0-9_-]+/community\?lb=[A-Za-z0-9_-]+'

        if re.match(community_pattern, url):
            self.log("게시물 탭(구 커뮤니티 탭) URL이 감지되었습니다.")
            return True
        else:
            return False

    def stop_collection(self):
        self.is_running = False
        self.log("사용자에 의해 작업이 중지되었습니다.")
        self.status_var.set("중지됨")

        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def open_file_location(self):
        save_path = self.save_path_var.get()
        if os.path.exists(save_path):
            try:
                # 파일 탐색기에서 파일 선택하여 열기
                if os.name == 'nt':  # Windows
                    subprocess.Popen(f'explorer /select,"{save_path}"')
                elif os.name == 'posix':  # macOS, Linux
                    if 'darwin' in os.sys.platform:  # macOS
                        subprocess.Popen(['open', '-R', save_path])
                    else:  # Linux
                        subprocess.Popen(['xdg-open', os.path.dirname(save_path)])
            except Exception as e:
                self.log(f"파일 위치를 열 수 없습니다: {str(e)}")
        else:
            self.log("파일이 존재하지 않습니다.")

    def collect_comments(self):
        try:
            self.log(f"유튜브 게시물 댓글수집 프로그램 v{self.version} 시작")

            # 저장 폴더 설정
            base_folder = os.path.join(os.path.expanduser("~"), "Desktop", "유튜브게시물댓글수집")

            # 기존 폴더가 있는지 확인하고 처리
            if os.path.exists(base_folder):
                try:
                    # 새 이름 생성 (유튜브게시물댓글수집_old(1), 유튜브게시물댓글수집_old(2), ...)
                    new_folder_name = self.rename_existing_folder(base_folder)
                    self.log(f"기존 폴더를 {os.path.basename(new_folder_name)}(으)로 이름 변경")
                except OSError as e:
                    # 파일 사용 중 오류 처리
                    self.log(f"폴더 이름 변경 중 오류 발생: {str(e)}")
                    result = messagebox.askretrycancel(
                        "파일 사용 중",
                        "유튜브게시물댓글수집 결과물을 사용 중이어서 추가적인 댓글 수집이 어렵습니다.\n"
                        "모든 관련 파일을 닫고 '재시도'를 눌러주세요.",
                        parent=self.root
                    )
                    if result:  # 재시도 선택
                        self.root.after(0, self.start_collection)
                        return
                    else:  # 취소 선택
                        self.stop_collection()
                        return

            # 새 폴더 생성
            os.makedirs(base_folder, exist_ok=True)
            self.log(f"저장 폴더 생성: {base_folder}")

            # 스크린샷 폴더 생성
            self.screenshot_folder = os.path.join(base_folder, "screenshots")
            os.makedirs(self.screenshot_folder, exist_ok=True)
            self.log(f"스크린샷 폴더 생성: {self.screenshot_folder}")

            # 엑셀 파일 경로 설정
            now = datetime.now()
            formatted_date = now.strftime("%y%m%d_%H_%M")
            excel_path = os.path.join(base_folder, f"유튜브게시물댓글수집_{formatted_date}.xlsx")

            youtube_url = self.url_entry.get().strip()
            self.log(f"입력된 URL: {youtube_url}")

            # 드라이버 설정
            options = Options()
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            options.add_argument(f"user-agent={user_agent}")
            options.add_argument("--headless=new")  # 헤드리스 모드

            self.driver = webdriver.Chrome(options=options)

            # 페이지 로드
            self.log("페이지 로딩 중...")
            self.driver.get(youtube_url)
            time.sleep(2)  # 페이지 로딩 대기

            # 스크롤하여 모든 댓글 로드
            self.log("모든 댓글을 로드하기 위해 스크롤 중...")
            self.scroll_page()

            # 페이지 소스 가져오기
            html_source = self.driver.page_source

            # 스크린샷 저장
            self.save_screenshots()

            # 드라이버 종료
            self.driver.quit()
            self.driver = None

            # 댓글 파싱
            self.log("댓글 데이터 수집 중...")
            str_youtube_userIDs, str_youtube_comments = self.parse_comments(html_source)

            if not str_youtube_userIDs and not str_youtube_comments:
                self.log("수집된 댓글이 없습니다.")
                self.stop_collection()
                return

            # 데이터 길이 맞추기
            if len(str_youtube_userIDs) < len(str_youtube_comments):
                diff = len(str_youtube_comments) - len(str_youtube_userIDs)
                str_youtube_userIDs = [None] * diff + str_youtube_userIDs
                self.log(f"ID 데이터가 부족하여 {diff}개의 빈 항목 추가")
            elif len(str_youtube_userIDs) > len(str_youtube_comments):
                diff = len(str_youtube_userIDs) - len(str_youtube_comments)
                str_youtube_comments = [None] * diff + str_youtube_comments
                self.log(f"댓글 데이터가 부족하여 {diff}개의 빈 항목 추가")

            # 데이터프레임으로 변환
            self.log(f"총 {len(str_youtube_userIDs)}개의 댓글을 수집했습니다.")
            df = pd.DataFrame({'ID': str_youtube_userIDs, 'comment': str_youtube_comments})

            # 파일 저장
            df.to_excel(excel_path, sheet_name="sheet1", index=True)
            self.log(f"파일 저장 완료: {excel_path}")

            # 작업 완료 후 UI 업데이트
            self.root.after(0, self.collection_completed, excel_path)

        except Exception as e:
            self.log(f"오류 발생: {str(e)}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            self.root.after(0, self.stop_collection)

    def rename_existing_folder(self, folder_path):
        """기존 폴더 이름을 변경하는 함수"""
        base_dir = os.path.dirname(folder_path)
        folder_name = os.path.basename(folder_path)

        counter = 1
        while True:
            new_name = f"{folder_name}_old({counter})"
            new_path = os.path.join(base_dir, new_name)

            if not os.path.exists(new_path):
                try:
                    os.rename(folder_path, new_path)
                    return new_path
                except OSError:
                    # 권한 오류나 파일 사용 중 오류 발생 시 예외 전파
                    raise

            counter += 1

    def scroll_page(self):
        """페이지를 끝까지 스크롤하여 모든 댓글 로드"""
        last_page_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        scroll_count = 0
        max_scrolls = 30  # 최대 스크롤 횟수 제한

        while self.is_running and scroll_count < max_scrolls:
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(1.5)  # 데이터 로딩 대기
            new_page_height = self.driver.execute_script("return document.documentElement.scrollHeight")

            scroll_count += 1
            self.log(f"스크롤 {scroll_count}/{max_scrolls} 진행 중...")

            if new_page_height == last_page_height:
                self.log("더 이상 로드할 댓글이 없습니다.")
                break

            last_page_height = new_page_height

    def save_screenshots(self):
        """페이지 스크린샷 저장"""
        self.log("댓글 스크린샷 저장 중...")
        try:
            yt_formatted_strings = self.driver.find_elements(By.XPATH, '//*[@id="body"]')
            screenshot_count = 0

            for yt_formatted_string in yt_formatted_strings:
                if not self.is_running:
                    return

                text = yt_formatted_string.text
                if not text:
                    continue

                screenshot_path = os.path.join(self.screenshot_folder, "screenshot.png")
                screenshot_path = self.get_available_filename(screenshot_path)

                # 전체 페이지 스크린샷
                self.driver.save_screenshot(screenshot_path)

                # 요소 스크린샷
                element_png = yt_formatted_string.screenshot_as_png
                try:
                    with open(screenshot_path, "wb") as file:
                        file.write(element_png)
                    screenshot_count += 1
                except Exception as e:
                    self.log(f"스크린샷 저장 중 오류 발생: {str(e)}")

            self.log(f"총 {screenshot_count}개의 스크린샷 저장 완료")

        except Exception as e:
            self.log(f"스크린샷 저장 중 오류 발생: {str(e)}")

    def parse_comments(self, html_source):
        """HTML에서 댓글 정보 추출"""
        try:
            soup = BeautifulSoup(html_source, "lxml")

            # 사용자 ID 추출
            str_youtube_userIDs = []
            yt_formatted_strings = soup.find_all('a', id='author-text')
            self.log(f"사용자 ID {len(yt_formatted_strings)}개 발견")

            for yt_formatted_string in yt_formatted_strings:
                text = yt_formatted_string.get_text().replace(",", "").replace("\n", "")
                if "@" in text:
                    cleaned_text = re.sub(r"[^a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣0-9\s-]", "", text).replace(" ", "")
                    str_youtube_userIDs.append(cleaned_text)

            # 댓글 내용 추출
            str_youtube_comments = []
            yt_formatted_strings = soup.find_all('ytd-expander', id='expander')
            self.log(f"댓글 내용 {len(yt_formatted_strings)}개 발견")

            for yt_formatted_string in yt_formatted_strings:
                text = yt_formatted_string.get_text().replace(",", "").replace("\n", "").replace("간략히", "").replace(
                    "자세히 보기", "")
                cleaned_text = re.sub(r"[^a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣0-9\s]", "", text)
                str_youtube_comments.append(text)

            return str_youtube_userIDs, str_youtube_comments

        except Exception as e:
            self.log(f"댓글 파싱 중 오류 발생: {str(e)}")
            return [], []

    def get_available_filename(self, path):
        """중복되지 않는 파일명 생성"""
        base_dir = os.path.dirname(path)
        base_name = os.path.basename(path)
        name, ext = os.path.splitext(base_name)
        i = 1
        while os.path.exists(path):
            new_name = f"{name}{i}{ext}"
            path = os.path.join(base_dir, new_name)
            i += 1
        return path

    def ensure_unique_filename(self, filepath):
        """파일명이 중복되지 않도록 처리"""
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)

        counter = 1
        while os.path.exists(filepath):
            filepath = os.path.join(directory, f"{name}({counter}){ext}")
            counter += 1

        return filepath

    def collection_completed(self, save_path):
        self.is_running = False
        self.status_var.set("완료됨")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.open_file_btn.config(state=tk.NORMAL)
        self.log("작업이 완료되었습니다.")


def main():
    root = tk.Tk()
    app = YouTubePostCommentCollector(root)
    root.mainloop()


if __name__ == "__main__":
    main()
