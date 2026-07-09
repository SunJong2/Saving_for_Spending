# 3주차 정리 — 핵심 CRUD (목표 / 절약 기록)

## 0. 만든 것 한눈에 보기

```
POST /goals          목표 생성 ("한 번에 하나" 정책 검사 포함)
GET  /goals/current  진행 중 목표 조회 (진행률·D-day는 서버가 계산)
POST /savings        절약 기록 추가 (savings INSERT + goals UPDATE 동시)
GET  /savings        현재 목표의 기록 목록 (최신순)
```

이번 주부터 뼈대 없이 직접 작성 → 리뷰 방식으로 진행. 새 개념보다 기존 조합(라우터 + Pydantic + SQL + Depends)의 반복이 핵심.

---

## 1. 이번 주 새로 배운 것

### user_id 조건은 모든 쿼리의 기본
```sql
SELECT id FROM goals WHERE user_id = ? AND is_completed = 0
```
- 다중 사용자 서비스에서 검사/조회/수정 범위는 항상 **"요청한 그 사용자의 데이터"**로 좁혀야 함
- `user_id = ?` 빠뜨리면 남의 데이터를 보거나 건드리는 보안 사고 (신입 단골 실수)
- JWT에서 꺼낸 user_id(`Depends(get_current_user)`)가 여기서 실전 투입됨

### 서버가 계산해서 얹어주는 값 (파생 값)
```python
progress = round(current_amount / target_amount * 100, 1)
d_day = (datetime.strptime(deadline, "%Y-%m-%d") - datetime.now()).days
```
- **원본(금액)만 DB에 저장, 파생 값(비율)은 조회할 때마다 계산**이 원칙
- 파생 값을 저장하면 원본과 어긋날 위험이 생김. 계산 비용은 거의 없음

### strptime vs strftime
| 함수 | 방향 | 기억법 |
|------|------|--------|
| `strptime` | 문자열 → datetime (파싱) | **p**arse |
| `strftime` | datetime → 문자열 (포맷팅) | **f**ormat |
- 날짜 연산(빼기 등)을 하려면 datetime 객체여야 하므로 파싱이 필요

### UPDATE 문 (첫 사용)
```sql
UPDATE goals SET current_amount = current_amount + ? WHERE id = ?
```
- `현재값 + ?` — 지금 값에 더한 결과로 갱신
- WHERE 빠뜨리면 전체 행이 수정되므로 주의

### 두 테이블 동시 작업과 트랜잭션
```
POST /savings = savings INSERT + goals UPDATE
```
- 둘 다 성공해야 데이터가 맞음 (기록은 됐는데 금액이 안 오르면 어긋남)
- **commit 전까지는 임시 상태, commit 순간 한꺼번에 확정**
- 중간에 에러가 나서 commit에 도달하지 못하면 앞의 INSERT도 저장 안 됨 → 데이터 정합성 유지
- 이것이 트랜잭션의 기본 개념

### ORDER BY — 정렬은 SQL이 담당
```sql
ORDER BY created_at DESC   -- 내림차순 = 최신순
ORDER BY created_at ASC    -- 오름차순 (기본값, 생략 가능)
```
- 파이썬으로 정렬 코드를 짤 필요 없음
- TEXT 컬럼인데 시간순 정렬이 되는 이유: "YYYY-MM-DD HH:MM:SS" 형식은 **문자열 사전순 = 시간순** (큰 단위가 앞에 오기 때문). 날짜를 "DD-MM-YYYY"로 저장하면 안 되는 이유이기도 함

### REST 설계 — 같은 URL, 다른 메서드
```
POST /savings  → 기록 추가
GET  /savings  → 기록 목록
```
- 엔드포인트의 정체 = **HTTP 메서드 + URL 조합**. URL이 같아도 충돌 아님
- URL은 자원을, 메서드는 행동을 표현 (URL에 /create, /list 같은 동사 넣지 않기)
- `/goals/current`의 current는 동사가 아니라 "여러 goals 중 진행 중인 하나"라는 자원 지정

### 404 vs 400
- 400: 요청 자체가 잘못됨 (중복 이메일 등)
- 404: 요청은 정상인데 해당 데이터가 없음 (진행 중 목표 없음)
- "목표는 있는데 기록이 0개"는 404가 아니라 **빈 리스트 응답이 정상** — 프론트가 "기록 없음" 화면으로 처리

---

## 2. 겪은 버그들 (실전 디버깅 기록)

### ① Depends 오용 — 조용히 데이터가 꼬이는 버그
```python
# 잘못: goal_id에 user_id가 들어감
def create_saving(..., goal_id: int = Depends(get_current_user)):
```
- `Depends(get_current_user)`는 "토큰에서 user_id를 꺼내는 함수 실행"
- goal_id는 토큰이 아니라 **DB 조회(진행 중 목표 SELECT)로 알아내는 값**
- 에러 없이 잘못된 값이 저장되는 유형이라 특히 위험

### ② ? 바인딩 값 누락 (2회 반복 → 패턴으로 각인)
```python
# 잘못: ?는 있는데 값 튜플이 없음 → 실행 시 에러 (500의 원인)
cursor.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ?")
# 수정
cursor.execute("...", (req.amount, goal_id))
```
- 컬럼 개수 = ? 개수 = 값 개수, 항상 삼중 확인
- 값이 하나여도 튜플: `(user_id,)` — 쉼표 필수

### ③ NOT NULL 컬럼 누락
- INSERT에서 user_id, created_at 등 NOT NULL(DEFAULT 없음) 컬럼을 생략하면 INSERT 거부
- 반대로 DEFAULT 있는 컬럼(current_amount, is_completed)과 NULL 허용 컬럼(completed_at)은 생략 가능 — DB가 기본값을 채움

### ④ 정상 경로의 conn.close() 누락
- 에러 분기에는 close를 넣고 정상 경로에서 빼먹는 패턴
- **"연결을 열었으면 모든 경로에서 닫는다"** 를 습관으로

### 디버깅 습관
- 500 에러 → 무조건 uvicorn 터미널 로그의 맨 아래부터 확인
- "예상과 다르게 나오는 값"을 그냥 넘기지 않기 (예: progress 0.0이 0으로 표시 → JSON에는 int/float 구분이 없어서 소수부 0이면 .0 생략. 파이썬 쪽은 float 맞음)

---

## 3. 설계 판단 기록 (자소서/면접 재료)

- **"한 번에 목표 하나" 정책의 구현**: 목표 생성 전 `user_id = ? AND is_completed = 0`인 행 존재 여부 검사 → 있으면 400. 컬럼 하나(is_completed)로 정책을 코드화
- **GET /savings에 goal_id 조건 추가**: 달성 후 새 목표를 시작하면 과거 기록이 섞이면 안 됨. "지금은 목표가 하나"여도 데이터는 누적된다는 점을 반영
- **목표 조회와 기록 조회를 2단계로 분리**: 서브쿼리로 합칠 수도 있으나, "목표 없음(404)"과 "기록 없음(빈 리스트)"을 구분하기 위해 명시적 2단계 유지

---

## 4. 현재 백엔드 전체 상태

```
auth.py     POST /signup, POST /login, get_current_user
goals.py    POST /goals, GET /goals/current
savings.py  POST /savings, GET /savings
database.py 테이블 3개 (users, goals, savings)
main.py     라우터 등록, init_db
```

8주 플랜 위치: 1~3주차 완료. 4주차는 목표 달성 처리 + 달성 히스토리 (+ 여유 시 통계 맛보기)

## 5. 면접 셀프 체크

- 모든 쿼리에 user_id 조건이 왜 필요한가? 빠지면 어떤 문제가 생기는가?
- 진행률을 DB에 저장하지 않고 매번 계산하는 이유는?
- 트랜잭션이란? commit 전에 에러가 나면 어떻게 되는가?
- POST /savings 하나에서 INSERT와 UPDATE가 함께 일어나는 이유는?
- 같은 URL에 GET과 POST가 공존할 수 있는 이유는?
- "YYYY-MM-DD" 형식으로 날짜를 저장하면 문자열 정렬이 시간순이 되는 이유는?
- 400과 404의 차이는? 빈 목록은 왜 404가 아닌가?
