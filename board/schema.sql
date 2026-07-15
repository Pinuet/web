-- board_db 스키마
-- 게시판에서 쓰는 테이블은 posts 하나뿐입니다.
-- ORM 없이, 이 파일 내용을 그대로 mysql에 실행해서 테이블을 만듭니다.

CREATE DATABASE IF NOT EXISTS board_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; -- 한글이 깨지지 않게 utf8mb4로 지정했습니다.

USE board_db;

CREATE TABLE IF NOT EXISTS posts (
  id INT AUTO_INCREMENT PRIMARY KEY,          -- 글 번호, 자동으로 1씩 늘어남
  title VARCHAR(200) NOT NULL,                -- 제목
  author VARCHAR(50) NOT NULL DEFAULT '익명', -- 작성자, 안 적으면 익명으로 저장됨
  content TEXT NOT NULL,                      -- 본문. 길게 쓸 수도 있어서 TEXT로 잡음
  password_hash VARCHAR(255) NOT NULL,        -- 수정/삭제할 때 확인하는 비밀번호 (해시로 저장, 평문 저장 X)
  views INT NOT NULL DEFAULT 0,               -- 조회수. 글 볼 때마다 1씩 늘어남
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,                            -- 작성일
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP  -- 수정일, 수정하면 자동으로 갱신됨
) ENGINE=InnoDB;
