# youtube_Auto

youtube_Auto is a comprehensive program consisting of three components designed to streamline various tasks related to managing YouTube content and community interactions.

## 1. youtube_community_comments_screenshots.py

**Description:**
This program captures YouTube comments and exports them to Excel files. It is specifically tailored for YouTube community interactions. While it operates seamlessly on YouTube videos and Shorts, occasional errors may occur.

**Usage:**
After running the program, simply input the URL you wish to track!

**Requirements:**
- pip install bs4, selenium, pandas, lxml

**Exporting as Executable:**
For PyInstaller, use the following command:
```cmd
pyinstaller youtube_community_comments_screenshots.py --onefile --hidden-import bs4 --hidden-import selenium --hidden-import time --hidden-import subprocess --hidden-import pandas --hidden-import os --hidden-import re --hidden-import datetime --hidden-import lxml
```

## 2. youtube_community_comments_screenshots.py
**Description:**
Extracts thumbnails, titles, and video links from videos on the YouTube video tab.

## 3. youtube_thumbnail_distributor_by_Color.py
**Description:**
Classifies extracted thumbnail files based on specific color criteria. The default value is red.
---
# youtube_Auto(한국어 설명)

youtube_Auto는 유튜브 콘텐츠 및 커뮤니티 상호작용 관련 다양한 작업을 효율적으로 처리하기 위해 구성된 포괄적인 프로그램입니다.

## 1. youtube_community_comments_screenshots.py

**설명:**
이 프로그램은 유튜브 댓글을 캡처하여 엑셀 파일로 내보냅니다. 유튜브 커뮤니티 상호작용을 위해 특별히 제작되었습니다. 유튜브 동영상 및 숏츠에서도 작동하지만 가끔 오류가 발생할 수 있습니다.

**사용 방법:**
프로그램을 실행한 후 추적하려는 URL을 입력하십시오!

**요구 사항:**
- pip install bs4, selenium, pandas, lxml

**실행 파일로 내보내기:**
PyInstaller를 사용하여 다음 명령을 사용합니다:
```cmd
pyinstaller 유튜브_커뮤니티_댓글_스크린샷.py --onefile --hidden-import bs4 --hidden-import selenium --hidden-import time --hidden-import subprocess --hidden-import pandas --hidden-import os --hidden-import re --hidden-import datetime --hidden-import lxml
```

## 2. youtube_community_comments_screenshots.py
**설명:**
유튜브 비디오 탭에 있는 영상들의 썸네일과 제목, 영상 링크를 추출합니다.

## 3. youtube_thumbnail_distributor_by_Color.py
**설명:**
추출된 썸네일 파일들을 특정 색상 기준에 따라 분류합니다. 기본 분류 값은 빨간색입니다. 


