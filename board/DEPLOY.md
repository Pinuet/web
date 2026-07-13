# 배포하면서 정리한 메모

게시판을 외부에서 접속되게 하려고 네이버클라우드에 서버를 하나 만들어서 올렸는데,
그 과정에서 이것저것 검색해가며 겪은 걸 나중에 또 까먹을까봐 정리해둔 개인 메모입니다.
(제출용 문서는 아니고 저 혼자 보려고 남겨둔 거라 깃허브에는 안 올렸습니다.)

서버는 네이버클라우드플랫폼 Micro 서버(Ubuntu 24.04, vCPU 1개, 메모리 1GB, 10GB)로 만들었습니다.

## 1. 스왑 만들기

메모리가 1GB밖에 안 되는 서버라 뭘 설치하다가 멈추거나 그럴까봐, 스왑부터 만들어두는 게
좋다고 해서 먼저 했습니다.

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. 패키지 업데이트하다가 걸린 문제

```bash
sudo apt update && sudo apt upgrade -y
```

이걸 돌렸는데 `linux-firmware`라는 패키지(560MB짜리, 하드웨어 드라이버용이라 가상서버엔 필요없다고 함)가 계속 다운로드에 실패하면서 업그레이드가 안 끝났습니다. 검색해보니 이럴 땐 그냥 이 패키지만 빼고 넘어가면 된다고 해서 이렇게 했습니다.

```bash
sudo apt-mark hold linux-firmware
```

그다음 필요한 것들 설치.

```bash
sudo apt install -y python3-pip python3-venv mysql-server nginx git
```

## 3. MySQL 계정 만들기

과제 필독사항에 root 계정/개인 비밀번호 쓰지 말라고 되어 있어서, 이 프로젝트 전용 계정을 새로 만들었습니다. 비밀번호는 로컬에서 쓰던 거 말고 새로 하나 만들었습니다.

```bash
sudo mysql <<'SQL'
CREATE DATABASE IF NOT EXISTS board_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'board_app'@'localhost' IDENTIFIED BY '새비밀번호';
GRANT SELECT, INSERT, UPDATE, DELETE ON board_db.* TO 'board_app'@'localhost';
FLUSH PRIVILEGES;
SQL

sudo mysql board_db < board/schema.sql
```

## 4. 코드 서버로 옮기기

로컬에 있던 프로젝트 폴더를 통째로 서버로 복사했습니다 (rsync 사용, `.env`는 로컬 거 그대로 옮기면 안 되니까 빼고).

```bash
rsync -az --exclude 'board/.env' "웹프로젝트폴더/" root@서버IP:/opt/board/
```

옮긴 다음 서버에서 가상환경 만들고 패키지 설치.

```bash
cd /opt/board/board
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

`.env`는 서버에서 새로 만들었습니다 (DB 비밀번호, SECRET_KEY 둘 다 새로 생성).

```bash
cat > .env <<'EOF'
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=board_app
DB_PASSWORD=3번에서만든비밀번호
DB_NAME=board_db
FLASK_SECRET_KEY=아무거나랜덤한문자열
EOF
```

## 5. 서버 꺼져도 앱이 계속 켜져 있게 하기 (systemd)

`python3 app.py`로 그냥 실행하면 터미널 닫으면 꺼지고, 서버 재부팅하면 다시 안 켜져서, systemd라는 걸로 등록해두면 자동으로 계속 켜져 있는다고 해서 이렇게 했습니다.

`/etc/systemd/system/board.service` 파일을 만듭니다.

```ini
[Unit]
Description=Board Flask app (gunicorn)
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=/opt/board/board
Environment="PATH=/opt/board/board/venv/bin"
ExecStart=/opt/board/board/venv/bin/gunicorn -w 2 -b 127.0.0.1:5050 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now board
```

(gunicorn은 Flask 내장 개발 서버 대신 쓰는 건데, 개발 서버는 "실제 서비스에 쓰지 마세요"라는 경고가 떠서 이걸로 바꿨습니다.)

## 6. nginx 연결하기

nginx가 80번 포트(웹 기본 포트)로 들어오는 요청을 받아서 우리 앱(5050번 포트에서 돌아가는 gunicorn)으로 넘겨주는 역할을 합니다. `app.py`가 게시판이랑 포트폴리오 페이지를 둘 다 서빙하게 만들어놔서, nginx 설정은 그냥 다 5050번으로 넘기기만 하면 됐습니다.

`/etc/nginx/sites-available/board` 파일을 만듭니다.

```nginx
server {
    listen 80;
    server_name 도메인_또는_IP;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/board /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

처음에 이걸 했더니 nginx가 안 켜져서 에러 로그를 봤는데, `[::]:80 실패` 이런 에러가 떴습니다. 검색해보니 이 서버가 IPv6을 아예 안 쓰는 설정이라 그런 거였고, 기본 사이트 설정(`sites-enabled/default`)을 지우고 IPv6 관련 줄이 없는 설정만 쓰니까 해결됐습니다.

## 7. 방화벽 열기

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

네이버클라우드 콘솔에서도 ACG라는 곳에서 22/80/443을 따로 열어줘야 접속이 됩니다 (서버 안에서 ufw로 열어도, 콘솔 쪽 ACG가 막혀있으면 소용없음 — 이거 몰라서 한참 헤맸습니다).

## 8. https 붙이기

그냥 IP 주소로는 정식 인증서를 못 받는다고 해서, duckdns.org에서 무료 도메인을 하나 만들고 (예: `tae-hyun.duckdns.org`), 서버 IP로 연결해뒀습니다.

그다음 certbot이라는 걸로 인증서를 받았습니다.

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tae-hyun.duckdns.org --agree-tos -m 이메일주소 --redirect
```

이거 한 번 돌리니까 nginx 설정도 알아서 https용으로 고쳐주고, http로 들어오면 https로 자동으로 넘겨주는 것까지 다 해줬습니다. 인증서는 90일마다 만료된다는데, 자동으로 갱신해주는 것도 같이 설치돼서 따로 신경 안 써도 된다고 합니다.

## 9. SSH 비밀번호 대신 키로만 접속하게 바꾸기

SSH(22번 포트)를 전체 공개로 열어놔서, 초기 비밀번호만으로는 좀 불안하다고 해서 키 방식으로 바꿨습니다.

```bash
# 로컬에서 키 만들기
ssh-keygen -t ed25519 -f ~/.ssh/study_web_key

# 서버에 공개키 등록 (일단 비밀번호로 접속해서)
ssh root@서버IP "mkdir -p ~/.ssh && echo '공개키내용' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# 키로 잘 접속되는 거 확인한 다음에만 비밀번호 로그인 막기
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

이거 했는데도 계속 비밀번호로 접속이 됐는데, 알고 보니 `/etc/ssh/sshd_config.d/50-cloud-init.conf`라는 파일에 똑같은 설정이 따로 있어서 그게 덮어쓰고 있었습니다. 그 파일도 같이 `no`로 바꿔주니까 진짜로 막혔습니다.

root 비밀번호도 새 걸로 바꿔뒀습니다 (네이버클라우드 콘솔의 "서버 접속 콘솔" 기능 쓸 때 필요해서 완전히 없애진 않았습니다).

## 확인해본 것들

- 아까 만든 도메인으로 `https://tae-hyun.duckdns.org/`, `/board/posts` 둘 다 접속되는지 확인
- `http://`로 접속해도 자동으로 `https://`로 넘어가는지 확인
- `.env` 파일이 외부에서 안 열리는지 확인 (`/board/.env` 쳐봤을 때 404 떠야 함)
