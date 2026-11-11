# database_view.py - SEPARATE FILE - Only BRIAN + secret key
from flask import Blueprint, session, redirect, render_template, jsonify, request
import sqlite3, os, json
database_view = Blueprint("database_view", __name__)
OWNER_NAME = os.environ.get("OWNER_NAME", "BRIAN")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CHANGE-ME-BRIAN-12345!")
# FIX: Absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nexa_users.db")
DATA_PATH = os.path.join(BASE_DIR, "nexa_data.json")
def get_all_data():
    all_users = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("SELECT username FROM users")
        all_users = [r[0] for r in cur.fetchall()]; conn.close()
    except Exception as e: all_users = [f"Error: {e}"]
    all_posts = []
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f: data = json.load(f)
            for wall_slug, msgs in data.items():
                for m in msgs:
                    likes = m.get("likes", 0); comments = m.get("comments", []); views = m.get("views", 0)
                    score = (likes * 10) + (len(comments) * 5) + views
                    all_posts.append({"wall": wall_slug, "user": m.get("user", "?"), "text": m.get("text", ""), "video": m.get("video", ""), "likes": likes, "comments_count": len(comments), "comments_list": comments, "views": views, "score": score, "reports": m.get("reports", 0), "id": m.get("id", 0), "viewed_by": m.get("viewed_by", [])})
        except: all_posts = []
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    return all_users, all_posts
def check_admin():
    if "user" not in session: return False
    if session["user"].lower() != OWNER_NAME.lower(): return False
    if request.args.get("key") != ADMIN_PASSWORD: return False
    return True
@database_view.route("/admin-brian")
def admin_brian():
    if not check_admin(): return "<h1>❌ Not allowed. Only BRIAN with secret key.</h1><a href='/walls/Kenya'>Back</a>"
    all_users, all_posts = get_all_data()
    return render_template("admin.html", user=session["user"], all_users=all_users, all_posts=all_posts, total_posts=len(all_posts), total_likes=sum(p["likes"] for p in all_posts), total_comments=sum(p["comments_count"] for p in all_posts), total_views=sum(p["views"] for p in all_posts), admin_key=ADMIN_PASSWORD)
@database_view.route("/admin-brian/download")
def admin_download():
    if not check_admin(): return "❌ Not allowed."
    all_users, all_posts = get_all_data()
    return jsonify({"owner": OWNER_NAME, "total_users": len(all_users), "users": all_users, "total_posts": len(all_posts), "posts": all_posts})
@database_view.route("/admin-brian/delete/<wall_slug>/<int:msg_id>", methods=["POST"])
def admin_delete(wall_slug, msg_id):
    if not check_admin(): return "❌ Not allowed."
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f: data = json.load(f)
        if wall_slug in data:
            data[wall_slug] = [m for m in data[wall_slug] if m.get("id") != msg_id]
            with open(DATA_PATH, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    return redirect(f"/admin-brian?key={ADMIN_PASSWORD}")