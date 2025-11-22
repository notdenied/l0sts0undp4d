import os
import sqlite3

from datetime import timedelta

from flask import (
    Flask, render_template_string, request, redirect,
    session, send_from_directory
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
assert app.secret_key

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "app.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with db() as con:
    con.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        filename TEXT,
        display_order INTEGER
    )
    """)

CSS = """
:root{
  --bg:#0b0f13; --card:#0f1720; --muted:#98a2ad; --accent:#7c3aed;
  --glass: rgba(255,255,255,0.03);
}
*{box-sizing:border-box}
html,body{height:100%;margin:0;font-family:Inter,system-ui, -apple-system, 'Segoe UI', Roboto;background:linear-gradient(180deg,#040608,#071018);color:#e6eef6}
.container{max-width:1000px;margin:28px auto;padding:0 16px}
.header{display:flex;align-items:center;justify-content:space-between;padding:18px 0}
.brand{font-weight:700;font-size:20px}
.upload-row{display:flex;gap:12px;align-items:center}
.input-file{background:transparent;border:1px solid var(--glass);padding:8px 12px;border-radius:10px;color:inherit}
.btn{background:var(--accent);border:0;padding:10px 14px;border-radius:12px;color:white;font-weight:600;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px;margin-top:18px}
.card{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));padding:12px;border-radius:12px;border:1px solid rgba(255,255,255,0.03);display:flex;flex-direction:column;gap:10px;min-height:150px}
.title{font-weight:600;font-size:18px;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.controls{display:flex;gap:8px;justify-content:center}
.icon-btn{background:var(--glass);border:0;padding:8px;border-radius:8px;cursor:pointer;color:inherit;font-weight:600}
.rename-row{display:flex;gap:8px;align-items:center;margin-top:auto}
.rename-input{flex:1;min-width:0;padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,0.03);background:transparent;color:inherit;font-size:13px;overflow:hidden;text-overflow:ellipsis}
.small{color:var(--muted);font-size:13px;text-align:center;margin-top:18px}
@media(max-width:520px){.grid{grid-template-columns:repeat(2,1fr)}}
"""

LOGIN_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login</title><style>{{ css }}</style></head><body>
<div class="container">
  <div class="header"><div class="brand">l0sts0undp4d — Вход</div></div>
  <form method="post" style="display:flex;flex-direction:column;gap:10px;max-width:360px">
    <input name="username" placeholder="Username" required style="padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,0.03);background:transparent;color:inherit">
    <input name="password" placeholder="Password" type="password" required style="padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,0.03);background:transparent;color:inherit">
    <div style="display:flex;gap:8px"><button class="btn" type="submit">Войти</button><a href="/register" style="color:var(--accent);align-self:center">Register</a></div>
  </form>
</div></body></html>
"""

REGISTER_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Register</title><style>{{ css }}</style></head><body>
<div class="container">
  <div class="header"><div class="brand">l0sts0undp4d — Регистрация</div></div>
  <form method="post" style="display:flex;flex-direction:column;gap:10px;max-width:360px">
    <input name="username" placeholder="Username" required style="padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,0.03);background:transparent;color:inherit">
    <input name="password" placeholder="Password" type="password" required style="padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,0.03);background:transparent;color:inherit">
    <div style="display:flex;gap:8px"><button class="btn" type="submit">Создать</button><a href="/login" style="color:var(--accent);align-self:center">Login</a></div>
  </form>
</div></body></html>
"""

MAIN_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>l0sts0undp4d</title><style>{{ css }}</style>
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
</head><body>
<div class="container">
  <div class="header">
    <div class="brand">l0sts0undp4d — {{ username }}</div>
    <form method="post" action="/logout" style="margin:0"><button class="btn" type="submit">Выйти</button></form>
  </div>

  <div style="display:flex;gap:12px;align-items:center" class="upload-row">
    <form action="/upload" method="post" enctype="multipart/form-data" style="display:flex;gap:8px;align-items:center">
      <input class="input-file" type="file" name="file" accept="audio/*" required>
      <button class="btn" type="submit">Загрузить</button>
    </form>
  </div>

  <div id="grid" class="grid" style="margin-top:18px">
    {% for t in tracks %}
    <div class="card" data-id="{{ t['id'] }}">
      <div class="title" title="{{ t['name'] }}">{{ t['name'] }}</div>
      <audio id="audio{{ t['id'] }}" src="{{ url_for('serve_file', fname=t['filename']) }}"></audio>

      <div class="controls">
        <button class="icon-btn" onclick="playOnce({{ t['id'] }});return false">▶</button>
        <button class="icon-btn" onclick="loop({{ t['id'] }});return false">🔁</button>
        <button class="icon-btn" onclick="stop({{ t['id'] }});return false">■</button>
      </div>

      <div class="rename-row">
        <input class="rename-input" value="{{ t['name'] }}" onchange="renameTrack({{ t['id'] }}, this.value)" />
        <button class="icon-btn" onclick="deleteTrack({{ t['id'] }});return false">Del</button>
      </div>
    </div>
    {% endfor %}
  </div>

  {% if not tracks %}
    <div class="small">Нет загруженных треков — загрузите первый файл.</div>
  {% endif %}

</div>

<script>
function renameTrack(id, val){
  fetch('/rename/' + id, {method: 'POST', headers: {'Content-Type':'application/x-www-form-urlencoded'}, body: 'name=' + encodeURIComponent(val)})
}

function deleteTrack(id){
  fetch('/delete/' + id, {method: 'POST'}).then(()=>location.reload())
}

function playOnce(id){ let a=document.getElementById('audio'+id); a.loop=false; a.currentTime=0; a.play().catch(()=>{}) }
function loop(id){ let a=document.getElementById('audio'+id); a.loop=true; a.currentTime=0; a.play().catch(()=>{}) }
function stop(id){ let a=document.getElementById('audio'+id); a.pause(); a.currentTime=0 }

// Drag & drop
new Sortable(document.getElementById('grid'), {
  animation: 150,
  onEnd: function(){
    const ids = [...document.querySelectorAll('.card')].map(e => Number(e.dataset.id));
    fetch('/reorder', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({order: ids})})
  }
});
</script>

</body></html>
"""


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return "Missing", 400
        with db() as con:
            try:
                con.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                            (username, generate_password_hash(password)))
            except sqlite3.IntegrityError:
                return "User exists", 400
        return redirect("/login")
    return render_template_string(REGISTER_HTML, css=CSS)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        with db() as con:
            r = con.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not r or not check_password_hash(r["password"], password):
            return "Invalid", 403
        session["user_id"] = r["id"]
        session["username"] = username
        session.permanent = True
        return redirect("/")
    return render_template_string(LOGIN_HTML, css=CSS)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    with db() as con:
        rows = con.execute("SELECT * FROM tracks WHERE user_id = ? ORDER BY display_order ASC", (uid,)).fetchall()
    tracks = [dict(r) for r in rows]
    return render_template_string(MAIN_HTML, css=CSS, tracks=tracks, username=session.get("username", "user"))


@app.route("/upload", methods=["POST"])
def upload():
    if "user_id" not in session:
        return "Not auth", 403
    file = request.files.get("file")
    if not file:
        return "No file", 400
    filename = secure_filename(file.filename or "")
    if not filename:
        return "Bad name", 400
    path = os.path.join(UPLOAD_DIR, filename)

    base, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(path):
        filename = f"{base}_{i}{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        i += 1
    file.save(path)
    uid = session["user_id"]
    with db() as con:
        max_order = con.execute("SELECT COALESCE(MAX(display_order), -1) FROM tracks WHERE user_id = ?", (uid,)).fetchone()[0]
        con.execute("INSERT INTO tracks (user_id, name, filename, display_order) VALUES (?, ?, ?, ?)",
                    (uid, filename, filename, max_order + 1))
    return redirect("/")


@app.route("/rename/<int:tid>", methods=["POST"])
def rename(tid):
    if "user_id" not in session:
        return "Not auth", 403
    new = request.form.get("name", "").strip()
    if not new:
        return "Bad", 400
    with db() as con:
        con.execute("UPDATE tracks SET name = ? WHERE id = ? AND user_id = ?", (new, tid, session["user_id"]))
    return "OK"


@app.route("/delete/<int:tid>", methods=["POST"])
def delete(tid):
    if "user_id" not in session:
        return "Not auth", 403
    with db() as con:
        row = con.execute("SELECT filename FROM tracks WHERE id = ? AND user_id = ?", (tid, session["user_id"])).fetchone()
        if row:
            fname = row["filename"]
            # delete file if exists
            try:
                os.remove(os.path.join(UPLOAD_DIR, fname))
            except FileNotFoundError:
                pass
            con.execute("DELETE FROM tracks WHERE id = ? AND user_id = ?", (tid, session["user_id"]))
    return "OK"


@app.route("/reorder", methods=["POST"])
def reorder():
    if "user_id" not in session:
        return "Not auth", 403
    data = request.get_json() or {}
    order = data.get("order", [])
    if not isinstance(order, list):
        return "Bad", 400
    with db() as con:
        for idx, tid in enumerate(order):
            con.execute("UPDATE tracks SET display_order = ? WHERE id = ? AND user_id = ?",
                        (idx, int(tid), session["user_id"]))
    return "OK"


@app.route("/uploads/<path:fname>")
def serve_file(fname):
    return send_from_directory(UPLOAD_DIR, fname)


app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7331)
