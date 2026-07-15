# 배포 가이드 (Ubuntu VPS 기준)

이 문서는 `board/` 앱을 외부에서 접근 가능한 VPS에 올리는 절차입니다.
Ubuntu 24.04 기준이며, gunicorn(WSGI 서버) + nginx(리버스 프록시) + systemd(자동 재시작) 조합을 씁니다.
아래는 실제로 네이버클라우드플랫폼(NCP) Micro 서버(vCPU 1개, 메모리 1GB)에 배포하면서
진행한 순서 그대로입니다.

## 0. VPS 준비

- 실제로는 **네이버클라우드플랫폼(NCP)** Micro 서버(Ubuntu 24.04, 10GB)로 배포했습니다. 신규가입 크레딧과 Micro 서버 1년 무료 혜택이 있어 비용 부담이 없었습니다.
- 그 외 Oracle Cloud Free Tier, AWS Lightsail 등도 대안입니다.
- VPC 환경이라면 Public Subnet 생성 + 공인 IP 할당 + ACG에서 22/80/443 포트를 열어둬야 합니다.

## 1. 스왑 설정 (메모리 1GB짜리 저사양 서버라면 필수)

메모리가 1GB뿐이면 `apt upgrade`나 MySQL 구동 중에 메모리가 부족해질 수 있어서, 스왑을 먼저 만들어둡니다.

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. 서버 기본 설정

```bash
sudo apt update && sudo apt upgrade -y
```

> **참고**: 실제로 `linux-firmware` 패키지(560MB, 클라우드 VM엔 불필요한 하드웨어 펌웨어)가
> 다운로드 중 계속 실패해서 업그레이드가 안 끝난 적이 있었습니다. 이럴 땐 아래처럼
> 이 패키지만 보류시키고 넘어가면 됩니다.
> ```bash
> sudo apt-mark hold linux-firmware
> ```

```bash
sudo apt install -y python3-pip python3-venv mysql-server nginx git
```

## 3. MySQL 준비

로컬에서 한 것과 동일하게, **root 계정을 앱에 쓰지 말고 전용 계정을 새로 만듭니다.**
(로컬 개발용 비밀번호를 재사용하지 않고, 배포할 때 새로 생성했습니다.)

```bash
sudo mysql <<'SQL'
CREATE DATABASE IF NOT EXISTS board_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'board_app'@'localhost' IDENTIFIED BY '여기에_새로운_강력한_비밀번호';
GRANT SELECT, INSERT, UPDATE, DELETE ON board_db.* TO 'board_app'@'localhost';
FLUSH PRIVILEGES;
SQL

sudo mysql board_db < board/schema.sql
```

## 4. 앱 배포

프로젝트 전체(포트폴리오 + board)를 서버로 복사합니다. rsync/scp 둘 다 가능합니다.

```bash
# 로컬에서 실행
rsync -az --exclude 'board/.env' "웹프로젝트폴더/" root@서버IP:/opt/board/
```

서버 쪽에서 `.env`를 새로 만듭니다. **로컬 개발용 값을 그대로 옮기지 말고,
DB 비밀번호와 FLASK_SECRET_KEY를 새로 생성**합니다.

```bash
cd /opt/board/board
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

cat > .env <<'EOF'
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=board_app
DB_PASSWORD=여기에_3단계에서_만든_비밀번호
DB_NAME=board_db
FLASK_SECRET_KEY=여기에_새로_생성한_랜덤_문자열
EOF
```

## 5. systemd 서비스 등록 (gunicorn으로 실행, 자동 재시작)

`/etc/systemd/system/board.service` 파일을 만듭니다.
(프로젝트를 `/opt/board`에 통째로 복사했기 때문에 실제 앱 코드는 `/opt/board/board`에 있습니다.)

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
sudo systemctl status board
```

## 6. nginx 설정

`app.py`가 포트폴리오(`/`, `/css/...`, `/js/...`, `/images/...`)와 게시판(`/board/...`)을
**Flask 하나가 전부 서빙**하도록 만들어뒀기 때문에(로컬에서 `index.html`을 더블클릭해도
Board 메뉴가 안 열리는 문제 때문에 이렇게 구성했습니다), nginx는 모든 요청을 그냥
gunicorn 하나로 그대로 넘기기만 하면 됩니다. 정적 파일용 별도 location을 나눌 필요가 없습니다.

`/etc/nginx/sites-available/board`:

```nginx
server {
    listen 80;
    server_name 도메인_또는_서버IP;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo rm -f /etc/nginx/sites-enabled/default   # 기본 사이트 비활성화
sudo ln -s /etc/nginx/sites-available/board /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

> **참고**: 서버에 IPv6이 비활성화되어 있으면 nginx 기본 설정의
> `listen [::]:80;` 줄 때문에 `Address family not supported by protocol` 에러가 나면서
> nginx가 안 켜질 수 있습니다. 이 경우 기본(default) 사이트를 비활성화하고
> 위처럼 IPv4 전용 설정만 쓰면 해결됩니다.

## 7. 방화벽

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

클라우드 콘솔의 ACG(NCP) / 보안그룹(AWS) 등에서도 22, 80, 443 포트를 별도로 열어둬야 합니다.
방화벽은 서버 안(ufw)과 클라우드 쪽(ACG/보안그룹) 두 군데 다 확인이 필요합니다.

## 8. HTTPS (Let's Encrypt + 무료 도메인)

IP 주소만으로는 정식 SSL 인증서를 받을 수 없어서, **무료 DDNS 서비스로 도메인을 하나 만들어서** 적용했습니다.

1. [duckdns.org](https://www.duckdns.org)에서 무료 서브도메인 생성 (예: `tae-hyun.duckdns.org`), "current ip"에 서버의 공인 IP 입력
2. nginx 설정의 `server_name`을 그 도메인으로 변경
3. certbot으로 인증서 발급 + nginx 자동 설정 + http→https 리다이렉트까지 한 번에 처리

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tae-hyun.duckdns.org --agree-tos -m 본인이메일 --redirect
```

인증서는 90일마다 만료되는데, certbot이 설치되면서 **자동 갱신 타이머(systemd timer)도 같이 등록**되어서
따로 신경 쓸 필요 없습니다.

## 9. SSH 보안 강화

서버 생성 시 ACG에서 22번 포트를 `0.0.0.0/0`(전체 허용)으로 열어두면, 초기 비밀번호만으로는
무차별 대입 공격에 노출될 수 있습니다. 아래 순서로 키 기반 인증으로 전환했습니다.

```bash
# 로컬에서 키 생성
ssh-keygen -t ed25519 -f ~/.ssh/서버용_키이름

# 공개키를 서버에 등록 (최초엔 비밀번호로 접속해서)
ssh root@서버IP "mkdir -p ~/.ssh && echo '공개키내용' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# 키로 접속되는지 확인한 뒤에만 비밀번호 로그인 차단
# /etc/ssh/sshd_config 와 /etc/ssh/sshd_config.d/50-cloud-init.conf (있다면) 둘 다 확인
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config.d/50-cloud-init.conf
sudo systemctl restart ssh
```

> Ubuntu 클라우드 이미지는 `/etc/ssh/sshd_config.d/50-cloud-init.conf`에 `PasswordAuthentication yes`가
> 별도로 들어있어서, `sshd_config` 본문만 고치면 무시되고 적용이 안 될 수 있습니다. 두 파일 다 확인해야 합니다.

또한 root 초기 비밀번호도 새 값으로 변경해뒀습니다 (클라우드 콘솔의 "서버 접속 콘솔" 기능용으로만 필요).

## 체크리스트 (과제 필독사항 재확인)

- [x] sqlalchemy 등 ORM 미사용, pymysql로 SQL 직접 작성 (`db.py`, `app.py`)
- [x] DB 비밀번호는 `.env`에서 로드, 코드에 하드코딩하지 않음 (`.gitignore`로 커밋 제외)
- [x] 평소 쓰는 개인 비밀번호 대신 이 프로젝트 전용 새 계정/비밀번호 사용
- [x] 게시판 CRUD (생성/조회/수정/삭제) 구현
- [x] 검색 기능 (제목/내용/전체) 구현
- [x] 외부에서 HTTPS로 접속 가능하도록 배포
