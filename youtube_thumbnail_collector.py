# Standard library imports
import re
import os
import time
import requests
import threading
import queue
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Third party imports
import lxml
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import pillow_avif  # 이 import는 필수이지만 직접 사용하지는 않음

# GUI imports
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import messagebox
from tkinter import filedialog
import threading


class YouTubeScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 영상 정보 및 썸네일 추출 프로그램")
        self.root.geometry("800x650")  # 높이를 늘려 추가 버튼을 위한 공간 확보
        self.root.resizable(True, True)

        # 버전 및 사용자 정보
        self.ver = "2025-04-24 18:00:00"
        self.user = os.getlogin()

        # 데이터 저장 변수
        self.src_list = []
        self.t_list = []
        self.href_list = []
        self.href_set = set()
        self.driver = None
        self.is_shorts = False
        self.is_running = False

        # 결과 폴더 경로
        self.output_folder = os.path.dirname(os.path.abspath(__file__))

        # 스레드 관련 변수
        self.thread_count = tk.IntVar(value=3)
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.scraping_thread = None

        # 로그 관련 변수
        self.download_progress_tag = "download_progress"
        self.info_tag = "info"
        self.success_tag = "success"
        self.warning_tag = "warning"
        self.error_tag = "error"
        self.header_tag = "header"
        self.scroll_progress_tag = "scroll_progress"

        # GUI 구성
        self.create_widgets()

        # 로그 업데이트 타이머 시작
        self.update_log_from_queue()

    def create_widgets(self):
        # 프레임 구성
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)

        folder_frame = ttk.Frame(self.root, padding="10")
        folder_frame.pack(fill=tk.X)

        progress_frame = ttk.Frame(self.root, padding="10")
        progress_frame.pack(fill=tk.X)

        log_frame = ttk.Frame(self.root, padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X)

        # 링크 입력
        ttk.Label(top_frame, text="YouTube 채널 링크:").pack(side=tk.LEFT, padx=(0, 5))
        self.url_entry = ttk.Entry(top_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # 로그인 체크박스
        self.login_var = tk.BooleanVar(value=False)
        self.login_check = ttk.Checkbutton(top_frame, text="로그인 필요", variable=self.login_var)
        self.login_check.pack(side=tk.LEFT, padx=(0, 5))

        # 스레드 수 설정
        ttk.Label(control_frame, text="썸네일 다운로드 스레드 수:").pack(side=tk.LEFT, padx=(0, 5))
        self.thread_slider = ttk.Scale(control_frame, from_=1, to=12, orient=tk.HORIZONTAL,
                                       variable=self.thread_count, length=200)
        self.thread_slider.pack(side=tk.LEFT, padx=(0, 5))

        # 스레드 수 표시 레이블
        self.thread_label = ttk.Label(control_frame, text="3")
        self.thread_label.pack(side=tk.LEFT, padx=(0, 5))

        # 스레드 슬라이더 값 변경 시 레이블 업데이트
        self.thread_slider.bind("<Motion>", self.update_thread_label)

        # 결과 폴더 위치 지정
        ttk.Label(folder_frame, text="결과 폴더 위치:").pack(side=tk.LEFT, padx=(0, 5))
        self.folder_entry = ttk.Entry(folder_frame, width=50)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.folder_entry.insert(0, self.output_folder)

        # 폴더 선택 버튼
        self.folder_button = ttk.Button(folder_frame, text="폴더 선택", command=self.select_folder)
        self.folder_button.pack(side=tk.RIGHT)

        # 프로그레스 바
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        # 로그 창
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        # 맑은 고딕 글꼴 설정 시도
        try:
            log_font = ("맑은 고딕", 10)
            self.log_text.configure(font=log_font)
        except:
            # 맑은 고딕 사용 불가능한 경우 시스템 기본 글꼴 사용
            self.log_text.configure(font=("TkDefaultFont", 10))

        # 하단 버튼들
        self.start_button = ttk.Button(button_frame, text="시작", command=self.start_scraping)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="중지", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.open_folder_button = ttk.Button(button_frame, text="결과 폴더 보기", command=self.open_output_folder)
        self.open_folder_button.pack(side=tk.LEFT, padx=5)

        self.exit_button = ttk.Button(button_frame, text="종료", command=self.exit_application)
        self.exit_button.pack(side=tk.RIGHT, padx=5)

        # 태그 설정
        self.log_text.tag_configure(self.download_progress_tag, foreground="#0066CC")
        self.log_text.tag_configure(self.info_tag, foreground="#333333")
        self.log_text.tag_configure(self.success_tag, foreground="#008800")
        self.log_text.tag_configure(self.warning_tag, foreground="#FF6600")
        self.log_text.tag_configure(self.error_tag, foreground="#CC0000")
        self.log_text.tag_configure(self.header_tag, foreground="#000000")
        self.log_text.tag_configure(self.scroll_progress_tag, foreground="#0066CC")

        # 초기 로그 메시지
        self.add_log("=" * 70, tag=self.header_tag)
        self.add_log(f"🚀 유튜브 영상 정보 및 썸네일 추출 프로그램 v{self.ver}", tag=self.header_tag)
        self.add_log(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", tag=self.info_tag)
        self.add_log("=" * 70, tag=self.header_tag)
        self.add_log("")
        self.add_log("📝 사용 방법:", tag=self.header_tag)
        self.add_log("1️⃣ YouTube 채널 링크를 입력하세요", tag=self.info_tag)
        self.add_log("   예: https://www.youtube.com/@thinkgood638/videos", tag=self.info_tag)
        self.add_log("   예: https://www.youtube.com/@Knocpr/shorts", tag=self.info_tag)
        self.add_log("2️⃣ 채널 소유자인 경우 '로그인 필요' 체크박스를 선택하세요", tag=self.info_tag)
        self.add_log("3️⃣ 썸네일 다운로드 스레드 수를 조정하세요 (높을수록 빠르지만 시스템 부하 증가)", tag=self.info_tag)
        self.add_log("4️⃣ 결과 폴더 위치를 지정하세요 (기본: 프로그램 실행 위치)", tag=self.info_tag)
        self.add_log("5️⃣ '시작' 버튼을 클릭하여 작업을 시작하세요", tag=self.info_tag)
        self.add_log("")
        self.add_log("🔍 준비가 완료되면 '시작' 버튼을 눌러주세요!", tag=self.success_tag)

    def update_thread_label(self, event=None):
        self.thread_label.config(text=str(self.thread_count.get()))

    def select_folder(self):
        """결과 폴더 선택"""
        folder = filedialog.askdirectory(initialdir=self.output_folder)
        if folder:
            self.output_folder = folder
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, self.output_folder)
            self.add_log(f"📁 결과 폴더가 변경되었습니다: {self.output_folder}", tag=self.info_tag, add_timestamp=True)

    def open_output_folder(self):
        """결과 폴더 열기"""
        folder = self.folder_entry.get()
        if os.path.exists(folder):
            if os.name == 'nt':  # Windows
                os.startfile(folder)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.Popen(['open', folder])
            self.add_log(f"📂 결과 폴더를 열었습니다: {folder}", tag=self.info_tag, add_timestamp=True)
        else:
            messagebox.showerror("오류", "지정된 폴더가 존재하지 않습니다.")

    def exit_application(self):
        """프로그램 종료"""
        if self.is_running:
            if messagebox.askyesno("경고", "작업이 진행 중입니다. 정말 종료하시겠습니까?"):
                self.stop_scraping()
                self.root.after(500, self.root.destroy)
        else:
            self.root.destroy()

    def add_log(self, message, tag=None, replace_last=False, add_timestamp=False):
        """로그 큐에 메시지 추가"""
        if add_timestamp:
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            message = timestamp + message
        self.log_queue.put((message, tag, replace_last))

    def update_log_from_queue(self):
        """큐에서 로그 메시지를 가져와 로그 창에 표시"""
        try:
            while not self.log_queue.empty():
                message, tag, replace_last = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)

                if replace_last:
                    # 마지막 라인 찾기
                    last_line_start = self.log_text.index("end-1c linestart")
                    last_line_end = self.log_text.index("end-1c")

                    # 마지막 라인이 특정 태그를 가진 경우 삭제
                    if tag and self.log_text.tag_ranges(tag):
                        tag_ranges = self.log_text.tag_ranges(tag)
                        if tag_ranges:
                            self.log_text.delete(tag_ranges[0], tag_ranges[1])

                    # 새 메시지 추가
                    self.log_text.insert(tk.END, message + "\n", tag)
                else:
                    # 일반 메시지 추가
                    self.log_text.insert(tk.END, message + "\n", tag)

                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        finally:
            # 100ms마다 큐 확인
            self.root.after(100, self.update_log_from_queue)

    def update_progress(self, value):
        """프로그레스 바 업데이트"""
        self.progress_bar["value"] = value
        self.root.update_idletasks()

    def start_scraping(self):
        """스크래핑 시작"""
        # 입력 검증
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("오류", "YouTube 채널 링크를 입력해주세요.")
            return

        # 결과 폴더 확인
        self.output_folder = self.folder_entry.get().strip()
        if not os.path.exists(self.output_folder):
            try:
                os.makedirs(self.output_folder)
                self.add_log(f"📁 결과 폴더를 생성했습니다: {self.output_folder}", tag=self.info_tag, add_timestamp=True)
            except Exception as e:
                messagebox.showerror("오류", f"결과 폴더를 생성할 수 없습니다: {str(e)}")
                return

        # 버튼 상태 변경
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.is_running = True

        # 데이터 초기화
        self.src_list = []
        self.t_list = []
        self.href_list = []
        self.href_set = set()
        self.stop_event.clear()

        # 로그 섹션 구분선 추가
        self.add_log("")
        self.add_log("=" * 70, tag=self.header_tag)
        self.add_log("🔄 작업 시작", tag=self.header_tag)
        self.add_log(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", tag=self.info_tag)
        self.add_log("=" * 70, tag=self.header_tag)
        self.add_log("")

        # 스크래핑 스레드 시작
        self.scraping_thread = threading.Thread(target=self.scraping_thread_func, args=(url,), daemon=True)
        self.scraping_thread.start()

    def stop_scraping(self):
        """스크래핑 중지"""
        if self.is_running:
            self.stop_event.set()
            self.add_log("⚠️ 작업 중지 요청됨. 잠시만 기다려주세요...", tag=self.warning_tag, add_timestamp=True)
            self.stop_button.config(state=tk.DISABLED)

    def scraping_thread_func(self, url):
        """스크래핑 작업을 수행하는 스레드"""
        try:
            # URL 수정
            modified_url = self.modify_youtube_url(url)
            if modified_url == "잘못된 URL 입니다":
                self.add_log("❌ 올바른 유튜브 channel 링크를 입력해주세요.", tag=self.error_tag, add_timestamp=True)
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.is_running = False
                return

            self.add_log(f"🌐 {modified_url} 로 접속합니다.", tag=self.info_tag, add_timestamp=True)

            # Shorts 여부 확인
            self.is_shorts = '/shorts' in modified_url
            if self.is_shorts:
                self.add_log("📱 쇼츠(Shorts) 링크가 감지되었습니다.", tag=self.info_tag, add_timestamp=True)
            else:
                self.add_log("🎬 비디오(Videos) 링크가 감지되었습니다.", tag=self.info_tag, add_timestamp=True)

            # 크롬 드라이버 설정
            option = webdriver.ChromeOptions()
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
            option.add_argument(f"user-agent={user_agent}")
            option.add_argument(f"--headless")

            # 로그인 필요 여부
            if self.login_var.get():
                self.add_log("🔐 로그인이 필요한 것으로 확인되었습니다.", tag=self.info_tag, add_timestamp=True)
                self.add_log("   로그인 페이지로 이동합니다...", tag=self.info_tag)
                self.driver = webdriver.Chrome(options=option)
                self.driver.get("https://accounts.google.com/InteractiveLogin")

                # 로그인 대기
                self.add_log("👤 Google 계정으로 로그인을 완료한 후 확인 버튼을 눌러주세요.", tag=self.warning_tag, add_timestamp=True)

                # 로그인 확인 다이얼로그
                self.root.after(0, lambda: self.show_login_dialog())
                return
            else:
                self.add_log("🔓 로그인 없이 진행합니다.", tag=self.info_tag, add_timestamp=True)
                self.driver = webdriver.Chrome(options=option)
                self.continue_after_login(modified_url)

        except Exception as e:
            self.add_log(f"❌ 오류 발생: {str(e)}", tag=self.error_tag, add_timestamp=True)
            if self.driver:
                self.driver.quit()
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.is_running = False

    def show_login_dialog(self):
        """로그인 완료 확인 다이얼로그"""
        dialog = tk.Toplevel(self.root)
        dialog.title("로그인 확인")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # 아이콘 및 메시지
        message_frame = ttk.Frame(dialog, padding=20)
        message_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(message_frame, text="🔐 Google 로그인").pack(pady=(0, 10))
        ttk.Label(message_frame, text="로그인을 완료하셨나요?").pack(pady=(0, 20))

        # 버튼 프레임
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(0, 20))

        ttk.Button(btn_frame, text="✅ 로그인 완료",
                   command=lambda: self.on_login_complete(dialog)).pack(side=tk.LEFT, padx=10)

        ttk.Button(btn_frame, text="❌ 취소",
                   command=lambda: self.on_login_cancel(dialog)).pack(side=tk.LEFT, padx=10)

    def on_login_complete(self, dialog):
        """로그인 완료 후 처리"""
        dialog.destroy()
        modified_url = self.modify_youtube_url(self.url_entry.get().strip())
        self.add_log("✅ 로그인 확인 완료", tag=self.success_tag, add_timestamp=True)
        self.continue_after_login(modified_url)

    def on_login_cancel(self, dialog):
        """로그인 취소 처리"""
        dialog.destroy()
        if self.driver:
            self.driver.quit()
        self.add_log("❌ 작업이 취소되었습니다.", tag=self.error_tag, add_timestamp=True)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.is_running = False

    def continue_after_login(self, url):
        """로그인 후 스크래핑 계속 진행"""
        try:
            self.update_progress(5)
            self.add_log("🔍 데이터를 살피는 중...", tag=self.info_tag, add_timestamp=True)

            # 페이지 접속
            self.driver.get(url)
            time.sleep(1)

            # 중지 확인
            if self.stop_event.is_set():
                raise Exception("사용자에 의해 작업이 중지되었습니다.")

            # 스크롤 다운하여 더 많은 컨텐츠 로드
            self.add_log("📜 컨텐츠를 로드하기 위해 스크롤 중...", tag=self.info_tag, add_timestamp=True)
            self.update_progress(10)

            last_scroll_position = self.driver.execute_script("return window.scrollY")
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
            time.sleep(0.5)

            scroll_count = 0
            max_scrolls = 50000  # 최대 스크롤 횟수 제한

            # 스크롤 진행 상황 초기 메시지
            self.add_log(f"📜 스크롤 진행 중... (0/{max_scrolls})",
                        tag=self.scroll_progress_tag)

            # 현재 스크롤 위치를 다시 가져와서 비교
            while scroll_count < max_scrolls and not self.stop_event.is_set():
                current_scroll_position = self.driver.execute_script("return window.scrollY")
                if current_scroll_position == last_scroll_position:
                    break
                else:
                    last_scroll_position = current_scroll_position
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                    time.sleep(0.5)
                    scroll_count += 1

                    # 진행률 업데이트 (10~25%)
                    progress = 10 + (scroll_count / max_scrolls) * 15
                    self.update_progress(progress)

                    # 스크롤 진행 상황 업데이트 (5번마다)
                    if scroll_count % 5 == 0:
                        self.add_log(f"📜 스크롤 진행 중... ({scroll_count}/최대 {max_scrolls})",
                                     tag=self.scroll_progress_tag, replace_last=True)

            # 중지 확인
            if self.stop_event.is_set():
                raise Exception("사용자에 의해 작업이 중지되었습니다.")

            self.add_log("🔄 데이터를 추출 중입니다...", tag=self.info_tag, add_timestamp=True)
            self.update_progress(25)

            # HTML 파싱
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # 데이터 추출
            if self.is_shorts:
                self.add_log("📱 쇼츠 데이터를 분석 중...", tag=self.info_tag, add_timestamp=True)
                self.find_shorts_data(soup)
            else:
                self.add_log("🎬 비디오 데이터를 분석 중...", tag=self.info_tag, add_timestamp=True)
                self.find_videos_data(soup)

            # 중지 확인
            if self.stop_event.is_set():
                raise Exception("사용자에 의해 작업이 중지되었습니다.")

            # 영상 주소 완성
            self.complete_video_urls()

            # 데이터 길이 확인 및 출력
            src_list_length = len(self.src_list)

            self.add_log("", tag=self.info_tag)
            self.add_log("📊 데이터 추출 결과:", tag=self.header_tag, add_timestamp=True)
            self.add_log(f"   🖼️ 이미지 링크 수: {src_list_length}개", tag=self.info_tag)
            self.add_log(f"   📝 제목 수: {len(self.t_list)}개", tag=self.info_tag)
            self.add_log(f"   🔗 영상 주소 수: {len(self.href_list)}개", tag=self.info_tag)

            # 이미지 링크 수가 제목 수보다 정확히 1개 더 많은 경우 첫 번째 이미지 링크 제외
            if len(self.src_list) == len(self.t_list) + 1 and len(self.src_list) == len(self.href_list) + 1:
                self.add_log("⚠️ '대문'이미지가 포함되어있는 것으로 보입니다. 첫 번째 이미지 링크를 제외합니다.",
                             tag=self.warning_tag, add_timestamp=True)
                self.src_list = self.src_list[1:]
                src_list_length = len(self.src_list)
                self.add_log(f"   🖼️ 조정된 이미지 링크 수: {src_list_length}개", tag=self.info_tag)

            # 데이터 길이 맞추기 (가장 짧은 리스트 기준)
            min_length = min(len(self.src_list), len(self.t_list), len(self.href_list))
            if min_length < src_list_length:
                self.add_log(f"⚠️ 일부 데이터가 불완전하여 {min_length}개 항목만 처리합니다.",
                             tag=self.warning_tag, add_timestamp=True)

            self.src_list = self.src_list[:min_length]
            self.t_list = self.t_list[:min_length]
            self.href_list = self.href_list[:min_length]

            self.update_progress(40)

            # 중지 확인
            if self.stop_event.is_set():
                raise Exception("사용자에 의해 작업이 중지되었습니다.")

            # 엑셀 파일 저장
            self.add_log("", tag=self.info_tag)
            self.add_log("📊 엑셀 파일로 데이터를 저장 중...", tag=self.info_tag, add_timestamp=True)
            self.save_to_excel()
            self.update_progress(50)

            # 중지 확인
            if self.stop_event.is_set():
                raise Exception("사용자에 의해 작업이 중지되었습니다.")

            # 이미지 다운로드
            self.add_log("", tag=self.info_tag)
            self.add_log("🖼️ 썸네일 이미지 다운로드", tag=self.header_tag, add_timestamp=True)
            self.download_images()

            # 완료
            self.add_log("", tag=self.info_tag)
            self.add_log("=" * 70, tag=self.header_tag)
            self.add_log("✅ 모든 작업이 완료되었습니다!", tag=self.success_tag, add_timestamp=True)
            self.add_log("=" * 70, tag=self.header_tag)

            self.update_progress(100)
            messagebox.showinfo("완료", "데이터 추출 및 이미지 다운로드가 완료되었습니다.")

        except Exception as e:
            if "사용자에 의해 작업이 중지되었습니다" in str(e):
                self.add_log(f"⚠️ {str(e)}", tag=self.warning_tag, add_timestamp=True)
            else:
                self.add_log(f"❌ 오류 발생: {str(e)}", tag=self.error_tag, add_timestamp=True)

        finally:
            if self.driver:
                self.driver.quit()
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.is_running = False

    def modify_youtube_url(self, url):
        """YouTube URL 수정"""
        # 기본 URL 형식 확인
        if "youtube.com/@" in url:
            # "@" 이후에 "/"가 있는 경우
            match = re.search(r"@([^/]+)/?", url)
            if match:
                # "@" 이후 처음 나오는 "/" 까지의 부분을 추출
                username = match.group(1)

                # URL에 이미 '/shorts'가 포함되어 있는지 확인
                if '/shorts' in url:
                    modified_url = f"https://www.youtube.com/@{username}/shorts"
                # URL에 이미 '/videos'가 포함되어 있는지 확인
                elif '/videos' in url:
                    modified_url = f"https://www.youtube.com/@{username}/videos"
                else:
                    # 기본적으로 videos 탭으로 설정
                    modified_url = f"https://www.youtube.com/@{username}/videos"
            else:
                # "@" 이후에 "/"가 없는 경우 (예: https://www.youtube.com/@zuyoni1)
                username = url.split('@')[1]
                modified_url = f"https://www.youtube.com/@{username}/videos"
            return modified_url
        else:
            modified_url = "잘못된 URL 입니다"
            return modified_url

    def find_shorts_data(self, soup):
        """Shorts 데이터 추출"""
        # 모든 이미지 태그 찾기
        all_images = soup.find_all('img')

        # shorts 관련 이미지만 필터링
        for img in all_images:
            img_classes = img.get('class', [])
            if isinstance(img_classes, list):
                img_classes = ' '.join(img_classes)

            # shortsLockupViewModelHostThumbnail 클래스를 포함하거나 src에 '/vi/' 패턴이 있는 이미지 찾기
            if ('shortsLockupViewModelHostThumbnail' in img_classes or
                    (img.has_attr('src') and '/vi/' in img['src'])):
                if img.has_attr('src'):
                    self.src_list.append(img['src'])

        # 제목과 링크 찾기
        title_spans = soup.find_all('span',
                                    class_="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap",
                                    role="text")

        # 중복 방지를 위해 수정된 링크 수집 로직
        a_tags = soup.find_all('a')

        # 제목 수집
        for title_span in title_spans:
            if title_span.parent and title_span.parent.name == 'a':
                self.t_list.append(title_span.text)

        # 링크 수집 (중복 방지)
        for a_tag in a_tags:
            if a_tag.has_attr('href') and '/shorts/' in a_tag['href']:
                href = a_tag['href']
                # 중복 확인 후 추가
                if href not in self.href_set:
                    self.href_set.add(href)
                    self.href_list.append(href)

    def find_videos_data(self, soup):
        """일반 비디오 데이터 추출"""
        # img 태그이면서 class 명이 "yt-core-image yt-core-image--fill-parent-height yt-core-image--fill-parent-width yt-core-image--content-mode-scale-aspect-fill yt-core-image--loaded" 인 모든 항목들을 찾습니다.
        img_tags = soup.find_all('img',
                                 class_="yt-core-image yt-core-image--fill-parent-height yt-core-image--fill-parent-width yt-core-image--content-mode-scale-aspect-fill yt-core-image--loaded")

        # 각 항목에서 src를 뽑아냅니다.
        for img_tag in img_tags:
            if 'src' in img_tag.attrs:
                self.src_list.append(img_tag['src'])

        video_titles = soup.find_all('a', id="video-title-link")
        for video_title in video_titles:
            title = video_title.text
            href = video_title['href']
            self.t_list.append(str(title))
            # 중복 확인 후 추가
            if href not in self.href_set:
                self.href_set.add(href)
                self.href_list.append(href)

    def complete_video_urls(self):
        """영상 주소 완성"""
        for i in range(len(self.href_list)):
            # 이미 완전한 URL인지 확인
            if self.href_list[i].startswith('http'):
                continue
            # 상대 경로인 경우에만 도메인 추가
            elif self.href_list[i].startswith('/'):
                self.href_list[i] = "https://www.youtube.com" + self.href_list[i]
            else:
                self.href_list[i] = "https://www.youtube.com/" + self.href_list[i]

    def save_to_excel(self):
        """엑셀 파일로 저장"""
        data_dict = dict([(key, pd.Series(value)) for key, value in {
            "타이틀": self.t_list,
            "이미지링크": self.src_list,
            "영상주소": self.href_list
        }.items()])

        df = pd.DataFrame(data_dict)

        # Excel 파일로 저장
        file_path = os.path.join(self.output_folder, "유튜브수집.xlsx")

        # Excel 파일로 저장 _ 파일명 중복 방지
        n = 1
        while os.path.exists(file_path):
            n += 1
            file_path = os.path.join(self.output_folder, f"유튜브수집({n}).xlsx")

        df.to_excel(file_path, index=True)
        self.add_log(f"✅ 엑셀 파일 저장 완료: {file_path}", tag=self.success_tag, add_timestamp=True)

    def download_images(self):
        """이미지 다운로드"""
        # 이미지를 저장할 폴더 경로
        folder_path = os.path.join(self.output_folder, "youtube_images")

        # 폴더가 없으면 생성
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            self.add_log(f"📁 이미지 저장 폴더 생성: {folder_path}", tag=self.info_tag, add_timestamp=True)

        total_images = len(self.src_list)
        thread_count = self.thread_count.get()

        self.add_log(f"🔄 썸네일 이미지 다운로드를 시작합니다. (총 {total_images}개)",
                     tag=self.info_tag, add_timestamp=True)
        self.add_log(f"⚙️ 스레드 수: {thread_count}개", tag=self.info_tag)

        # 다운로드 진행 상황 초기화
        self.add_log(f"⏳ 썸네일 이미지를 내려받는 중입니다 - 0/{total_images} (0%)",
                     tag=self.download_progress_tag)

        # 진행 상황 업데이트를 위한 락
        progress_lock = threading.Lock()
        downloaded = [0]  # 리스트로 만들어 참조로 전달

        # 멀티스레딩으로 이미지 다운로드
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # 각 이미지에 대한 다운로드 작업 제출
            future_to_idx = {}

            for idx, src in enumerate(self.src_list):
                # 중지 확인
                if self.stop_event.is_set():
                    break

                future = executor.submit(self.download_single_image, src, idx, folder_path,
                                         total_images, downloaded, progress_lock)
                future_to_idx[future] = idx

            # 작업 완료 대기
            for future in future_to_idx:
                try:
                    # 중지 확인
                    if self.stop_event.is_set():
                        executor.shutdown(wait=False)
                        break

                    future.result()
                except Exception as e:
                    idx = future_to_idx[future]
                    self.add_log(f"⚠️ 이미지 {idx} 다운로드 실패: {str(e)}",
                                 tag=self.warning_tag, add_timestamp=True)

        # 중지 확인
        if self.stop_event.is_set():
            self.add_log(f"⚠️ 이미지 다운로드가 중단되었습니다. ({downloaded[0]}/{total_images})",
                         tag=self.warning_tag, add_timestamp=True)
        else:
            # 최종 완료 메시지
            self.add_log(f"✅ 썸네일 이미지를 내려받는 중입니다 - {total_images}/{total_images} (100%)",
                         tag=self.download_progress_tag, replace_last=True)
            self.add_log(f"✅ 이미지 다운로드 완료: {folder_path}", tag=self.success_tag, add_timestamp=True)

    def download_single_image(self, src, idx, folder_path, total_images, downloaded, progress_lock):
        """단일 이미지 다운로드 및 AVIF에서 JPG로 변환"""
        try:
            # 중지 확인
            if self.stop_event.is_set():
                return False

            response = requests.get(src)
            if response.status_code == 200:
                # 임시 파일로 저장
                temp_path = os.path.join(folder_path, f"temp_{idx}.avif")
                with open(temp_path, 'wb') as f:
                    f.write(response.content)

                # AVIF를 JPG로 변환
                try:
                    from PIL import Image
                    import pillow_avif  # 필수 import

                    img = Image.open(temp_path)
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')

                    output_path = os.path.join(folder_path, f"youtube_image_{idx}.jpg")
                    img.save(output_path, 'JPEG', quality=95)

                    # 임시 파일 삭제
                    os.remove(temp_path)
                except ImportError:
                    self.add_log(
                        f"⚠️ pillow-avif-plugin이 설치되어 있지 않습니다. pip install pillow pillow-avif-plugin 명령으로 설치하세요.",
                        tag=self.warning_tag, add_timestamp=True)
                    # 변환 실패 시 원본 그대로 저장
                    output_path = os.path.join(folder_path, f"youtube_image_{idx}.avif")
                    with open(output_path, 'wb') as f:
                        f.write(response.content)

                # 진행 상황 업데이트
                with progress_lock:
                    downloaded[0] += 1
                    current = downloaded[0]

                    # 진행률 업데이트 (50~100%)
                    progress = 50 + (current / total_images) * 50
                    self.update_progress(progress)

                    # 로그 업데이트 (10% 단위로 또는 완료 시)
                    percent = int((current / total_images) * 100)
                    if current % max(1, int(total_images / 10)) == 0 or current == total_images:
                        self.add_log(f"⏳ 썸네일 이미지를 내려받는 중입니다 - {current}/{total_images} ({percent}%)",
                                     tag=self.download_progress_tag, replace_last=True)

                return True
            return False
        except Exception as e:
            with progress_lock:
                self.add_log(f"⚠️ 이미지 {idx} 다운로드 중 오류: {str(e)}",
                             tag=self.warning_tag, add_timestamp=True)
            return False


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeScraperApp(root)
    root.mainloop()
