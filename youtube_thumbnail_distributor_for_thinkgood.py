import os
from PIL import Image
from multiprocessing import Pool, cpu_count

# 폴더 생성 함수
def create_folder_if_not_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

# 이미지 파일에서 특정 좌표의 색상을 가져오는 함수
def get_pixel_color(image_path, x, y):
    try:
        image = Image.open(image_path)
        pixel_color = image.getpixel((x, y))
        return pixel_color
    except Exception as e:
        print("오류 발생:", e)
        return None

# 파일 처리 함수
def process_file(file_path):
    try:
        file_name = os.path.basename(file_path)
        color = get_pixel_color(file_path, 4, 3)
        print()
        if red_range[0][0] <= color[0] <= red_range[1][0] and \
           red_range[0][1] >= color[1] >= red_range[1][1] and \
           red_range[0][2] >= color[2] >= red_range[1][2]:
            os.rename(file_path, os.path.join(folder_path_2, file_name))
        else:
            os.rename(file_path, os.path.join(folder_path_1, file_name))
    except Exception as e:
        print("오류 발생:", e)


user = os.getlogin()  # 유저 아이디(현재 자동 입력 중)
# 폴더 경로 생성
folder_path_1 = f"C:\\Users\\{user}\\Desktop\\youtube_images\\씽굿연구소"
folder_path_2 = f"C:\\Users\\{user}\\Desktop\\youtube_images\\씽굿크리에이터"
# 빨간색 범위 정의
red_range = [(200, 50, 50), (255, 0, 0)]  # 예: R: 200 이상, G, B: 50 이하
# ver
ver = str("2024-04-28 01:00:00")

if __name__ == "__main__":
    print("씽굿연구소/크리에이터 분류 프로그램입니다")
    print("ver:", ver)
    # 이미지 파일이 있는 폴더 경로
    image_folder_path = f"C:\\Users\\{user}\\Desktop\\youtube_images"

    print("경로는 다음과 같은 위치로 기본 설정 설정되어있습니다:", image_folder_path)
    print("바탕화면에 youtube_images 폴더가 없는 경우 생성 후 썸네일 이미지들을 넣어주십시오")
    a = input("준비 완료 되었다면 엔터")

    create_folder_if_not_exists(folder_path_1)
    create_folder_if_not_exists(folder_path_2)

    # 파일 목록 가져오기
    file_list = [os.path.join(image_folder_path, file_name) for file_name in os.listdir(image_folder_path) if file_name.endswith(".jpg")]

    # CPU 코어 수만큼 풀 생성
    pool_count = cpu_count()  # CPU 코어 수
    with Pool(processes=pool_count) as pool:
        pool.map(process_file, file_list)

    print("\n이미지 처리 완료되었습니다. 아무거나 입력 후 엔터하면 종료됩니다")
    a = input()
