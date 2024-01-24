# youtube_community_comments_screenshots.py


유튜브 댓글 캡쳐 및 엑셀 파일로 내보내기 프로그램입니다
유튜브 커뮤니티를 기반으로 만들어졌습니다.
유튜브 영상, 숏츠에서도 작동은 하나 오류가 발생할 수 있습니다.
It's a program that captures comments on YouTube and exports them to Excel files
It is based on the YouTube community. YouTube videos, Shots also work, but errors can occur.

프로그램 실행 후, 추적할 url 만 넣어주세요!
please input your URL which you want!

requirments: pip install bs4, selenium, pandas, lxml
pyinstaller 제작 시, pyinstaller youtube_community_comments_screenshots.py --onefile --hidden-import bs4 --hidden-import selenium --hidden-import time --hidden-import subprocess --hidden-import pandas --hidden-import os --hidden-import re --hidden-import datetime --hidden-import lxml
