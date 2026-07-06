from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime
from database import get_connection

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SignupRequest(BaseModel):
    email: str
    password: str
    nickname: str


@router.post("/signup")
def signup(req: SignupRequest):
    conn = get_connection()
    cursor = conn.cursor()

    # 이메일 중복 확인
    cursor.execute("SELECT id FROM users WHERE email = ?", (req.email,))
    if cursor.fetchone() is not None:
        conn.close()
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다")

    # 비밀번호 해시 후 저장
    password_hash = pwd_context.hash(req.password)
    cursor.execute(
        "INSERT INTO users (email, password_hash, nickname, created_at) VALUES (?, ?, ?, ?)",
        (req.email, password_hash, req.nickname, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

    return {"message": "signup success"}