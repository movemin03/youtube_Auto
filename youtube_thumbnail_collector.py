# Standard library imports
import re
import os
import time
import requests

# Third party imports
import lxml
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def sleep_short():
    start_time1 = time.time()
    target_time = start_time1 + 0.5
    while time.time() < target_time:
        pass


# 사용자 정의
ver = str("2024-04-25 18:00:00")
user = os.getlogin()  # 유저 아이디(현재 자동 입력 중)

# 크롬 드라이버 디버깅 모드 실행
option = webdriver.ChromeOptions()
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
option.add_argument(f"user-agent={user_agent}")

# 시작
print("\n")
print("유튜브 영상 정보 및 썸네일 추출 프로그램입니다 " + ver)
print("접속할 유튜브에 로그인이 필요합니까? y / n")
print("해당 유튜브 채널의 소유주일 경우에는 y 를 권장합니다 (비밀 댓글도 수집할 수 있습니다)")
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
print("\n접속할 유튜브 링크 url 입력해야합니다. 비디오 탭 또는 shorts 탭 링크를 입력하세요")
print("예: https://www.youtube.com/@thinkgood638/videos 또는 https://www.youtube.com/@Knocpr/shorts")


def modify_youtube_url(url):
    if "www.youtube.com/@" in url:
        # "@" 이후에 "/"가 있는 경우
        match = re.search(r"@([^/]+)/?", url)
        if match:
            # "@" 이후 처음 나오는 "/" 까지의 부분을 추출
            username = match.group(1)

            # URL에 이미 '/shorts'가 포함되어 있는지 확인
            if '/shorts' in url:
                modified_url = f"https://www.youtube.com/@{username}/shorts"
            else:
                # 기본적으로 videos 탭으로 설정
                modified_url = f"https://www.youtube.com/@{username}/videos"
        else:
            # "@" 이후에 "/"가 없는 경우
            modified_url = url + "/videos"
        return modified_url
    else:
        modified_url = "잘못된 URL 입니다"
        return modified_url


while True:
    url = input("주소를 입력:")
    modified_url = modify_youtube_url(url)
    if modified_url == "잘못된 URL 입니다":
        print("올바른 유튜브 channel 링크를 주셔야 합니다")
        continue
    else:
        print(modified_url, "로 접속합니다")
        break

# URL에서 shorts 여부 확인
is_shorts = '/shorts' in modified_url

# 저장소 생성
src_list = []
t_list = []
href_list = []
# 중복 링크 확인을 위한 집합 추가
href_set = set()

print("프로그램 실행여부 확인 중")
driver.get(modified_url)
a = input("데이터 로딩을 시작할까요?")

print("데이터를 살피는 중")
time.sleep(1)

# 스크롤 다운하여 더 많은 컨텐츠 로드
last_scroll_position = driver.execute_script("return window.scrollY")
driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
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


def find_shorts_data():
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
                src_list.append(img['src'])

    # 제목과 링크 찾기
    title_spans = soup.find_all('span',
                                class_="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap",
                                role="text")

    # 중복 방지를 위해 수정된 링크 수집 로직
    a_tags = soup.find_all('a')

    # 제목 수집
    for title_span in title_spans:
        if title_span.parent and title_span.parent.name == 'a':
            t_list.append(title_span.text)

    # 링크 수집 (중복 방지)
    for a_tag in a_tags:
        if a_tag.has_attr('href') and '/shorts/' in a_tag['href']:
            href = a_tag['href']
            # 중복 확인 후 추가
            if href not in href_set:
                href_set.add(href)
                href_list.append(href)


def find_videos_data():
    # 일반 비디오 데이터 추출 로직
    # img 태그이면서 class 명이 "yt-core-image yt-core-image--fill-parent-height yt-core-image--fill-parent-width yt-core-image--content-mode-scale-aspect-fill yt-core-image--loaded" 인 모든 항목들을 찾습니다.
    img_tags = soup.find_all('img',
                             class_="yt-core-image yt-core-image--fill-parent-height yt-core-image--fill-parent-width yt-core-image--content-mode-scale-aspect-fill yt-core-image--loaded")

    # 각 항목에서 src를 뽑아냅니다.
    for img_tag in img_tags:
        if 'src' in img_tag.attrs:
            src_list.append(img_tag['src'])

    video_titles = soup.find_all('a', id="video-title-link")
    for video_title in video_titles:
        title = video_title.text
        href = video_title['href']
        t_list.append(str(title))
        # 중복 확인 후 추가
        if href not in href_set:
            href_set.add(href)
            href_list.append(href)


# URL에 따라 적절한 데이터 추출 함수 호출
if is_shorts:
    find_shorts_data()
else:
    find_videos_data()

# 영상 주소 완성 - 중복 방지
for i in range(len(href_list)):
    # 이미 완전한 URL인지 확인
    if href_list[i].startswith('http'):
        continue
    # 상대 경로인 경우에만 도메인 추가
    elif href_list[i].startswith('/'):
        href_list[i] = "https://www.youtube.com" + href_list[i]
    else:
        href_list[i] = "https://www.youtube.com/" + href_list[i]

# 리스트 길이 확인 및 출력
src_list_length = len(src_list)
print(f"이미지 링크 수: {src_list_length}")
print(f"제목 수: {len(t_list)}")
print(f"영상 주소 수: {len(href_list)}")

# 데이터 길이 맞추기 (가장 짧은 리스트 기준)
min_length = min(len(src_list), len(t_list), len(href_list))
src_list = src_list[:min_length]
t_list = t_list[:min_length]
href_list = href_list[:min_length]

# 데이터프레임으로 변환
print("엑셀 파일 수집이 완료되어 바탕화면에 파일로 저장합니다")

data_dict = dict([(key, pd.Series(value)) for key, value in {
    "타이틀": t_list,
    "이미지링크": src_list,
    "영상주소": href_list
}.items()])

df = pd.DataFrame(data_dict)
# 영상 주소는 이미 완성되어 있으므로 추가 처리 불필요

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
    print(str(int(src_list_length) - int(idx)), "항목 남았습니다")
    response = requests.get(src)
    if response.status_code == 200:
        with open(os.path.join(folder_path, f"youtube_image_{idx}.jpg"), 'wb') as f:
            f.write(response.content)

print(folder_path, " 위치에 저장 완료되었습니다")

driver.quit()
a = input("아무키나 입력하면 종료됩니다")
exit()
