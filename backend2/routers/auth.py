"""Auth router — register / login / me (backend2 native)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend2.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend2.db.session import get_db
from backend.models import User

router = APIRouter()


def _ok(data=None, message: str | None = None) -> dict:
    result: dict = {"success": True}
    if data is not None:
        result["data"] = data
    if message:
        result["message"] = message
    return result


class AuthRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(req: AuthRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(400, "用户名已存在")
    user = User(username=req.username, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _ok({"id": user.id, "username": user.username}, message="注册成功")


@router.post("/login")
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = create_access_token(user.id, user.username)
    return _ok({"token": token, "user": {"id": user.id, "username": user.username}})


from backend.services.growth.stage import determine_stage


@router.get("/me/stage")
def get_career_stage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's current career-planning stage."""
    return {"stage": determine_stage(user.id, db)}
