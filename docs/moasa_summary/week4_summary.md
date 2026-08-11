# 4주차 정리 — 목표 달성 처리 / 수정·삭제 / 히스토리 / 입력 검증

## 0. 만든 것 한눈에 보기

```
POST   /savings        (개선) 달성 자동 판정 + 완료 처리 + goal_completed 응답
POST   /goals          (개선) deadline·target_amount 입력 검증
PATCH  /goals/current  목표 부분 수정 (COALESCE)
DELETE /goals/current  목표 삭제 (딸린 savings도 함께)
GET    /goals/history  달성한 목표 목록 (최신 달성순)
```

goals가 CRUD 풀세트 완성: POST(C) / GET(R) / PATCH(U) / DELETE(D)

---

## 1. 설계 판단 기록 (자소서·면접 재료)

### 달성 처리: 자동 + 축하 이벤트 하이브리드
- A안(자동 달성) vs B안(수동 버튼) 중 **"자동 처리하되 순간은 놓치지 않는다"** 선택
- 백엔드/프론트 역할 분담:
  - 백엔드: 판정 + 완료 처리 + 응답에 `goal_completed: true/false` 신호
  - 프론트: 신호를 보고 축하 모달 표시 ("다음엔 무엇을 목표로?")
- **알림을 띄우는 건 프론트의 일, 백엔드는 판단 재료(데이터)를 주는 것까지**

### 달성 여부 확인: DB 재조회 방식 선택
- UPDATE 후 SELECT로 다시 읽기 vs 미리 읽고 파이썬 계산
- 트레이드오프: **정확성(확정된 값) vs 성능(쿼리 1회 절약)**
- 금융 성격 앱이므로 안전성 우선 → 재조회 선택
- 일반 원칙: 동시성이 걱정될수록 DB에서 다시 읽는다 (은행 잔고라면 무조건 재조회)

### 수정 범위 결정 (PATCH)
- 허용: name, deadline, image_url
- 불허: current_amount(기록의 합, 사용자가 손댈 값 아님), is_completed/completed_at(시스템 관리)
- 보류: target_amount — 낮추면 "즉시 달성" 애매함 발생, 재판정 로직 필요 → 향후 과제

### 삭제 정책
- 목표 삭제 = "이 도전을 없던 걸로" → **딸린 savings도 함께 삭제** (A안)
- 근거: "목표 바꾸고 기록 유지" 니즈는 PATCH가 이미 해결 → 삭제의 의미가 명확해짐
- 기록만 남기면(B안) 보이지도 않으면서 통계를 오염시키는 고아 데이터가 됨
- 소프트 삭제(C안, is_deleted 플래그)는 실무 패턴이지만 현 규모에 과함 → 향후 고려사항

---

## 2. 새로 배운 개념

### 입력 검증 (validation)
- **문지기는 문 앞에**: 검증은 DB 연결 전, 함수 맨 앞에서. 저장 후 검증은 순서가 틀린 것
- **프론트를 믿지 않는다**: 프론트 검증(달력 선택 등)은 우회 가능(/docs에서 직접 요청) → 백엔드도 자체 검증 필수
- 검증의 두 층:
  1. **형식(문법)**: strptime 파싱 실패 → ValueError. 13월, 2월 30일 같은 달력상 불가능한 날짜도 잡아줌
  2. **의미(비즈니스 규칙)**: 형식은 완벽해도 말이 안 되는 값 — 과거 마감일, 0 이하 금액 → 직접 검사
- 효과: 500(서버가 예상 못한 에러) → 400(잘못된 요청)으로 바뀜
```python
try:
    deadline_date = datetime.strptime(req.deadline, "%Y-%m-%d")
except ValueError:
    raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")
if deadline_date <= datetime.now():
    raise HTTPException(status_code=400, detail="마감일은 오늘 이후여야 합니다")
```

### PATCH와 부분 수정 (COALESCE)
- PUT = 전체 교체, **PATCH = 부분 수정** (REST 메서드 구분)
- Pydantic에서 `str | None = None` → 안 보낸 필드는 None
- SQL COALESCE(a, b): a가 NULL이 아니면 a, NULL이면 b
```sql
UPDATE goals SET name = COALESCE(?, name), deadline = COALESCE(?, deadline) WHERE id = ?
```
- 보낸 값은 새 값으로, 안 보낸 값(None→NULL)은 기존 값 유지
- 부분 수정이면 검증도 조건부로: `if req.deadline is not None:`

### JSON에서 "없음"의 세 가지 형태
```json
{ "name": "string" }   →  "string"이라는 실제 값 (docs 예시를 그대로 내면 이게 됨!)
{ "name": null }       →  명시적 null
{ }                    →  필드 자체를 안 보냄 → 기본값 None
```
- /docs의 "string"은 자리표시 예시 — 부분 수정 테스트 시 필드를 **지우고** 보내야 함

### DELETE와 삭제 순서
- **참조하는 쪽(savings) 먼저 → 참조받는 쪽(goals) 나중**
- 반대로 하면 존재하지 않는 목표를 가리키는 고아(orphan) 데이터 발생, 외래키 제약이 엄격한 DB에서는 거부됨
- 두 DELETE를 commit 하나로 묶어 중간 실패 시 둘 다 취소 (트랜잭션)

### 2단계 조회 패턴의 적용 기준
```
아직 뭔지 모를 때  → user_id + 정책 조건(is_completed 등)으로 찾기
이미 특정했을 때   → 기본키 id로만 (id는 이미 유일하므로 조건 덧붙이지 않음)
목록을 원할 때     → 2단계 불필요. 조건으로 한 번에 fetchall
```
- 히스토리에서 저지른 실수: 목록 조회에 2단계 패턴을 잘못 적용 (`id <= 최신완료id` → 남의 목표·미완료 목표까지 딸려옴)

### 404 vs 빈 리스트 (재확인)
- 특정한 하나의 자원 요청 (GET /goals/current) → 없으면 **404**
- 목록 요청 (GET /savings, GET /goals/history) → 없으면 **빈 리스트가 정상**
- "아직 달성한 목표 없음"은 에러가 아니라 프론트가 안내 화면을 그릴 정상 상황
- 사용자 문구("기록이 없습니다")는 항상 프론트 몫 — 백엔드는 데이터, 프론트는 표현

### JSON 불리언
- `true`(불리언) ≠ `"true"`(문자열). 문자열 "false"는 JS 조건문에서 참으로 평가되는 버그 유발
- 파이썬 True → FastAPI가 JSON true로 자동 변환. 따옴표 금지

### XxxCreate / XxxUpdate 클래스 분리
- 지금 필드가 비슷해도 역할이 다름: "만들 때 받는 값" vs "수정을 허용하는 값"
- 둘은 따로 진화함 (생성엔 있지만 수정 불허인 필드 등) → 공유하면 나중에 꼬임. 분리가 표준 패턴

---

## 3. 겪은 버그·이슈 (실전 기록)

1. **달성 판정만 하고 완료 처리 누락** — goal_completed: true 응답만 하고 is_completed UPDATE를 빼먹음 → 목표가 영원히 안 끝나는 상태 (다음 기록에도 금액 계속 증가, 새 목표 생성 불가, 히스토리 안 뜸)
2. **None 체크 전에 인덱싱** — `goal_id = goal[0]`을 `if goal is None` 앞에 씀 → 404 대신 TypeError 500. **검사 먼저, 사용은 그 다음**
3. **fetchone()은 항상 튜플** — 컬럼 하나만 SELECT해도 `(3,)` 형태. 바로 바인딩하면 "type 'tuple' is not supported" → `goal[0]`으로 꺼내기
4. **잘못된 필드명** — GoalCreate 검증에 req.amount(존재하지 않음) 사용 → AttributeError 500. 필드명은 그 함수가 받는 모델 클래스 기준으로 확인
5. **컴프리헨션 변수 혼동** — `for g in rows` 해놓고 앞에서 rows[0] 인덱싱 → 전체 리스트를 인덱싱하는 버그. for 뒤에서 지은 이름을 앞에서 쓴다
6. **토큰 만료 착각** — 라우터 추가 후 401이 떠서 코드 탓인 줄 → 실은 ACCESS_TOKEN_EXPIRE_MINUTES(60분) 만료. 토큰은 코드 수정과 무관
7. **날짜 오타 사건 (2026-0813)** — 잘못된 데이터가 들어가니 조회가 500으로 연쇄 붕괴 + 고칠 수단(U/D) 부재 발견 → 이번 주 검증·수정·삭제 구현의 계기. 응급처치로 sqlite3 직접 UPDATE 경험

---

## 4. 알아둔 것들

- `"""..."""`: 여러 줄 문자열. 긴 SQL을 줄 나눠 쓸 때 관례적 사용
- SELECT는 쓸 컬럼만 명시 (`SELECT *` 지양 — 불필요한 전송 + 컬럼 추가 시 언패킹 깨짐)
- 리스트 컴프리헨션: `[가공식 for 변수 in 반복대상]` = for+append의 압축. 변수명은 자유(관례: 복수형→단수형). 코테 빈출
- 언패킹: `current, target = cursor.fetchone()`
- UPDATE로 여러 컬럼 동시 변경: `SET a = ?, b = ?`
- 수정/생성 후엔 자원의 최신 상태를 응답으로 (프론트 재호출 절약)

---

## 5. 현재 백엔드 전체 API

```
[인증]  POST /signup · POST /login · get_current_user
[목표]  POST /goals · GET /goals/current · PATCH /goals/current
        DELETE /goals/current · GET /goals/history
[기록]  POST /savings (달성 판정 포함) · GET /savings
```

8주 플랜 위치: 1~4주차 완료. MVP 백엔드가 사실상 완성 단계.
5주차 예정: 통계 API (주간/월간 집계, streak) + 프론트 기본 화면 시작

## 6. 면접 셀프 체크

- 입력 검증을 백엔드에서도 해야 하는 이유는? (프론트 검증의 한계)
- 형식 검증과 비즈니스 규칙 검증의 차이는?
- PUT과 PATCH의 차이는? COALESCE로 부분 수정을 구현하는 원리는?
- 목표 삭제 시 절약 기록을 함께 지운 이유는? 삭제 순서가 중요한 이유는?
- 소프트 삭제란 무엇이고 언제 쓰는가?
- 404를 반환할 상황과 빈 리스트를 반환할 상황의 구분 기준은?
- 달성 판정을 서버가 하는 이유는? (클라이언트 판정의 문제점)
- JSON에서 불리언을 문자열로 보내면 생기는 문제는?
