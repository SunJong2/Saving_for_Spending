# 2주차 정리 — 회원가입 / 로그인 (인증 시스템)

## 0. 만든 것 한눈에 보기

```
POST /signup      회원가입 (비밀번호를 bcrypt 해시로 저장)
POST /login       로그인 (검증 후 JWT 발급)
GET  /me          토큰 검증 테스트용
get_current_user  토큰 검증 함수 — 앞으로 모든 보호 API의 문지기
```

전체 인증 흐름:

```
[가입]   비밀번호 → bcrypt 해시(+솔트) → DB 저장 (원문은 어디에도 없음)
[로그인] 입력 비번을 해시해서 DB 해시와 대조 → 통과 시 JWT 발급
[이후]   모든 요청 헤더에 토큰 첨부 → 서버가 서명 검증 → user_id 확인
```

---

## 1. 비밀번호 해시 (bcrypt)

### 왜 원문 저장이 금지인가
- DB가 털리면 모든 사용자의 비밀번호가 그대로 노출됨
- 사용자들은 비밀번호를 여러 사이트에서 재사용 → 내 서비스가 털리면 다른 서비스까지 위험
- 원칙: **개발자 본인도 사용자의 비밀번호를 알 수 없어야 한다**

### 해시의 특징
1. 같은 입력 → 항상 같은 결과
2. 결과에서 입력을 역산할 수 없음 (일방향)
3. 로그인 검증 = 원문 복원이 아니라, **입력을 다시 해시해서 저장된 해시와 비교**

### 솔트(salt)가 필요한 이유
- 순수 해시만 쓰면: 같은 비밀번호 → 같은 해시
  - 털린 DB에서 "이 두 사람은 같은 비번을 쓴다"가 노출됨
  - **레인보우 테이블 공격**: 흔한 비밀번호의 해시를 수억 개 미리 계산해둔 표로 역추적 가능
- 솔트 = 사용자마다 다른 랜덤 문자열을 비밀번호에 섞고 나서 해시
  - 같은 비밀번호라도 저장된 해시가 전부 달라짐 → 미리 계산한 표가 무용지물
- bcrypt는 솔트 생성/저장을 자동 처리 (해시 문자열 안에 솔트가 포함됨)
- bcrypt는 일부러 계산이 느림 → 무차별 대입 공격을 비현실적으로 만듦

### 코드
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

pwd_context.hash("1234")               # 가입 시: 해시 생성
pwd_context.verify("1234", saved_hash) # 로그인 시: 대조 (True/False)
```

---

## 2. JWT (JSON Web Token)

### 배경: HTTP는 무상태(stateless)
- 서버는 요청 하나를 처리하고 나면 그 사람을 잊어버림
- 로그인 상태를 유지하려면 매 요청마다 "내가 누구인지" 증명이 필요
- 해결: 로그인 성공 시 **출입증(토큰)** 발급 → 이후 요청에 첨부

### JWT 구조
```
[헤더].[페이로드].[서명]
```
- **페이로드**: 담을 정보. 우리는 `{"user_id": 1, "exp": 만료시간}`
- **서명**: 헤더+페이로드를 **서버만 아는 비밀키(SECRET_KEY)**로 계산한 값

### 핵심 원리 (면접 단골)
- 페이로드를 조작하면 서명이 안 맞음 → 새 서명을 만들려면 비밀키 필요 → 서버만 가능
- 검증 = 저장된 값과 대조가 아니라 **그때그때 재계산해서 비교**
  - 같은 내용 + 같은 비밀키 → 항상 같은 서명
  - 서버가 기억할 것은 비밀키 하나뿐. 발급한 토큰은 저장하지 않음
- 이것이 무상태 문제를 상태 저장 없이 푸는 방법 (유저 100만 명이어도 DB 조회 없이 검증)

### 주의점
- 페이로드는 암호화가 아니라 **인코딩** → 누구나 열어볼 수 있음 (jwt.io에서 확인했던 것)
  - **"읽기는 가능, 위조는 불가"**
  - 따라서 토큰에 비밀번호 등 민감 정보 절대 금지
- `exp` (만료시간): 토큰 도난 시 피해 시간을 제한. 보통 30분~수 시간

### 코드
```python
from jose import jwt, JWTError

# 발급 (로그인 성공 시)
token = jwt.encode({"user_id": user_id, "exp": expire}, SECRET_KEY, algorithm="HS256")

# 검증 (보호된 API 접근 시) — 서명 검증 + 만료 확인을 한 번에
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])  # 실패 시 JWTError
```

### SECRET_KEY
- 현재는 코드에 하드코딩 → **배포 전에 반드시 환경변수로 분리** (할 일)
- 이 키가 유출되면 누구나 토큰을 위조 가능

---

## 3. FastAPI 기술 요소

### APIRouter — 파일 분리
```python
# auth.py
router = APIRouter()

@router.post("/signup")
def signup(...): ...

# main.py
from auth import router as auth_router
app.include_router(auth_router)
```
- main.py에 전부 몰아넣지 않고 기능별 파일로 분리
- 앞으로 goals.py, savings.py도 같은 패턴으로 만들 예정

### Pydantic BaseModel — 요청 본문 정의
```python
class SignupRequest(BaseModel):
    email: str
    password: str
    nickname: str

@router.post("/signup")
def signup(req: SignupRequest): ...
```
- URL 경로 변수(`/weather/{city}`)와 달리, 여러 값은 **요청 본문(body)에 JSON**으로 받음
- 클래스 = "이 엔드포인트가 받는 JSON의 모양" 선언
- 형식이 안 맞는 요청은 FastAPI가 자동 거부

### Depends — 의존성 주입 (문지기 패턴)
```python
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")

# 사용: 보호가 필요한 엔드포인트에 한 줄
@router.get("/me")
def get_me(user_id: int = Depends(get_current_user)):
    return {"user_id": user_id}
```
- 요청마다 FastAPI가 자동으로: 헤더에서 토큰 추출 → 검증 → 성공 시 user_id 주입 / 실패 시 401
- 검증 코드를 엔드포인트마다 복붙할 필요가 없어짐
- `HTTPBearer`: `Authorization: Bearer <토큰>` 표준 헤더에서 토큰을 꺼내는 도구
  - 로그인 응답의 `"token_type": "bearer"`가 이 방식을 의미

### HTTPException — 에러 응답
```python
raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다")
```

### HTTP 상태 코드 (최소한 이 4개)
| 코드 | 의미 | 이번 주 사용처 |
|------|------|----------------|
| 200 | 성공 | 가입/로그인 성공 |
| 400 | 잘못된 요청 | 이메일 중복 |
| 401 | 인증 실패 | 비번 틀림, 토큰 무효 |
| 500 | 서버 내부 에러 | bcrypt 버전 충돌 때 봤던 것 |

### /docs — 자동 API 테스트 페이지
- FastAPI가 자동 생성. POST 요청 테스트에 필수 (브라우저 주소창은 GET만 가능)
- HTTPBearer 사용 시 Authorize 버튼이 자동 생성됨

---

## 4. 보안 관례 & 디버깅 경험

### 로그인 에러 메시지를 뭉뚱그리는 이유
- "이메일 없음" / "비번 틀림"을 구분해서 알려주면 → 공격자가 가입된 이메일을 알아낼 수 있음
- 둘 다 "이메일 또는 비밀번호가 틀렸습니다"로 통일

### SQL 인젝션과 ? 바인딩
```python
# 금지: 사용자 입력을 문자열로 직접 결합
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")

# 규칙: 항상 ? 바인딩
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```

### 겪었던 문제들 (실전 디버깅 기록)
1. **bcrypt 버전 충돌** — `AttributeError: module 'bcrypt' has no attribute '__about__'`
   - 원인: passlib(업데이트 중단)과 최신 bcrypt의 궁합 문제. 내 코드 잘못이 아님
   - 해결: `pip install "bcrypt==4.0.1"` (호환 버전으로 고정)
   - 교훈: 500 에러 → uvicorn 터미널의 에러 로그 맨 아래부터 확인
2. **.gitignore 저장 누락** — 편집기에 보이는 것과 디스크 저장은 별개
   - `cat 파일명`으로 실제 저장 내용 확인 가능
   - 이미 추적된 파일은 .gitignore에 적어도 계속 따라옴 → `git rm --cached`로 추적 해제 후 커밋
3. **DB 파일은 GitHub 금지** — 사용자 데이터(이메일, 해시)가 들어가는 파일

---

## 5. 사용 라이브러리

```
passlib[bcrypt]           비밀번호 해시
bcrypt==4.0.1             (passlib 호환 버전 고정)
python-jose[cryptography] JWT 발급/검증
```

## 6. 면접에서 나올 수 있는 질문 셀프 체크

- 비밀번호를 왜 해시로 저장하는가? 해시와 암호화의 차이는?
- 솔트는 왜 필요한가? 레인보우 테이블 공격이란?
- JWT의 구조와 서명의 원리는? 서버는 왜 토큰을 저장하지 않아도 되는가?
- JWT 페이로드에 민감 정보를 넣으면 안 되는 이유는?
- HTTP가 무상태라는 것의 의미와, 그로 인해 토큰이 필요한 이유는?
- SQL 인젝션이 무엇이고 어떻게 방어하는가?
