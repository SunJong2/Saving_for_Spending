import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from database import get_db
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()   # .env 파일을 읽어 환경변수로 등록

security = HTTPBearer()
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY is None:
    raise RuntimeError("SECRET_KEY가 설정되지 않았습니다. .env 파일을 확인하세요")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class SignupRequest(BaseModel):
    email: str
    password: str
    nickname: str


@router.post("/signup")
def signup(req: SignupRequest):
    # 0. 입력 검증
    if not req.email.strip() or not req.password.strip() or not req.nickname.strip():
        raise HTTPException(status_code=400, detail="모든 항목을 입력해주세요")
    
    with get_db() as conn:
        cursor = conn.cursor()

        # 이메일 중복 확인
        cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
        if cursor.fetchone() is not None:
            raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다")

        # 비밀번호 해시 후 저장
        password_hash = pwd_context.hash(req.password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, nickname, created_at) VALUES (%s, %s, %s, %s)",
            (req.email, password_hash, req.nickname, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()

    return {"message": "signup success"}

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. 이메일로 사용자 찾기
        cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (req.email,))
        user = cursor.fetchone()

    # 블록 밖 — DB 작업이 끝났으므로 연결은 이미 닫힘
    if user is None:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다")

    user_id, password_hash = user

    # 2. 비밀번호 대조
    if not pwd_context.verify(req.password, password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다")

    # 3. JWT 발급
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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