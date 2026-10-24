"""Goi B (B7): danh muc tai khoan (TT133) va loai khoan kem cach viet khac (alias). Day la endpoint THAT.

Doc: moi nguoi da dang nhap. Them/sua/xoa: chi ke toan truong (KTT), vi danh muc anh huong moi dinh khoan.
"""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, CategoryAlias, InvoiceField, ItemCategory, JournalEntry, User
from app.security import get_current_user, require_role
from app.services.gl_suggest import fold

router = APIRouter(prefix="/api", tags=["B"])
CODE_RE = re.compile(r"^\d{3,10}$")
KTT = Depends(require_role("KTT"))


def _code(code: str) -> str:
    code = code.strip()
    if not CODE_RE.match(code):
        raise HTTPException(422, "Mã tài khoản gồm 3 đến 10 chữ số")
    return code


# ------------------------------------------------------------------ tai khoan
def _account_usage(db: Session, code: str) -> int:
    n = db.scalar(select(func.count()).select_from(JournalEntry).where(
        (JournalEntry.debit_account == code) | (JournalEntry.credit_account == code)))
    return n + db.scalar(select(func.count()).select_from(ItemCategory)
                         .where(ItemCategory.default_debit_account == code))


def _acc(a: Account) -> dict:
    return {"account_code": a.account_code, "account_name": a.account_name}


@router.get("/accounts")
def list_accounts(q: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.scalars(select(Account).order_by(Account.account_code))
    out = [_acc(a) for a in rows]
    if q and q.strip():
        k = fold(q)
        out = [a for a in out if k in fold(a["account_code"] + " " + a["account_name"])]
    return {"data": out, "total": len(out)}


class AccountIn(BaseModel):
    account_code: str = Field(max_length=10)
    account_name: str = Field(min_length=1, max_length=200)


class AccountName(BaseModel):
    account_name: str = Field(min_length=1, max_length=200)


@router.post("/accounts", status_code=201)
def create_account(body: AccountIn, db: Session = Depends(get_db), _: User = KTT):
    code = _code(body.account_code)
    if not body.account_name.strip():
        raise HTTPException(422, "Tên tài khoản không được để trống")
    if db.get(Account, code):
        raise HTTPException(409, f"Tài khoản {code} đã có")
    a = Account(account_code=code, account_name=body.account_name.strip())
    db.add(a)
    db.commit()
    return {"data": _acc(a)}


@router.put("/accounts/{code}")
def rename_account(code: str, body: AccountName, db: Session = Depends(get_db), _: User = KTT):
    a = db.get(Account, code)
    if a is None:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    if not body.account_name.strip():
        raise HTTPException(422, "Tên tài khoản không được để trống")
    a.account_name = body.account_name.strip()
    db.commit()
    return {"data": _acc(a)}


@router.delete("/accounts/{code}")
def delete_account(code: str, db: Session = Depends(get_db), _: User = KTT):
    a = db.get(Account, code)
    if a is None:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    if (n := _account_usage(db, code)):
        raise HTTPException(409, f"Tài khoản {code} đang được dùng ở {n} bút toán/loại khoản, không thể xóa")
    db.delete(a)
    db.commit()
    return {"data": {"deleted": code}}


# ------------------------------------------------------------------ loai khoan
def _cat(db: Session, c: ItemCategory) -> dict:
    aliases = db.scalars(select(CategoryAlias).where(CategoryAlias.category_id == c.category_id)
                         .order_by(CategoryAlias.alias_id))
    return {"category_id": c.category_id, "category_name": c.category_name,
            "default_debit_account": c.default_debit_account,
            "aliases": [{"alias_id": a.alias_id, "alias_text": a.alias_text} for a in aliases]}


def _get_cat(db: Session, category_id: int) -> ItemCategory:
    c = db.get(ItemCategory, category_id)
    if c is None:
        raise HTTPException(404, "Không tìm thấy loại khoản")
    return c


def _check_debit(db: Session, code: str | None) -> str | None:
    code = (code or "").strip() or None
    if code and db.get(Account, code) is None:
        raise HTTPException(422, f"Tài khoản Nợ mặc định {code} không có trong danh mục")
    return code


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {"data": [_cat(db, c) for c in db.scalars(select(ItemCategory).order_by(ItemCategory.category_name))]}


class CategoryIn(BaseModel):
    category_name: str = Field(min_length=1, max_length=100)
    default_debit_account: str | None = Field(None, max_length=10)


def _unique_name(db: Session, name: str, except_id: int | None = None) -> str:
    name = " ".join(name.split())
    if not name:
        raise HTTPException(422, "Tên loại khoản không được để trống")
    dup = db.scalar(select(ItemCategory.category_id).where(ItemCategory.category_name == name))
    if dup is not None and dup != except_id:
        raise HTTPException(409, f"Loại khoản “{name}” đã có")
    return name


@router.post("/categories", status_code=201)
def create_category(body: CategoryIn, db: Session = Depends(get_db), _: User = KTT):
    c = ItemCategory(category_name=_unique_name(db, body.category_name),
                     default_debit_account=_check_debit(db, body.default_debit_account))
    db.add(c)
    db.commit()
    return {"data": _cat(db, c)}


@router.put("/categories/{category_id}")
def update_category(category_id: int, body: CategoryIn, db: Session = Depends(get_db), _: User = KTT):
    c = _get_cat(db, category_id)
    c.category_name = _unique_name(db, body.category_name, category_id)
    c.default_debit_account = _check_debit(db, body.default_debit_account)
    db.commit()
    return {"data": _cat(db, c)}


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), _: User = KTT):
    c = _get_cat(db, category_id)
    if db.scalar(select(func.count()).select_from(InvoiceField).where(InvoiceField.category_id == category_id)):
        raise HTTPException(409, "Loại khoản đang gắn với các trường hóa đơn, không thể xóa")
    for a in db.scalars(select(CategoryAlias).where(CategoryAlias.category_id == category_id)):
        db.delete(a)
    db.delete(c)
    db.commit()
    return {"data": {"deleted": category_id}}


class AliasIn(BaseModel):
    alias_text: str = Field(min_length=1, max_length=150)


@router.post("/categories/{category_id}/aliases", status_code=201)
def add_alias(category_id: int, body: AliasIn, db: Session = Depends(get_db), _: User = KTT):
    _get_cat(db, category_id)
    text = " ".join(body.alias_text.split())
    key = fold(text)
    if len(key) < 2:
        raise HTTPException(422, "Cách viết khác cần ít nhất 2 ký tự chữ hoặc số")
    for other in db.scalars(select(CategoryAlias)):
        if fold(other.alias_text) == key:  # khong dau/hoa thuong: 'Van phong pham' trung 'văn phòng phẩm'
            raise HTTPException(409, "Cách viết này đã có (không phân biệt dấu và chữ hoa/thường)")
    a = CategoryAlias(alias_text=text, category_id=category_id)
    db.add(a)
    db.commit()
    return {"data": {"alias_id": a.alias_id, "alias_text": a.alias_text}}


@router.delete("/categories/{category_id}/aliases/{alias_id}")
def delete_alias(category_id: int, alias_id: int, db: Session = Depends(get_db), _: User = KTT):
    a = db.get(CategoryAlias, alias_id)
    if a is None or a.category_id != category_id:
        raise HTTPException(404, "Không tìm thấy cách viết khác")
    db.delete(a)
    db.commit()
    return {"data": {"deleted": alias_id}}
