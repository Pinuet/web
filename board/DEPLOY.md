# 배포 가이드 (Ubuntu VPS 기준)

이 문서는 `board/` 앱을 외부에서 접근 가능한 VPS에 올리는 절차입니다.
Ubuntu 22.04/24.04 기준이며, gunicorn(WSGI 서버) + nginx(리버스 프록시) + systemd(자동 재시작) 조합을 씁니다.

## 0. VPS 준비

아직 서버가 없다면 아래 중 하나를 추천합니다. (과제용 데모 수준이면 가장 저렴한 사양으로 충분합니다.)

- **Oracle Cloud Free Tier**: 평생 무료 티어(암 기반 4코어/24GB 가능)가 있어 비용 부담이 없습니다. 다만 가입 시 카드 등록이 필요하고 프리티어 재고가 지역별로 부족할 때가 있습니다.
- **AWS Lightsail**: 월 3.5~5달러 수준으로 간단하게 고정 IP까지 받을 수 있어 설정이 쉽습니다.
- **네이버클라우드플랫폼**: 국내 리전이라 속도가 빠르고, 학생/신규 가입 크레딧이 있는 경우가 많습니다.

Ubuntu 22.04 LTS 이미지로 인스턴스를 만들고, SSH 키를 등록한 뒤 아래 정보를 알려주시면 제가 원격으로 배포를 진행할 수 있습니다.
- 서버 IP (또는 도메인)
- SSH 접속 계정명 (보통 `ubuntu` 또는 `root`)
- SSH 키 파일 경로 (또는 비밀번호 로그인 여부)

## 1. 서버 기본 설정

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv mysql-server nginx git
```

## 2. MySQL 준비

로컬에서 한 것과 동일하게, **root 계정을 앱에 쓰지 말고 전용 계정을 새로 만듭니다.**

```bash
sudo mysql <<'SQL'
CREATE DATABASE IF NOT EXISTS board_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'board_app'@'localhost' IDENTIFIED BY '여기에_새로운_강력한_비밀번호';
GRANT SELECT, INSERT, UPDATE, DELETE ON board_db.* TO 'board_app'@'localhost';
FLUSH PRIVILEGES;
SQL

mysql -u root -p board_db < schema.sql
```

## 3. 앱 배포

```bash
sudo mkdir -p /opt/board
sudo chown $USER:$USER /opt/board
# 로컬 board/ 폴더 전체를 이 경로로 복사 (scp, rsync, git 등 편한 방법 사용)

cd /opt/board
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env를 열어서 DB_PASSWORD 등 실제 값으로 채웁니다.
# 절대 평소 쓰는 개인 비밀번호를 재사용하지 않습니다.
```

## 4. systemd 서비스 등록 (gunicorn으로 실행, 자동 재시작)

`/etc/systemd/system/board.service` 파일을 만듭니다.

```ini
[Unit]
Description=Board Flask app (gunicorn)
After=network.target mysql.service

[Service]
User=ubuntu
WorkingDirectory=/opt/board
Environment="PATH=/opt/board/venv/bin"
ExecStart=/opt/board/venv/bin/gunicorn -w 3 -b 127.0.0.1:5050 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now board
sudo systemctl status board
```

## 5. nginx 설정 (포트폴리오 정적 사이트 + 게시판 프록시를 한 도메인에서)

index.html의 상단 메뉴에서 "게시판"을 누르면 `/board/posts`로 이동하도록
만들어뒀습니다. 그래서 nginx도 두 가지를 같이 처리해야 합니다.
- `/` : 포트폴리오 정적 파일 (`index.html`, `css/`, `js/`, `images/`)
- `/board/` : Flask 게시판 앱으로 프록시 (경로를 자르지 않고 그대로 전달 — 앱 쪽 라우트가 이미 `/board`로 시작하기 때문입니다)

먼저 정적 사이트 파일을 서버로 복사합니다. (`index.html`, `css/`, `js/`, `images/` 폴더를 예: `/var/www/portfolio`에 업로드)

`/etc/nginx/sites-available/board`:

```nginx
server {
    listen 80;
    server_name 서버_IP_또는_도메인;

    root /var/www/portfolio;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /board/ {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/board /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 6. 방화벽

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

이제 `http://서버_IP/` 에서 포트폴리오가, 상단 메뉴의 "게시판"을 누르면
`http://서버_IP/board/posts` 로 외부에서 접속할 수 있습니다.

## 7. (선택) HTTPS

도메인이 있다면 Let's Encrypt로 무료 인증서를 붙일 수 있습니다.

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 체크리스트 (과제 필독사항 재확인)

- [x] sqlalchemy 등 ORM 미사용, pymysql로 SQL 직접 작성 (`db.py`, `app.py`)
- [x] DB 비밀번호는 `.env`에서 로드, 코드에 하드코딩하지 않음 (`.gitignore`로 커밋 제외)
- [x] 평소 쓰는 개인 비밀번호 대신 이 프로젝트 전용 새 계정/비밀번호 사용
- [x] 게시판 CRUD (생성/조회/수정/삭제) 구현
- [x] 검색 기능 (제목/내용/전체) 구현
