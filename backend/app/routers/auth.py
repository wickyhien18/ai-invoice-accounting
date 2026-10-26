"""A2: dang nhap, dang ky JWT. Day la endpoint THAT (khong mock)."""
import hmac
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.security import create_access_token, get_current_user, hash_password, verify_password, work_roles

router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginIn(BaseModel):
    email: str
    password: str


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=100)
    password: str = Field(min_length=8, max_length=72)
    role_name: str = "KTV"          # KTV (mac dinh) hoac KTT
    invite_code: str = ""           # chi can khi dang ky KTT


def user_out(u: User) -> dict:
    return {"user_id": u.user_id, "full_name": u.full_name, "email": u.email, "role_name": u.role_name,
            "can_work": u.role_name in work_roles()}   # duoc tai/sua hoa don (giao dien dung de an/hien nut)


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Sai email hoặc mật khẩu")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user_out(user)}


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """Tu dang ky. Mac dinh la KTV. KTT can ma moi (KTT_INVITE_CODE trong .env) de nguoi la khong tu phong
    minh thanh ke toan truong (nguoi duoc quyen duyet/tu choi). Dang ky xong tu dang nhap luon."""
    email = body.email.strip().lower()
    name = " ".join(body.full_name.split())
    if len(name) < 2:
        raise HTTPException(422, "Họ tên quá ngắn")
    if not _EMAIL.match(email):
        raise HTTPException(422, "Email không hợp lệ")
    if len(body.password.encode()) > 72:  # bcrypt chi doc 72 byte dau; bao ro thay vi cat am tham
        raise HTTPException(422, "Mật khẩu tối đa 72 ký tự")
    if body.role_name not in ("KTV", "KTT"):
        raise HTTPException(422, "Vai trò phải là KTV hoặc KTT")
    if body.role_name == "KTT":
        code = settings.ktt_invite_code
        if not code:
            raise HTTPException(403, "Hệ thống không cho tự đăng ký kế toán trưởng. Hãy nhờ quản trị viên tạo tài khoản")
        if not hmac.compare_digest(body.invite_code.strip().encode(), code.encode()):
            raise HTTPException(403, "Mã mời kế toán trưởng không đúng")
    if db.scalar(select(User.user_id).where(func.lower(User.email) == email)) is not None:
        raise HTTPException(409, "Email này đã được đăng ký")

    user = User(full_name=name, email=email, password_hash=hash_password(body.password), role_name=body.role_name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # hai nguoi dang ky cung email cung luc: rang buoc UNIQUE cua DB chan
        db.rollback()
        raise HTTPException(409, "Email này đã được đăng ký")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user_out(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)
