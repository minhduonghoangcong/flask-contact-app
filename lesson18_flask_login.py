# -*- coding: utf-8 -*-
import os
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

# ------------ Database config (Postgres preferred) ---------------
db_url = os.getenv("DATABASE_URL", "sqlite:///contacts.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
if db_url.startswith("postgresql://") and "sslmode=" not in db_url:
    db_url += ("&" if "?" in db_url else "?") + "sslmode=require"

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------------------- Models -----------------------------------
class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Contact(db.Model):
    id   = db.Column(db.Integer, primary_key=True)
    ten  = db.Column(db.String(100), nullable=False)
    so_dt= db.Column(db.String(20),  nullable=False)

with app.app_context():
    db.create_all()

# -------------------- Login manager -------------------------------
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ---------------------- Auth routes -------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        if not u or not p:
            flash("Nhập đủ username & password", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(username=u).first():
            flash("Username đã tồn tại", "danger")
            return redirect(url_for("register"))
        db.session.add(User(username=u, password=generate_password_hash(p)))
        db.session.commit()
        flash("Đăng ký thành công! Mời đăng nhập.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        user = User.query.filter_by(username=u).first()
        if not user or not check_password_hash(user.password, p):
            flash("Sai username hoặc password", "danger")
            return redirect(url_for("login"))
        login_user(user)
        flash("Đăng nhập thành công!", "success")
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất", "info")
    return redirect(url_for("login"))

# --------------------- UI (protected) -----------------------------
@app.route("/")
@login_required
def index():
    q = request.args.get("q", "", type=str)
    base = Contact.query
    if q:
        base = base.filter(Contact.ten.ilike(f"%{q}%"))
    items = base.order_by(Contact.id.desc()).all()
    return render_template("index.html", items=items, q=q, user=current_user)

@app.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        ten = request.form.get("ten","").strip()
        so  = request.form.get("so_dt","").strip()
        if not ten or not so:
            flash("Tên và SĐT không được rỗng.", "danger")
            return redirect(url_for("create"))
        db.session.add(Contact(ten=ten, so_dt=so))
        db.session.commit()
        flash("Đã thêm liên hệ.", "success")
        return redirect(url_for("index"))
    return render_template("form.html", title="Thêm liên hệ")

@app.route("/delete/<int:cid>", methods=["POST"])
@login_required
def delete(cid):
    c = db.session.get(Contact, cid)
    if not c:
        flash("Không tìm thấy liên hệ.", "danger")
        return redirect(url_for("index"))
    db.session.delete(c)
    db.session.commit()
    flash("Đã xoá liên hệ.", "warning")
    return redirect(url_for("index"))

# ---------------------- API (protected) ---------------------------
@app.route("/api/contacts", methods=["GET"])
@login_required
def api_contacts():
    data = [{"id": c.id, "ten": c.ten, "so_dt": c.so_dt} for c in Contact.query.all()]
    return jsonify(data)

@app.route("/api/contacts", methods=["POST"])
@login_required
def api_add_contact():
    body = request.get_json(silent=True) or {}
    ten = (body.get("ten") or "").strip()
    so  = (body.get("so_dt") or "").strip()
    if not ten or not so:
        return jsonify({"error": "Thiếu tên hoặc số"}), 400
    c = Contact(ten=ten, so_dt=so)
    db.session.add(c)
    db.session.commit()
    return jsonify({"message": "Đã thêm", "id": c.id}), 201

@app.route("/api/contacts/<int:cid>", methods=["DELETE"])
@login_required
def api_delete_contact(cid):
    c = db.session.get(Contact, cid)
    if not c:
        return jsonify({"error": "Không tìm thấy"}), 404
    db.session.delete(c)
    db.session.commit()
    return jsonify({"message": "Đã xoá"})

# ---------------------- Main -------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
