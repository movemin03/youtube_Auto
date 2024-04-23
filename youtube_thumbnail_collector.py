# Standard library imports
import os
import time
import lxml
import requests

# Third party imports
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

def sleep_short():
    start_time1 = time.time()
    target_time = start_time1 + 0.5
    while time.time() < target_time:
        pass


# 사용자 정의
ver = str("2024-04-23 18:00:00")
user = os.getlogin()  # 유저 아이디(현재 자동 입력 중)

# 크롬 드라이버 디버깅 모드 실행
option = webdriver.ChromeOptions()
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36"
option.add_argument(f"user-agent={user_agent}")

# 시작
print("\n")
print("유튜브 영상 정보 및 썸네일 추출 프로그램입니다 " + ver)
print("접속할 블로그에 로그인이 필요합니까? y / n")
print("해당 블로그의 소유주일 경우에는 y 를 권장합니다 (비밀 댓글도 수집할 수 있습니다)")
a = input()
if a == "y":
    print("로그인이 필요한 것으로 확인되었습니다")
    driver = webdriver.Chrome(options=option)
    driver.get("https://accounts.google.com/InteractiveLogin")
    print("로그인 진행 완료 후 아무값이나 입력해주세요")
    a = input()
else:
    print("로그인이 필요 없는 것으로 확인되었습니다")
    driver = webdriver.Chrome(options=option)

wait_s = WebDriverWait(driver, 10)
print("\n접속할 유튜브 비디오 링크 url 입력해야합니다. 반드시 비디오 탭 링크를 주셔야 합니다")
print("예: https://www.youtube.com/@thinkgood638/videos")

while True:
    url = input("주소를 입력:")
    if "youtube.com/" in url and "/videos" in url:
        break
    else:
        print("반드시 비디오 탭 링크를 주셔야 합니다")
        continue

# 저장소 생성
c_list = []

print("프로그램 실행여부 확인 중")
# 프로그램이 완전히 켜질 때까지 대기
while True:
    try:
        driver.get(url)
        driver.execute_script("var script = document.createElement('script');\
                              script.src = 'https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&callback=initMap';\
                              script.defer = true;\
                              document.head.appendChild(script);")
        break
    except:
        sleep_short()

print("데이터를 살피는 중")
time.sleep(1)

last_scroll_position = driver.execute_script("return window.scrollY")
driver.find_element(By.TAG_NAME , 'body').send_keys(Keys.PAGE_DOWN)
sleep_short()

# 현재 스크롤 위치를 다시 가져와서 비교
while True:
    current_scroll_position = driver.execute_script("return window.scrollY")
    if current_scroll_position == last_scroll_position:
        break
    else:
        last_scroll_position = current_scroll_position
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
        sleep_short()

time.sleep(1)

print("데이터를 읽어들이는 중")
html = driver.page_source
soup = BeautifulSoup(html, 'lxml')
driver.quit()

# 저장소 생성
src_list = []
t_list = []
href_list = []


def find_data():

    # img 태그이면서 class 명이 "yt-core-image yt-core-image--fill-parent-height yt-core-image--fill-parent-width yt-core-image--content-mode-scale-aspect-fill yt-core-image--loaded" 인 모든 항목들을 찾습니다.
    img_tags = soup.find_all('img',
                             class_="yt-core-image yt-core-image--fill-parent-height yt-core-image--fill-parent-width yt-core-image--content-mode-scale-aspect-fill yt-core-image--loaded")

    # 각 항목에서 src를 뽑아냅니다.
    for img_tag in img_tags:
        src = img_tag['src']


        src_list.append(src)

    video_titles = soup.find_all('a', id="video-title-link")
    for video_title in video_titles:
        title = video_title.text
        href = video_title['href']
        t_list.append("https://www.youtube.com" + title)
        href_list.append(href)

find_data()

print(len(src_list))
print(len(t_list))
print(len(href_list))

# 데이터프레임으로 변환
print("엑셀 파일 수집이 완료되어 바탕화면에 파일로 저장합니다")
df = pd.DataFrame({"타이틀": t_list, "이미지링크": src_list, "영상주소": href_list})

# Excel 파일로 저장
file_path = "C:\\Users\\" + user + "\\Desktop\\유튜브수집.xlsx"

# Excel 파일로 저장 _ 파일명 중복 방지
n = 1
while os.path.exists(file_path):
    n += 1
    file_path = f"C:\\Users\\{user}\\Desktop\\유튜브수집({n}).xlsx"

df.to_excel(file_path, index=True)
print(file_path, " 위치에 저장 완료되었습니다")

print("썸네일 이미지 파일들을 다운로드 받는 중입니다")

# 이미지를 저장할 폴더 경로
folder_path = "C:\\Users\\" + user + "\\Desktop\\youtube_images\\"

# 폴더가 없으면 생성
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# 이미지 다운로드 및 저장
for idx, src in enumerate(src_list):
    response = requests.get(src)
    if response.status_code == 200:
        with open(os.path.join(folder_path, f"youtube_image_{idx}.jpg"), 'wb') as f:
            f.write(response.content)

print(folder_path, " 위치에 저장 완료되었습니다")

driver.quit()
a = input("아무키나 입력하면 종료됩니다")
exit()
