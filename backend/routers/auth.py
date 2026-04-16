"""Auth router — register / login / me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.db import get_db
from backend.db_models import User

router = APIRouter()


from backend.utils import ok


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
    return ok({"id": user.id, "username": user.username}, message="注册成功")


@router.post("/login")
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = create_access_token(user.id, user.username)
    return ok({"token": token, "user": {"id": user.id, "username": user.username}})


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return ok({"id": user.id, "username": user.username})


from backend.services.career_stage import determine_stage

@router.get("/me/stage")
def get_career_stage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's current career-planning stage.

    Used by the frontend to conditionally render homepage CTA and gate
    access to the /explore flow.
    """
    return {"stage": determine_stage(user.id, db)}
