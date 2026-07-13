"""
db.py
pymysql로 DB에 연결하는 부분만 따로 뺐습니다. app.py에서 매번 접속 정보를
쓰기 귀찮기도 하고, 비밀번호가 여기저기 흩어져 있으면 나중에 관리하기
힘들 것 같아서 한 곳에 모아뒀습니다.

ORM은 안 쓰고, SQL 문장은 app.py에서 직접 작성해서 실행합니다.

DB 접속 정보(비밀번호 포함)는 .env 파일에서 읽어옵니다. 비밀번호를 코드에
그대로 적으면 깃허브에 올릴 때 같이 올라가버릴 수 있어서, .env로 따로 빼고
.gitignore에 넣어서 커밋되지 않게 했습니다.
"""
import os

import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        charset="utf8mb4",  # 한글이 깨지지 않게 utf8mb4로 맞춰줍니다.
        cursorclass=pymysql.cursors.DictCursor,  # 결과를 딕셔너리로 받아서 post["title"]처럼 쓰기 편하게 했습니다.
    )
