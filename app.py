from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json, os, uuid, threading, urllib.request, sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "nexa-secret-2026-brian"
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "nexa_data.json")
USERS_FILE = os.path.join(BASE, "nexa_users.json")
DB_FILE = os.path.join(BASE, "nexa_users.db")
UPLOAD_FOLDER = os.path.join(BASE, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

WALLS = [
    {"slug":"Kenya","name":"Kenya","code":"ke","desc":"Black, Red, Green","rank":1,"people":0,"posts":0,"likes":0},
    {"slug":"USA","name":"USA","code":"us","desc":"Red, White, Blue","rank":2,"people":0,"posts":0,"likes":0},
    {"slug":"UK","name":"UK","code":"gb","desc":"Blue, Red, White","rank":3,"people":0,"posts":0,"likes":0},
    {"slug":"Nigeria","name":"Nigeria","code":"ng","desc":"Green, White, Green","rank":4,"people":0,"posts":0,"likes":0},
    {"slug":"South-Africa","name":"South Africa","code":"za","desc":"Rainbow","rank":5,"people":0,"posts":0,"likes":0},
    {"slug":"Ghana","name":"Ghana","code":"gh","desc":"Red, Gold, Green","rank":6,"people":0,"posts":0,"likes":0},
    {"slug":"Uganda","name":"Uganda","code":"ug","desc":"Black, Yellow, Red","rank":7,"people":0,"posts":0,"likes":0},
    {"slug":"Tanzania","name":"Tanzania","code":"tz","desc":"Green, Gold, Black, Blue","rank":8,"people":0,"posts":0,"likes":0},
    {"slug":"Ethiopia","name":"Ethiopia","code":"et","desc":"Green, Yellow, Red","rank":9,"people":0,"posts":0,"likes":0},
    {"slug":"Rwanda","name":"Rwanda","code":"rw","desc":"Blue, Yellow, Green","rank":10,"people":0,"posts":0,"likes":0},
    {"slug":"India","name":"India","code":"in","desc":"Saffron, White, Green","rank":11,"people":0,"posts":0,"likes":0},
    {"slug":"Brazil","name":"Brazil","code":"br","desc":"Green, Yellow, Blue","rank":12,"people":0,"posts":0,"likes":0},
    {"slug":"France","name":"France","code":"fr","desc":"Blue, White, Red","rank":13,"people":0,"posts":0,"likes":0},
    {"slug":"Germany","name":"Germany","code":"de","desc":"Black, Red, Gold","rank":14,"people":0,"posts":0,"likes":0},
    {"slug":"Canada","name":"Canada","code":"ca","desc":"Red, White","rank":15,"people":0,"posts":0,"likes":0},
]

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                d = json.load(f)
                if isinstance(d, dict):
                    return d
        except: pass
    return {w["slug"]: [] for w in WALLS}

def save_data(d):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(d, f)
    except: pass

def load_users_json():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                u = json.load(f)
                if isinstance(u, dict):
                    return u
        except: pass
    return {}

def load_users_db():
    # OLD DB - BRIAN and old users are here
    users = {}
    if os.path.exists(DB_FILE):
        try:
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()
            # try common table/column names
            try:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cur.fetchall()]
            except:
                tables = []
            for tbl in tables:
                try:
                    cur.execute(f"PRAGMA table_info({tbl})")
                    cols = [r[1] for r in cur.fetchall()]
                    if not cols:
                        continue
                    # find username + password columns
                    ucol = None
                    pcol = None
                    for c in cols:
                        lc = c.lower()
                        if lc in ("username","user","name","email") and not ucol:
                            ucol = c
                        if lc in ("password","pass","pwd","passwd") and not pcol:
                            pcol = c
                    if ucol and pcol:
                        cur.execute(f"SELECT {ucol}, {pcol} FROM {tbl}")
                        for uname, pwd in cur.fetchall():
                            if uname and pwd is not None:
                                users[str(uname)] = str(pwd)
                except:
                    continue
            con.close()
        except:
            pass
    return users

def load_users():
    # FIX: check BOTH new JSON + old DB, DB wins if same name exists in both
    users = load_users_json()
    db_users = load_users_db()
    for k, v in db_users.items():
        # keep both exact + lower lookup - do not overwrite JSON if JSON already has it
        if k not in users:
            users[k] = v
    return users

def save_users(u):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(u, f)
    except: pass

def find_user(users, name):
    # case-insensitive lookup - BRIAN == Brian == brian
    if name in users:
        return name, users[name]
    low = name.lower()
    for k, v in users.items():
        if str(k).lower() == low:
            return k, v
    return None, None

def current_user():
    return session.get("user", "Guest")

def need_login():
    return current_user() == "Guest"

def cloudflare_ping():
    try:
        urllib.request.urlopen("https://icy-shadow-4307.briankibet2029.workers.dev/helper/health", timeout=3)
    except: pass

@app.route("/")
def home():
    return redirect("/walls/Kenya")

@app.route("/health")
def health():
    threading.Thread(target=cloudflare_ping, daemon=True).start()
    return jsonify({"ok": True, "helper": "cloudflare"})

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        # FIX: accept any field names from login.html - username/name/user, password/pass
        name = (request.form.get("username") or request.form.get("name") or request.form.get("user") or "").strip()
        pw = (request.form.get("password") or request.form.get("pass") or request.form.get("pwd") or "").strip()
        # FIX: accept any action names - action, submit, button
        action_raw = (request.form.get("action") or request.form.get("submit") or request.form.get("button") or "").lower()
        # if form has 'create' or 'signup' or 'register' anywhere, treat as create
        is_create = False
        if "create" in action_raw or "sign" in action_raw or "register" in action_raw or "new" in action_raw:
            is_create = True
        # also check if any key contains create
        for k in request.form.keys():
            if "create" in k.lower() or "signup" in k.lower() or "register" in k.lower():
                is_create = True
        users = load_users()
        if not name or not pw:
            return render_template("login.html", error_msg="Enter name and password")
        if is_create:
            found_name, _ = find_user(users, name)
            if found_name:
                return render_template("login.html", error_msg="That name is already taken - try " + name + "254 or " + name + "2")
            users[name] = pw
            save_users(users)
            session["user"] = name
            return redirect("/walls/Kenya")
        else:
            found_name, stored_pw = find_user(users, name)
            if not found_name:
                return render_template("login.html", error_msg="No such name - tap Create New Account below")
            # compare as string, strip spaces - your password is 100% correct, we don't trim inside
            if str(stored_pw).strip() != pw:
                return render_template("login.html", error_msg="Wrong name or password - check capital letters, BRIAN is not brian")
            session["user"] = found_name
            return redirect("/walls/Kenya")
    return render_template("login.html", error_msg=None)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/walls/Kenya")

@app.route("/walls/<slug>", methods=["GET","POST"])
def walls(slug):
    data = load_data()
    wall = next((w for w in WALLS if w["slug"] == slug), WALLS[0])
    slug = wall["slug"]
    user = current_user()
    if request.method == "POST":
        if need_login():
            return redirect("/login")
        text = (request.form.get("message") or "").strip()[:500]
        f = request.files.get("video_file")
        video_url = ""
        if f and f.filename:
            fn = secure_filename(str(uuid.uuid4())[:8] + "_" + f.filename)
            path = os.path.join(UPLOAD_FOLDER, fn)
            f.save(path)
            video_url = "/static/uploads/" + fn
        if text or video_url:
            msg = {"id": str(uuid.uuid4())[:8], "user": user, "text": text, "video": video_url, "likes": 0, "views": 0, "comments": [], "viewed_by": [], "score": 0}
            data.setdefault(slug, []).insert(0, msg)
            save_data(data)
            threading.Thread(target=cloudflare_ping, daemon=True).start()
        return redirect(f"/walls/{slug}")
    msgs = data.get(slug, [])
    for w in WALLS:
        lst = data.get(w["slug"], [])
        w["posts"] = len(lst)
        w["likes"] = sum(m.get("likes",0) for m in lst)
        w["people"] = len(set(m.get("user","") for m in lst))
    return render_template("walls.html", walls=WALLS, current_slug=slug, current_wall=wall, messages=msgs, user=user, current_rank=1, notif_count=0, error_msg=None)

@app.route("/like/<slug>/<mid>", methods=["POST"])
def like(slug, mid):
    if need_login():
        return redirect("/login")
    data = load_data()
    for m in data.get(slug, []):
        if str(m.get("id")) == str(mid):
            m["likes"] = int(m.get("likes",0)) + 1
            break
    save_data(data)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})
    return redirect(f"/walls/{slug}")

@app.route("/comment/<slug>/<mid>", methods=["POST"])
def comment(slug, mid):
    if need_login():
        return redirect("/login")
    user = current_user()
    txt = (request.form.get("comment") or "").strip()[:300]
    if txt:
        data = load_data()
        for m in data.get(slug, []):
            if str(m.get("id")) == str(mid):
                m.setdefault("comments", []).append({"user": user, "text": txt})
                break
        save_data(data)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})
    return redirect(f"/walls/{slug}")

@app.route("/report/<slug>/<mid>", methods=["POST"])
def report(slug, mid):
    if need_login():
        return redirect("/login")
    data = load_data()
    lst = data.get(slug, [])
    for m in list(lst):
        if str(m.get("id")) == str(mid):
            m["reports"] = int(m.get("reports",0)) + 1
            if m["reports"] >= 5:
                lst.remove(m)
            break
    save_data(data)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})
    return redirect(f"/walls/{slug}")

@app.route("/profile/<username>")
def profile(username):
    data = load_data()
    all_posts = []
    for slug, lst in data.items():
        for m in lst:
            if m.get("user") == username:
                all_posts.append(m)
    return render_template("profile.html", user=current_user(), profile_user=username, posts=all_posts)

if __name__ == "__main__":
    app.run(debug=True)