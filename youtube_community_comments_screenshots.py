from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import subprocess
import pandas as pd
import os
import re
from datetime import datetime
import lxml


# 사용자가 환경에 따라 변경해야 할 값
ver = str("2024-02-22")
chrome_ver = 120
user = os.getlogin()
upper_path = 'C:\\Users\\' + user + '\\Desktop'
print("유튜브 댓글 자동 수집기")
print("https://github.com/movemin03/youtube_comments")
print("본 프로그램은 유튜브 커뮤니티를 기준으로 만들어졌습니다")
print("파일은 " + upper_path + "와 screenshots 폴더에 저장됩니다")

#youtube_url = 'https://www.youtube.com/shorts/sZi87-UR2H8'
print("추적할 유튜브 커뮤니티 url 을 아래에 입력해주세요")
youtube_url = input().replace(" ", "").replace("'", "").replace('"', "")

# 크롬드라이버 디버깅 모드 실행
user = os.getlogin()
subprocess.Popen(
    r'C:\Program Files\Google\Chrome\Application\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\Users\\' + user + r'\\AppData\\Local\\Google\\Chrome\\User Data"')
option = Options()
option.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=option)
driver.get(youtube_url)

if "www.youtube.com/shorts" in youtube_url:
    print("주의!!!!! 숏츠 링크를 입력하신 것으로 보입니다")
    print("숏츠의 댓글창을 열어주십시오")
    print("숏츠 url 도 가능은 하지만 설명란의 글도 엑셀 파일에 포함이 되는 오류가 있습니다")
    print("이 경우 아이디와 댓글의 순서가 한 칸 밀릴 수 있습니다. 설명란의 글은 보통 맨 아래에 포함됩니다\n")
    print("엔터를 눌러주세요")
    a = input()
elif "/post" or "/channel" in youtube_url:
    print("커뮤니티 링크를 입력하신 것으로 보입니다")
    print("로딩 확인 후 엔터")
    a = input()
else:
    print("주의!!!!! 일반 유튜브 영상 링크를 입력하신 것으로 보입니다")
    print("일반 유튜브도 가능은 하지만 설명란의 글도 엑셀 파일에 포함이 되는 오류가 있습니다")
    print("이 경우 아이디와 댓글의 순서가 한 칸 밀릴 수 있습니다. 설명란의 글은 보통 맨 아래에 포함됩니다\n")
    print("엔터를 눌러주세요")
    a = input()
start = time.time()

folder_path = upper_path + "\\screenshots"
if not os.path.exists(folder_path):
    os.makedirs(folder_path)
    print("폴더가 생성되었습니다.")
else:
    print("이미 폴더가 존재합니다.")

def get_available_filename(path):
    base_dir = os.path.dirname(path)
    base_name = os.path.basename(path)
    name, ext = os.path.splitext(base_name)
    i = 1
    while os.path.exists(path):
        new_name = f"{name}{i}{ext}"
        path = os.path.join(base_dir, new_name)
        i += 1
    return path

def save_img(driver):
    yt_formatted_strings = driver.find_elements(By.XPATH ,'//*[@id="body"]')
    for yt_formatted_string in yt_formatted_strings:
        text = yt_formatted_string.text
        if not text:
            pass
        else:
            screenshot_path = os.path.join(folder_path, "screenshot.png")
            screenshot_path = get_available_filename(screenshot_path)
            driver.save_screenshot(screenshot_path)
            element_png = yt_formatted_string.screenshot_as_png
            try:
                with open(screenshot_path, "wb") as file:
                    file.write(element_png)
            except OSError:
                pattern = r'screenshots(\d+)\.png'
                match = re.search(pattern, screenshot_path)
                if match:
                    extracted_num = int(match.group(1))
                    new_num = extracted_num + 1
                    screenshot_path = screenshot_path.replace(f'screenshots{extracted_num}.png',f'screenshots{new_num}.png')
                    with open(screenshot_path, "wb") as file:
                        file.write(element_png)

        print("이미지 저장함")

def scroll(driver):
    last_page_height = driver.execute_script("return document.documentElement.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(1.0)  # 인터발 1이상으로 줘야 데이터 취득가능(롤링시 데이터 로딩 시간 때문)
        new_page_height = driver.execute_script("return document.documentElement.scrollHeight")

        if new_page_height == last_page_height:
            break
        last_page_height = new_page_height
scroll(driver)
html_source = driver.page_source
save_img(driver)
driver.close()

# HTML 태크 크롤링 작업
soup = BeautifulSoup(html_source, "lxml")
str_youtube_userIDs = []
yt_formatted_strings = soup.find_all('a', id='author-text')
print(len(yt_formatted_strings))
for yt_formatted_string in yt_formatted_strings:
    text = yt_formatted_string.get_text().replace(",", "").replace("\n", "")
    if "@" in text:
        cleaned_text = re.sub(r"[^a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣0-9\s-]", "", text).replace(" ", "")
        str_youtube_userIDs.append(cleaned_text)

str_youtube_comments = []
yt_formatted_strings = soup.find_all('ytd-expander', id='expander')
print(len(yt_formatted_strings))
for yt_formatted_string in yt_formatted_strings:
    text = yt_formatted_string.get_text().replace(",", "").replace("\n", "").replace("간략히", "").replace("자세히 보기", "")
    cleaned_text = re.sub(r"[^a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣0-9\s]", "", text)
    str_youtube_comments.append(text)


## MODIFY VIEW FORMAT
print("youtube_userIDs 갯수: " + str(len(str_youtube_userIDs)))
print("str_youtube_comments 갯수: " + str(len(str_youtube_comments)))
if len(str_youtube_userIDs) < len(str_youtube_comments):
    diff = len(str_youtube_comments) - len(str_youtube_userIDs)
    str_youtube_userIDs = [None] * diff + str_youtube_userIDs
elif len(str_youtube_userIDs) > len(str_youtube_comments):
    diff = len(str_youtube_userIDs) - len(str_youtube_comments)
    str_youtube_comments = [None] * diff + str_youtube_comments

df = pd.DataFrame({'ID': str_youtube_userIDs, 'comment': str_youtube_comments})
youtube_pd = pd.DataFrame(df)

## WRITE TO EXCEL
now = datetime.now()
formatted_date = now.strftime("%y%m%d_%H_%M")
excel_name = upper_path + "\\유튜브댓글수집" + str(formatted_date) + ".xlsx"
youtube_pd.to_excel(excel_name, sheet_name="sheet1", index=True)
print("Running Time : ", time.time() - start,  " 초 소모됨")
print(excel_name + "에 엑셀파일이 저장되었습니다")
a = input()
