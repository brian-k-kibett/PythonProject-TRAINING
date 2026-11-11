# app.py - 【entity-NEXA¦canonical_name=NEXA】 v28 FINAL - ALL IN ONE - Delete + Limits + High Security + Click Likes/Comments
# Features: 15 Walls, Ranking, Likes, Comments (click to see), Views, Profiles, Badges, Notifications, Search, Report, Delete, Post Limits, Admin
from flask import Flask, render_template, request, redirect, session, jsonify
import database, os, requests, json, time, datetime, secrets, re
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
load_dotenv()

app = Flask(__name__)

# ===== SECURITY =====
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB max
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=7)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True if os.environ.get("KOYEB") else False

database.init_db()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CHANGE-ME-BRIAN-12345!")
OWNER_NAME = os.environ.get("OWNER_NAME", "BRIAN")

# ===== FIX: Absolute paths - so PythonAnywhere never uses the wrong folder =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_VIDEO = {"mp4", "mov", "webm", "mkv", "avi"}
ALLOWED_PHOTO = {"png", "jpg", "jpeg", "gif", "webp"}
DATA_FILE = os.path.join(BASE_DIR, "nexa_data.json")
PROFILES_FILE = os.path.join(BASE_DIR, "profiles.json")
NOTIF_FILE = os.path.join(BASE_DIR, "notifications.json")

# ===== LIMITS =====
MAX_POSTS_PER_DAY = 10
MAX_COMMENTS_PER_DAY = 30
POST_COOLDOWN_SECONDS = 30
MAX_LOGIN_ATTEMPTS = 10
LOGIN_BLOCK_MINUTES = 2
login_attempts = {}
last_post_time = {}
user_post_count_today = {}
user_comment_count_today = {}

BAD_WORDS = ["fuck", "shit", "bitch", "porn", "sex", "dick", "pussy", "kill yourself", "suicide", "nigger", "nigga"]
def contains_bad_word(text):
    t = (text or "").lower()
    for w in BAD_WORDS:
        if w in t: return True
    return False
def get_today_key(username): return f"{username}_{datetime.date.today().isoformat()}"
def check_post_limit(username):
    now = time.time()
    if username in last_post_time and now - last_post_time[username] < POST_COOLDOWN_SECONDS:
        return False, f"⏳ Wait {int(POST_COOLDOWN_SECONDS - (now - last_post_time[username]))} seconds before posting again!"
    if user_post_count_today.get(get_today_key(username), 0) >= MAX_POSTS_PER_DAY:
        return False, f"🚫 You reached max {MAX_POSTS_PER_DAY} posts today! Come back tomorrow."
    return True, ""
def check_comment_limit(username):
    if user_comment_count_today.get(get_today_key(username), 0) >= MAX_COMMENTS_PER_DAY: return False, "🚫 Max comments today reached."
    return True, ""
def check_login_block(key):
    if key in login_attempts and login_attempts[key].get("blocked_until", 0) > time.time():
        return False, int(login_attempts[key]["blocked_until"] - time.time())
    return True, 0
def record_failed_login(key):
    if key not in login_attempts: login_attempts[key] = {"count": 0, "blocked_until": 0}
    login_attempts[key]["count"] += 1
    if login_attempts[key]["count"] >= MAX_LOGIN_ATTEMPTS:
        login_attempts[key]["blocked_until"] = time.time() + LOGIN_BLOCK_MINUTES * 60
        login_attempts[key]["count"] = 0

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
@app.errorhandler(413)
def too_large(e): return "🚫 File too big! Max 10MB only.", 413
@app.errorhandler(404)
def not_found(e): return redirect("/")

WALLS = [
    {"slug": "USA", "name": "USA", "flag": "🇺🇸", "code": "us", "color": "#3B82F6", "color2": "#EF4444", "desc": "Red, White & Blue"},
    {"slug": "Kenya", "name": "Kenya", "flag": "🇰🇪", "code": "ke", "color": "#000000", "color2": "#16A34A", "desc": "Black, Red, Green"},
    {"slug": "UK", "name": "UK", "flag": "🇬🇧", "code": "gb", "color": "#1D4ED8", "color2": "#DC2626", "desc": "Blue, White & Red"},
    {"slug": "Tanzania", "name": "Tanzania", "flag": "🇹🇿", "code": "tz", "color": "#16A34A", "color2": "#0EA5E9", "desc": "Green, Blue, Black, Yellow"},
    {"slug": "South-Africa", "name": "South Africa", "flag": "🇿🇦", "code": "za", "color": "#DC2626", "color2": "#16A34A", "desc": "Red, Blue, Green, Yellow"},
    {"slug": "Uganda", "name": "Uganda", "flag": "🇺🇬", "code": "ug", "color": "#000000", "color2": "#EAB308", "desc": "Black, Yellow, Red"},
    {"slug": "Brazil", "name": "Brazil", "flag": "🇧🇷", "code": "br", "color": "#16A34A", "color2": "#EAB308", "desc": "Green, Yellow & Blue"},
    {"slug": "Nigeria", "name": "Nigeria", "flag": "🇳🇬", "code": "ng", "color": "#16A34A", "color2": "#FFFFFF", "desc": "Green, White, Green"},
    {"slug": "Ghana", "name": "Ghana", "flag": "🇬🇭", "code": "gh", "color": "#DC2626", "color2": "#EAB308", "desc": "Red, Yellow, Green"},
    {"slug": "Canada", "name": "Canada", "flag": "🇨🇦", "code": "ca", "color": "#DC2626", "color2": "#FFFFFF", "desc": "Red & White"},
    {"slug": "Australia", "name": "Australia", "flag": "🇦🇺", "code": "au", "color": "#1D4ED8", "color2": "#DC2626", "desc": "Blue, White & Red"},
    {"slug": "Jamaica", "name": "Jamaica", "flag": "🇯🇲", "code": "jm", "color": "#16A34A", "color2": "#EAB308", "desc": "Green, Yellow, Black"},
    {"slug": "India", "name": "India", "flag": "🇮🇳", "code": "in", "color": "#FF7A00", "color2": "#16A34A", "desc": "Orange, White, Green"},
    {"slug": "New-Zealand", "name": "New Zealand", "flag": "🇳🇿", "code": "nz", "color": "#1D4ED8", "color2": "#DC2626", "desc": "Blue, White & Red"},
    {"slug": "Ireland", "name": "Ireland", "flag": "🇮🇪", "code": "ie", "color": "#16A34A", "color2": "#FF7A00", "desc": "Green, White, Orange"},
]
WALL_SLUGS = [w["slug"] for w in WALLS]
CHALLENGES = ["🍔 Post your favourite food!", "⚽ Post your favourite football team!", "🎵 Post your favourite song!", "🌍 Post your dream country to visit!", "😂 Post the funniest thing today!", "📸 Post a photo of your town!", "🎬 Post your best video!", "❤ Post something you love!"]
def get_today_challenge():
    day = datetime.date.today().timetuple().tm_yday
    return CHALLENGES[day % len(CHALLENGES)]
def get_badge(total_likes, total_posts):
    if total_likes >= 50: return "👑 【entity-NEXA¦canonical_name=NEXA】 King"
    if total_likes >= 20: return "🔥 Rising Star"
    if total_likes >= 5: return "⭐ Star"
    if total_posts >= 3: return "✍ Active Poster"
    return "🌱 Newcomer"
def post_score(m): return (m.get("likes", 0) * 10) + (len(m.get("comments", [])) * 5) + m.get("views", 0)
def default_messages():
    d = {}
    for w in WALLS: d[w["slug"]] = [{"id": 1, "user": "【entity-nexa¦canonical_name=NEXA】", "text": f"Welcome to {w['name']} wall! {w['flag']} Post anything!", "video": "", "likes": 0, "liked_by": [], "comments": [], "views": 0, "viewed_by": [], "reports": 0}]
    return d
def load_messages():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            for wall in data:
                for m in data[wall]:
                    if "likes" not in m: m["likes"] = 0
                    if "liked_by" not in m: m["liked_by"] = []
                    if "comments" not in m: m["comments"] = []
                    if "id" not in m: m["id"] = int(time.time()*1000)
                    if "views" not in m: m["views"] = 0
                    if "viewed_by" not in m: m["viewed_by"] = []
                    if "reports" not in m: m["reports"] = 0
            for w in WALL_SLUGS:
                if w not in data: data[w] = default_messages()[w]
            return data
        except: pass
    return default_messages()
def save_messages():
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(MESSAGES, f, ensure_ascii=False, indent=2)
def load_profiles():
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}
def save_profiles(data):
    with open(PROFILES_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
def load_notifs():
    if os.path.exists(NOTIF_FILE):
        try:
            with open(NOTIF_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}
def save_notifs(data):
    with open(NOTIF_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
def add_notif(to_user, from_user, type_, text, wall_slug):
    if to_user == from_user: return
    notifs = load_notifs()
    if to_user not in notifs: notifs[to_user] = []
    notifs[to_user].insert(0, {"from": from_user, "type": type_, "text": text, "wall": wall_slug, "time": int(time.time()), "seen": False})
    notifs[to_user] = notifs[to_user][:30]; save_notifs(notifs)
def unread_count(username):
    notifs = load_notifs()
    return sum(1 for n in notifs.get(username, []) if not n.get("seen"))
def is_owner(): return "user" in session and session["user"].lower() == OWNER_NAME.lower()
MESSAGES = load_messages()
SEARCH_CACHE = {}
def get_wall(slug):
    for w in WALLS:
        if w["slug"] == slug: return w
    return WALLS[0]
def get_ranked_walls():
    ranked = []
    for w in WALLS:
        msgs = MESSAGES.get(w["slug"], [])
        people = set(); total_likes = 0; total_comments = 0; total_views = 0
        for m in msgs:
            people.add(m["user"]); total_likes += m.get("likes", 0); total_views += m.get("views", 0)
            for c in m.get("comments", []): people.add(c["user"]); total_comments += 1
        real_people = [p for p in people if p != "nexa"]
        people_count = len(real_people) if real_people else 0
        score = (people_count * 100) + (len(msgs) * 10) + total_likes + total_comments + total_views
        ranked.append({**w, "people": people_count, "posts": len(msgs), "likes": total_likes, "comments": total_comments, "views": total_views, "score": score})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(ranked): r["rank"] = i + 1
    return ranked
def local_search(query):
    q = query.lower()
    if "kenya" in q: return "🇰🇪 Kenya: Capital Nairobi. Famous for Maasai Mara, Diani Beach."
    if "nigeria" in q: return "🇳🇬 Nigeria: Capital Abuja. Famous for Lagos, Nollywood."
    if "ghana" in q: return "🇬🇭 Ghana: Capital Accra. Famous for cocoa, football."
    return f"✨ NEXA: You searched '{query}'. Try Kenya, Nigeria, Canada."
def groq_search(query):
    if not GROQ_API_KEY: return local_search(query)
    for model in ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]:
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            data = {"model": model, "messages": [{"role": "system", "content": "You are NEXA assistant. Short, fun, for a kid."}, {"role": "user", "content": query}], "max_tokens": 500}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=15)
            if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
        except Exception: continue
    return local_search(query)
def find_related_posts(query):
    q = query.lower().strip()
    if not q: return []
    results = []
    for wall_slug in WALL_SLUGS:
        wall = get_wall(wall_slug)
        for m in MESSAGES.get(wall_slug, []):
            if q in (m.get("text","") + " " + m.get("user","") + " " + wall["name"]).lower():
                results.append({"id": m["id"], "user": m["user"], "text": m.get("text",""), "video": m.get("video",""), "likes": m.get("likes",0), "comments_count": len(m.get("comments",[])), "views": m.get("views",0), "comments": m.get("comments",[])[:2], "wall": wall["name"], "wall_slug": wall_slug, "flag": wall["flag"]})
    return results[:10]

# ===== LOGIN =====
@app.route("/", methods=["GET", "POST"])
def login():
    error = ""
    ip = (request.headers.get("X-Forwarded-For", "") or request.remote_addr or "unknown").split(",")[0].strip()
    if request.method == "POST":
        name = request.form["username"].strip(); password = request.form["password"]; action = request.form["action"]
        login_key = f"{ip}|{name.lower()}"
        allowed, wait = check_login_block(login_key)
        if not allowed:
            error = f"🚫 Too many wrong tries for {name}. Wait {wait} seconds, then try Sign Up if you are new."
            return render_template("login.html", error=error)
        if not re.match(r"^[A-Za-z0-9_]{3,20}$", name):
            error = "Username must be 3-20 letters/numbers, no spaces or symbols."
            return render_template("login.html", error=error)
        if len(password) < 4:
            error = "Password must be at least 4 characters."
            return render_template("login.html", error=error)
        if action == "login":
            if database.check_user(name, password):
                login_attempts.pop(login_key, None); session["user"] = name; session.permanent = True; return redirect("/walls/Kenya")
            else: record_failed_login(login_key); error = "Wrong name or password. Try Sign Up first."
        if action == "signup":
            if database.create_user(name, password): session["user"] = name; session.permanent = True; return redirect("/walls/Kenya")
            else: error = "That name is already taken."
    return render_template("login.html", error=error)

@app.route("/walls")
def walls_redirect(): return redirect("/walls/Kenya")

# ===== WALLS / CHAT PLACE =====
@app.route("/walls/<wall_slug>", methods=["GET", "POST"])
def wall_page(wall_slug):
    if "user" not in session: return redirect("/")
    if wall_slug not in WALL_SLUGS: return redirect("/walls/Kenya")
    error_msg = ""
    if request.method == "POST":
        text = request.form.get("message", "").strip()[:500]
        if contains_bad_word(text): error_msg = "🚫 Your post has a bad word. Please be kind!"
        else:
            ok, msg = check_post_limit(session["user"])
            if not ok: error_msg = msg
            else:
                media_url = ""
                if "video_file" in request.files:
                    f = request.files["video_file"]
                    if f and f.filename != "":
                        ext = f.filename.rsplit(".", 1)[-1].lower()
                        if ext in ALLOWED_VIDEO or ext in ALLOWED_PHOTO:
                            filename = secure_filename(f"{session['user']}_{int(time.time())}_{f.filename}")
                            path = os.path.join(app.config["UPLOAD_FOLDER"], filename); f.save(path); media_url = f"/static/uploads/{filename}"
                        else: error_msg = "🚫 Only photos/videos allowed!"
                if not error_msg and (text or media_url):
                    MESSAGES[wall_slug].append({"id": int(time.time()*1000), "user": session["user"], "text": text, "video": media_url, "likes": 0, "liked_by": [], "comments": [], "views": 0, "viewed_by": [], "reports": 0})
                    last_post_time[session["user"]] = time.time()
                    key = get_today_key(session["user"]); user_post_count_today[key] = user_post_count_today.get(key, 0) + 1
                    save_messages(); return redirect(f"/walls/{wall_slug}")
    viewer = session["user"]; changed = False
    for m in MESSAGES.get(wall_slug, []):
        if "viewed_by" not in m: m["viewed_by"] = []
        if "views" not in m: m["views"] = 0
        if viewer not in m["viewed_by"]: m["viewed_by"].append(viewer); m["views"] = len(m["viewed_by"]); changed = True
    if changed: save_messages()
    ranked_posts = sorted(MESSAGES[wall_slug], key=lambda m: post_score(m), reverse=True)
    for m in ranked_posts: m["score"] = post_score(m)
    wall = get_wall(wall_slug); ranked = get_ranked_walls(); current_rank = 1
    for r in ranked:
        if r["slug"] == wall_slug: current_rank = r["rank"]
    posts_left = MAX_POSTS_PER_DAY - user_post_count_today.get(get_today_key(viewer), 0)
    return render_template("walls.html", user=session["user"], walls=ranked, current_wall=wall, current_slug=wall_slug, messages=ranked_posts, current_rank=current_rank, notif_count=unread_count(session["user"]), challenge=get_today_challenge(), error_msg=error_msg, posts_left=posts_left, is_owner=is_owner())

# ===== LIKE =====
@app.route("/like/<wall_slug>/<int:msg_id>", methods=["POST"])
def like_post(wall_slug, msg_id):
    if "user" not in session: return redirect("/")
    for m in MESSAGES.get(wall_slug, []):
        if m["id"] == msg_id:
            user = session["user"]
            if user in m.get("liked_by", []): m["liked_by"].remove(user); m["likes"] -= 1
            else: m["liked_by"].append(user); m["likes"] += 1; add_notif(m["user"], user, "like", m.get("text","")[:40] or "your photo/video", wall_slug)
            save_messages(); break
    ref = request.referrer or ""
    if "/profile/" in ref: return redirect(ref)
    return redirect(f"/walls/{wall_slug}")

# ===== COMMENT =====
@app.route("/comment/<wall_slug>/<int:msg_id>", methods=["POST"])
def comment_post(wall_slug, msg_id):
    if "user" not in session: return redirect("/")
    comment_text = request.form.get("comment", "").strip()[:300]
    if contains_bad_word(comment_text): return redirect(f"/walls/{wall_slug}")
    ok, _ = check_comment_limit(session["user"])
    if not ok: return redirect(f"/walls/{wall_slug}")
    if comment_text:
        for m in MESSAGES.get(wall_slug, []):
            if m["id"] == msg_id:
                m["comments"].append({"user": session["user"], "text": comment_text}); add_notif(m["user"], session["user"], "comment", comment_text[:60], wall_slug)
                key = get_today_key(session["user"]); user_comment_count_today[key] = user_comment_count_today.get(key, 0) + 1
                save_messages(); break
    ref = request.referrer or ""
    if "/profile/" in ref: return redirect(ref)
    return redirect(f"/walls/{wall_slug}")

# ===== DELETE - INSIDE app.py - NO SEPARATE FILE NEEDED =====
@app.route("/delete/<wall_slug>/<int:msg_id>", methods=["POST"])
def delete_post(wall_slug, msg_id):
    if "user" not in session: return redirect("/")
    user = session["user"]
    fresh = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f: fresh = json.load(f)
        except: fresh = {}
    if wall_slug in fresh:
        new_list = []
        for m in fresh[wall_slug]:
            if m.get("id") == msg_id:
                if m.get("user") == user or user.lower() == OWNER_NAME.lower():
                    if m.get("video") and m["video"].startswith("/static/uploads/"):
                        try: os.remove(m["video"].lstrip("/"))
                        except: pass
                    print(f"✅ DELETED post {msg_id} by {m.get('user')} - deleted by {user}")
                    continue
                else:
                    print(f"❌ {user} NOT allowed to delete {m.get('user')} post")
            new_list.append(m)
        fresh[wall_slug] = new_list
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(fresh, f, ensure_ascii=False, indent=2)
        global MESSAGES
        MESSAGES = fresh
    ref = request.referrer or ""
    if "/profile/" in ref: return redirect(ref)
    return redirect(f"/walls/{wall_slug}")

# ===== REPORT =====
@app.route("/report/<wall_slug>/<int:msg_id>", methods=["POST"])
def report_post(wall_slug, msg_id):
    if "user" not in session: return redirect("/")
    for m in MESSAGES.get(wall_slug, []):
        if m["id"] == msg_id:
            m["reports"] = m.get("reports", 0) + 1
            add_notif(OWNER_NAME, session["user"], "comment", f"REPORTED post: {m.get('text','')[:50]} in {wall_slug}", wall_slug)
            save_messages(); break
    ref = request.referrer or ""
    if "/profile/" in ref: return redirect(ref)
    return redirect(f"/walls/{wall_slug}")

# ===== PROFILE - WITH DELETE + CLICK LIKES/COMMENTS DATA =====
@app.route("/profile/<username>", methods=["GET", "POST"])
def profile_page(username):
    if "user" not in session: return redirect("/")
    profiles = load_profiles()
    if request.method == "POST" and username == session["user"]:
        bio = request.form.get("bio", "").strip()[:120]
        if contains_bad_word(bio): return redirect(f"/profile/{username}")
        if bio: profiles[username] = bio; save_profiles(profiles)
        return redirect(f"/profile/{username}")
    bio = profiles.get(username, "Hello! I am on NEXA 🌍")
    my_posts = []; total_likes = 0; total_comments = 0; total_views = 0
    fresh_messages = load_messages()
    for wall_slug in WALL_SLUGS:
        wall = get_wall(wall_slug)
        for m in fresh_messages.get(wall_slug, []):
            if m["user"] == username:
                my_posts.append({"id": m["id"], "user": m["user"], "text": m.get("text",""), "video": m.get("video",""), "likes": m.get("likes",0), "liked_by": m.get("liked_by",[]), "comments": m.get("comments",[]), "views": m.get("views",0), "viewed_by": m.get("viewed_by",[]), "score": post_score(m), "wall": wall["name"], "wall_slug": wall_slug, "flag": wall["flag"], "reports": m.get("reports",0)})
                total_likes += m.get("likes",0); total_comments += len(m.get("comments",[])); total_views += m.get("views",0)
    my_posts.sort(key=lambda x: x["score"], reverse=True)
    badge = get_badge(total_likes, len(my_posts))
    can_delete = (username == session["user"]) or is_owner()
    return render_template("profile.html", user=session["user"], profile_user=username, bio=bio, my_posts=my_posts, total_likes=total_likes, total_comments=total_comments, total_views=total_views, notif_count=unread_count(session["user"]), badge=badge, is_owner=is_owner(), can_delete=can_delete)

# ===== NOTIFICATIONS =====
@app.route("/notifications")
def notifications_page():
    if "user" not in session: return redirect("/")
    notifs = load_notifs(); my = notifs.get(session["user"], [])
    for n in my: n["seen"] = True
    notifs[session["user"]] = my; save_notifs(notifs)
    return render_template("notifications.html", user=session["user"], notifs=my, notif_count=0)

# ===== SEARCH =====
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()[:100]
    if not q: return jsonify({"answer": "Type something...", "posts": []})
    ql = q.lower()
    if ql in SEARCH_CACHE: return jsonify({"answer": SEARCH_CACHE[ql], "posts": find_related_posts(q)})
    ans = groq_search(q); SEARCH_CACHE[ql] = ans
    return jsonify({"answer": ans, "posts": find_related_posts(q)})

# ===== ADMIN - INSIDE app.py - BRIAN ONLY WITH SECRET KEY =====
@app.route("/admin-brian")
def admin_brian():
    if "user" not in session: return redirect("/")
    if session["user"].lower() != OWNER_NAME.lower(): return "<h1>❌ Not allowed. Only BRIAN.</h1><a href='/walls/Kenya'>Back</a>"
    if request.args.get("key") != ADMIN_PASSWORD: return "<h1>❌ Wrong admin key. Add ?key=YOUR_ADMIN_PASSWORD</h1><a href='/walls/Kenya'>Back</a>"
    all_users = []
    try:
        import sqlite3
        conn = sqlite3.connect(os.path.join(BASE_DIR, "nexa_users.db"))
        cur = conn.execute("SELECT username FROM users")
        all_users = [r[0] for r in cur.fetchall()]; conn.close()
    except Exception as e: all_users = [f"Error: {e}"]
    all_posts = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            for wall_slug, msgs in data.items():
                for m in msgs:
                    likes = m.get("likes", 0); comments = m.get("comments", []); views = m.get("views", 0)
                    score = (likes * 10) + (len(comments) * 5) + views
                    all_posts.append({"wall": wall_slug, "user": m.get("user", "?"), "text": m.get("text", ""), "video": m.get("video", ""), "likes": likes, "comments_count": len(comments), "comments_list": comments, "views": views, "score": score, "reports": m.get("reports", 0), "id": m.get("id", 0)})
        except: all_posts = []
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    return render_template("admin.html", user=session["user"], all_users=all_users, all_posts=all_posts, total_posts=len(all_posts), total_likes=sum(p["likes"] for p in all_posts), total_comments=sum(p["comments_count"] for p in all_posts), total_views=sum(p["views"] for p in all_posts), admin_key=ADMIN_PASSWORD)

@app.route("/admin-brian/delete/<wall_slug>/<int:msg_id>", methods=["POST"])
def admin_delete(wall_slug, msg_id):
    if "user" not in session: return redirect("/")
    if session["user"].lower() != OWNER_NAME.lower(): return "❌ Not allowed."
    if request.args.get("key") != ADMIN_PASSWORD: return "❌ Wrong key."
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        if wall_slug in data:
            data[wall_slug] = [m for m in data[wall_slug] if m.get("id") != msg_id]
            with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
            global MESSAGES
            MESSAGES = data
    return redirect(f"/admin-brian?key={ADMIN_PASSWORD}")

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True, debug=False)