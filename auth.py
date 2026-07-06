from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from database import get_connection
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


security = HTTPBearer()
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "temporary-secret-key-change-later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


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

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 이메일로 사용자 찾기
    cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (req.email,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다")

    user_id, password_hash = user

    # 2. 비밀번호 대조
    if not pwd_context.verify(req.password, password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다")

    # 3. JWT 발급
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"user_id": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    
@router.get("/me")
def get_me(user_id: int = Depends(get_current_user)):
    return {"user_id": user_id}