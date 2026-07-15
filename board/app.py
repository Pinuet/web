"""
app.py
게시판 기능을 담당하는 Flask 앱입니다.

이 파일에서 하는 일은 크게 6가지입니다.
1) 게시글 목록 보여주기 + 검색(제목/내용/전체)
2) 글쓰기
3) 글 하나 자세히 보기 (들어올 때마다 조회수 올리기)
4) 글 수정하기
5) 글 삭제하기
6) 포트폴리오 메인 페이지(index.html)도 같이 열어주기

DB 관련해서는 과제 조건 때문에 이렇게 만들었습니다.
- sqlalchemy 같은 ORM은 쓰면 안 되니까, pymysql로 SQL 문장을 직접 써서 실행합니다.
- DB 비밀번호를 코드에 그대로 적으면 안 돼서, .env 파일에 따로 빼두고
  db.py에서 불러오게 했습니다 (자세한 내용은 db.py 참고).
"""
import os

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_connection

app = Flask(__name__, static_url_path="/board/static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-fallback-key")


# 게시판 주소는 전부 /board로 시작하게 만들었습니다.
# index.html 맨 위 메뉴에서 Board를 누르면 이 주소(/board)를 거쳐서
# /board/posts(목록)로 넘어갑니다.
@app.route("/board")
def board_home():
    return redirect(url_for("list_posts"))


# 게시글 목록 + 검색
# scope 값(all/title/content)에 따라 실행하는 쿼리를 다르게 나눴습니다.
# 검색어를 SQL 문장에 그냥 이어붙이면 SQL 인젝션 문제가 생길 수 있다고
# 배워서, 검색어는 항상 %s 자리표시자로 바인딩해서 넣었습니다.
@app.route("/board/posts")
def list_posts():
    query = request.args.get("q", "").strip()
    scope = request.args.get("scope", "all")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if not query:
                cur.execute("SELECT id, title, author, views, created_at FROM posts ORDER BY id DESC")
            elif scope == "title":
                cur.execute(
                    "SELECT id, title, author, views, created_at FROM posts WHERE title LIKE %s ORDER BY id DESC",
                    (f"%{query}%",),
                )
            elif scope == "content":
                cur.execute(
                    "SELECT id, title, author, views, created_at FROM posts WHERE content LIKE %s ORDER BY id DESC",
                    (f"%{query}%",),
                )
            else:
                # scope가 all이거나 이상한 값이 들어오면 제목/내용 둘 다 검색합니다.
                cur.execute(
                    "SELECT id, title, author, views, created_at FROM posts "
                    "WHERE title LIKE %s OR content LIKE %s ORDER BY id DESC",
                    (f"%{query}%", f"%{query}%"),
                )
            posts = cur.fetchall()
    finally:
        # 커넥션을 열었으면 끝나고 꼭 닫아줘야 해서 finally에 넣었습니다.
        conn.close()

    return render_template("list.html", posts=posts, query=query, scope=scope)


# 글쓰기 화면(GET)이랑 실제로 글 저장하는 처리(POST)를 한 함수에서 같이 합니다.
@app.route("/board/posts/new", methods=["GET", "POST"])
def new_post():
    if request.method == "GET":
        return render_template("write.html", post=None)

    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip() or "익명"
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "")

    # 제목, 내용, 비밀번호 중 하나라도 비어있으면 저장하지 않고 다시 보여줍니다.
    # 비밀번호는 나중에 이 글을 수정/삭제할 때 본인 확인용으로 씁니다.
    if not title or not content or not password:
        return render_template(
            "write.html",
            post={"title": title, "author": author, "content": content},
            error="제목, 내용, 비밀번호를 모두 입력해주세요.",
        )

    # 비밀번호를 그대로 저장하면 DB가 털렸을 때 바로 보이니까, 해시로 바꿔서 저장합니다.
    # method 안 적고 그냥 generate_password_hash(password)만 쓰니까 실행할 때 에러가 나서,
    # 검색해보니 method="pbkdf2:sha256"을 붙이면 된다고 해서 이렇게 했습니다.
    password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO posts (title, author, content, password_hash) VALUES (%s, %s, %s, %s)",
                (title, author, content, password_hash),
            )
            new_id = cur.lastrowid  # 방금 저장한 글의 id. 상세페이지로 넘어갈 때 씁니다.
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("view_post", post_id=new_id))


# 글 하나 자세히 보기. 들어올 때마다 조회수를 1씩 올려줍니다.
@app.route("/board/posts/<int:post_id>")
def view_post(post_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE posts SET views = views + 1 WHERE id = %s", (post_id,))
            conn.commit()

            cur.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
            post = cur.fetchone()
    finally:
        conn.close()

    if post is None:
        abort(404)

    return render_template("view.html", post=post)


# 글 수정. GET이면 기존 글 내용을 폼에 채워서 보여주고, POST면 실제로 수정합니다.
@app.route("/board/posts/<int:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
            post = cur.fetchone()

        if post is None:
            abort(404)

        if request.method == "GET":
            # 수정 버튼을 누르면 view.html에서 비밀번호를 먼저 물어보고,
            # 그 비밀번호를 ?pw=로 붙여서 여기로 넘어옵니다. 여기서 한 번 더 확인해서
            # 틀렸으면 수정 화면 자체를 보여주지 않습니다.
            pw = request.args.get("pw", "")
            if not check_password_hash(post["password_hash"], pw):
                flash("비밀번호가 일치하지 않습니다.")
                return redirect(url_for("view_post", post_id=post_id))
            return render_template("write.html", post=post, editing=True, password=pw)

        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip() or "익명"
        content = request.form.get("content", "").strip()
        password = request.form.get("password", "")

        if not title or not content or not password:
            return render_template(
                "write.html",
                post={"id": post_id, "title": title, "author": author, "content": content},
                editing=True,
                error="제목, 내용, 비밀번호를 모두 입력해주세요.",
            )

        # 글 쓸 때 저장해둔 해시랑 지금 입력한 비밀번호가 맞는지 확인합니다.
        if not check_password_hash(post["password_hash"], password):
            return render_template(
                "write.html",
                post={"id": post_id, "title": title, "author": author, "content": content},
                editing=True,
                error="비밀번호가 일치하지 않습니다.",
            )

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE posts SET title = %s, author = %s, content = %s WHERE id = %s",
                (title, author, content, post_id),
            )
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("view_post", post_id=post_id))


# 글 삭제. 삭제 버튼을 누르면 view.html에서 confirm 창을 한 번 띄운 다음에
# 여기로 요청이 옵니다. 비밀번호가 맞아야 실제로 지워집니다.
@app.route("/board/posts/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):
    password = request.form.get("password", "")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM posts WHERE id = %s", (post_id,))
            post = cur.fetchone()

        if post is None:
            abort(404)

        if not check_password_hash(post["password_hash"], password):
            flash("비밀번호가 일치하지 않습니다.")
            return redirect(url_for("view_post", post_id=post_id))

        with conn.cursor() as cur:
            cur.execute("DELETE FROM posts WHERE id = %s", (post_id,))
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("list_posts"))


# 여기서부터는 게시판이 아니라, 포트폴리오 메인 페이지를 같이 열어주기 위한 부분입니다.
# index.html을 그냥 더블클릭해서 열면(file://) 상단의 Board 메뉴가 /board/posts라는
# 절대경로를 못 찾아서 눌러도 반응이 없었습니다. 그래서 Flask가 포트폴리오 파일까지
# 같이 서빙하게 만들어서, http://localhost:5050/ 하나로 포트폴리오 + 게시판을
# 전부 확인할 수 있게 했습니다.
PORTFOLIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


@app.route("/")
def portfolio_home():
    return send_from_directory(PORTFOLIO_DIR, "index.html")


@app.route("/css/<path:filename>")
def portfolio_css(filename):
    return send_from_directory(os.path.join(PORTFOLIO_DIR, "css"), filename)


@app.route("/js/<path:filename>")
def portfolio_js(filename):
    return send_from_directory(os.path.join(PORTFOLIO_DIR, "js"), filename)


@app.route("/images/<path:filename>")
def portfolio_images(filename):
    return send_from_directory(os.path.join(PORTFOLIO_DIR, "images"), filename)


if __name__ == "__main__":
    # host를 0.0.0.0으로 열어둬야 같은 네트워크에 있는 다른 기기나,
    # 나중에 서버에 올렸을 때 외부에서도 접속할 수 있습니다.
    app.run(host="0.0.0.0", port=5050, debug=True)
