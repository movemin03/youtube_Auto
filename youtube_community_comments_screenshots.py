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
ver = str("2024-01-24")
chrome_ver = 120
user = os.getlogin()
upper_path = 'C:\\Users\\' + user + '\\Desktop'
print("유튜브 커뮤니티 댓글 자동 수집기")
print("파일은 " + upper_path + "와 screenshots 폴더에 저장됩니다")
#youtube_url = 'https://www.youtube.com/post/UgkxpfyPg1-lXDA6_9Zn2IabV_ugfSaoGq6A'
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
yt_formatted_strings = soup.find_all('yt-formatted-string', class_='style-scope ytd-comment-renderer style-scope ytd-comment-renderer')
for yt_formatted_string in yt_formatted_strings:
    text = yt_formatted_string.get_text().replace(",", "")
    cleaned_text = re.sub(r"[^a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣0-9\s]", "", text)
    str_youtube_userIDs.append(text)
str_youtube_comments = []
yt_formatted_strings = soup.find_all('yt-formatted-string', class_='style-scope ytd-comment-renderer')
for yt_formatted_string in yt_formatted_strings:
    text = yt_formatted_string.get_text().replace(",", "")
    cleaned_text = re.sub(r"[^a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣0-9\s]", "", text)
    str_youtube_comments.append(text)


## MODIFY VIEW FORMAT
print("youtube_userIDs 갯수: " + str(len(str_youtube_userIDs)))
print("str_youtube_comments 갯수: " + str(len(str_youtube_comments)))
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
