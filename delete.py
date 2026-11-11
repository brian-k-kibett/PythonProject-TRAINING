# delete.py - SEPARATE FILE - ONLY FOR DELETE - Does NOT touch app.py logic
# This file ONLY deletes posts. If this file breaks, NEXA still works.
from flask import Blueprint, session, redirect, request
import os, json

delete_view = Blueprint("delete_view", __name__)

OWNER_NAME = os.environ.get("OWNER_NAME", "BRIAN")
# FIX: Absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "nexa_data.json")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@delete_view.route("/delete/<wall_slug>/<int:msg_id>", methods=["POST"])
def delete_post_separate(wall_slug, msg_id):
    if "user" not in session:
        return redirect("/")
    user = session["user"]
    data = load_data()
    if wall_slug not in data:
        return redirect(f"/walls/{wall_slug}")
    new_list = []
    found = False
    for m in data[wall_slug]:
        if m.get("id") == msg_id:
            found = True
            can_delete = (m.get("user") == user) or (user.lower() == OWNER_NAME.lower())
            if can_delete:
                video = m.get("video", "")
                if video and video.startswith("/static/uploads/"):
                    try:
                        os.remove(video.lstrip("/"))
                    except:
                        pass
                print(f"✅ DELETED: Post {msg_id} by {m.get('user')} deleted by {user}")
                continue
            else:
                print(f"❌ NOT ALLOWED: {user} tried to delete {m.get('user')} post {msg_id}")
                new_list.append(m)
        else:
            new_list.append(m)
    if found:
        data[wall_slug] = new_list
        save_data(data)
    ref = request.referrer or ""
    if "/profile/" in ref:
        return redirect(ref)
    return redirect(f"/walls/{wall_slug}")

@delete_view.route("/delete-admin/<wall_slug>/<int:msg_id>", methods=["POST"])
def delete_admin(wall_slug, msg_id):
    if "user" not in session:
        return redirect("/")
    if session["user"].lower() != OWNER_NAME.lower():
        return "❌ Only BRIAN can delete from admin"
    data = load_data()
    if wall_slug in data:
        data[wall_slug] = [m for m in data[wall_slug] if m.get("id") != msg_id]
        save_data(data)
    return redirect("/walls/Kenya")