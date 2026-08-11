"""
모아사 데모 계정 시드 스크립트

실행: 프로젝트 루트(.env 있는 곳)에서  python seed_demo.py
재실행 가능 — 기존 데모 계정의 데이터를 싹 지우고 새로 심는다.

주의: DATABASE_URL이 가리키는 DB(배포용 Supabase)에 직접 쓴다.
데모 계정만 건드리므로 다른 사용자 데이터에는 영향 없음.

날짜를 바꾸고 싶으면 아래 GOALS의 created_at / window / completed_at / deadline 문자열만 수정.
"""

import random
from datetime import datetime

random.seed(42)   # 날짜 스캐터를 매번 동일하게 (재현성)

# ── 데모 계정 정보 ───────────────────────────────
DEMO_EMAIL = "demo@moasa.app"
DEMO_PASSWORD = "demo1234"
DEMO_NICKNAME = "데모"

# ── 절약 기록: (카테고리, 금액, 메모) ────────────
# 완료 목표1: 런닝화 (합 140,000)
RUNNING = [
    ("배달음식",     20000, "치킨 시킬 뻔한 거 참음"),
    ("배달음식",     19000, "야식 족발 참음"),
    ("교통",          9000, "택시 대신 버스"),
    ("편의점 간식",   3500, "과자 참음"),
    ("교통",         12000, "택시 대신 걸어감"),
    ("카페",          5000, "스벅 대신 편의점 커피"),
    ("편의점 간식",   3500, "야식 군것질 참기"),
    ("카페",          4500, "아이스 아메리카노 참음"),
    ("카페",          4500, "카페라떼 참음"),
    ("카페",          4500, "아아 한 잔 더 참음"),
    ("편의점 간식",   4000, "삼각김밥+음료 참음"),
    ("교통",          8000, "심야 택시 참음"),
    ("카페",          5500, "프라푸치노 참음"),    
    ("중고거래",     24000, "필요한 거 당근으로 싸게 산 차액"),
    ("구독 서비스",  13000, "안 보는 넷플릭스 해지"),
]

# 완료 목표2: 에어팟 프로 3 (합 348,000)
AIRPODS = [
    ("배달음식",     21000, "치킨 참음"),
    ("교통",         10000, "택시 대신 지하철"),
    ("편의점 간식",   3000, "과자 참음"),    
    ("배달음식",     20000, "야식 참고 집밥"),
    ("배달음식",     21000, "치킨 또 참음"),
    ("카페",          4500, "라떼 참음"),
    ("배달음식",     16000, "마라탕 참음"),
    ("카페",          5500, "프라푸치노 참음"),
    ("편의점 간식",   4000, "컵라면 참음"),
    ("카페",          6000, "시즌 음료 참음"),
    ("편의점 간식",   3500, "삼김+음료 참음"),
    ("카페",          4500, "버블티 참음"),
    ("배달음식",     20000, "배달 피자 참음"),
    ("카페",          5000, "편의점 커피로 대체"),
    ("교통",          9000, "버스로 대체"),
    ("배달음식",     17000, "떡볶이 배달 참음"),
    ("카페",          5500, "디저트 카페 참음"),
    ("교통",         11000, "심야 택시 참음"),
    ("배달음식",     25000, "치킨 세트 참음"),
    ("교통",         10000, "택시 참고 걷기"),
    ("카페",          5000, "아아 참음"),
    ("편의점 간식",   4000, "군것질 참음"),
    ("편의점 간식",   4500, "아이스크림 참음"),
    ("배달음식",     18000, "햄버거 참음"),
    ("교통",         12000, "택시 대신 걸어감"),
    ("편의점 간식",   3000, "젤리 참음"),
    ("중고거래",     30000, "필요한 거 당근으로 싸게 산 차액"),
    ("배달음식",     22000, "족발 시킬 뻔"),
    ("교통",          8000, "광역버스로 대체"),
    ("구독 서비스",  20000, "유튜브 프리미엄+OTT 정리"),
]

# 진행 중 목표: 닌텐도 스위치 2 (합 155,000 / 720,000)
SWITCH = [
    ("배달음식",     20000, "치킨 참음"),
    ("카페",          5000, "아아 참음"),
    ("배달음식",     21000, "배달 대신 집밥"),
    ("카페",          5000, "라떼 참음"),
    ("카페",          4500, "버블티 참음"),
    ("교통",          9000, "버스로 대체"),
    ("편의점 간식",   4000, "과자 참음"),
    ("교통",         11000, "택시 참음"),
    ("편의점 간식",   4000, "군것질 참음"),
    ("카페",          5500, "프라푸치노 참음"),
    ("배달음식",     19000, "야식 참음"),
    ("편의점 간식",   3500, "삼각김밥 참음"),
    ("중고거래",     18500, "당근으로 싸게 산 차액"),
    ("구독 서비스",  13000, "안 보는 OTT 해지"),
    ("교통",         12000, "택시 대신 걸어감"),
]

# ── 목표 3개 (2026년 기준, 오늘=8/11 가정) ────────
GOALS = [
    {
        "name": "런닝화",
        "target": 140000,
        "deadline": "2026-05-31",                    # 마감
        "created_at": "2026-05-03 09:00:00",
        "window": ("2026-05-03 10:00:00", "2026-05-24 15:00:00"),  # 절약 기록이 뿌려질 기간
        "completed_at": "2026-05-24 15:30:00",       # 마감 7일 전 → "7일 빠르게 ⚡"
        "savings": RUNNING,
    },
    {
        "name": "에어팟 프로 3",
        "target": 330000,
        "deadline": "2026-07-15",
        "created_at": "2026-06-01 09:00:00",
        "window": ("2026-06-01 10:00:00", "2026-07-22 19:00:00"),
        "completed_at": "2026-07-22 20:10:00",       # 마감 7일 후 → "끝까지 해냈어요"
        "savings": AIRPODS,
    },
    {
        "name": "닌텐도 스위치 2",
        "target": 720000,
        "deadline": "2026-12-31",
        "created_at": "2026-07-25 09:00:00",
        "window": ("2026-07-26 10:00:00", "2026-08-09 21:00:00"),
        "completed_at": None,                        # 진행 중
        "savings": SWITCH,
    },
]


def spread_dates(window, n):
    """window (start, end) 사이에 n개의 날짜시각을 흩뿌려서 오름차순으로 반환."""
    start = datetime.strptime(window[0], "%Y-%m-%d %H:%M:%S")
    end = datetime.strptime(window[1], "%Y-%m-%d %H:%M:%S")
    span = (end - start).total_seconds()
    offsets = sorted(random.uniform(0, span) for _ in range(n))
    return [(start.timestamp() + o) for o in offsets]  # epoch초 리스트


def main():
    from database import get_db          # DB 연결 (여기서 import → 검증 시 DB 없이도 데이터 확인 가능)
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. 기존 데모 계정 청소 (FK 순서: savings → goals → users)
        cursor.execute("SELECT id FROM users WHERE email = %s", (DEMO_EMAIL,))
        row = cursor.fetchone()
        if row:
            uid = row[0]
            cursor.execute("DELETE FROM savings WHERE user_id = %s", (uid,))
            cursor.execute("DELETE FROM goals WHERE user_id = %s", (uid,))
            cursor.execute("DELETE FROM users WHERE id = %s", (uid,))
            print(f"기존 데모 계정(id={uid}) 데이터 삭제")

        # 2. 데모 유저 생성
        cursor.execute(
            "INSERT INTO users (email, password_hash, nickname, created_at) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (DEMO_EMAIL, pwd_context.hash(DEMO_PASSWORD), DEMO_NICKNAME, "2026-05-01 09:00:00")
        )
        user_id = cursor.fetchone()[0]
        print(f"데모 유저 생성: id={user_id}, email={DEMO_EMAIL}")

        # 3. 목표 + 절약 기록 심기
        total_savings = 0
        for g in GOALS:
            current = sum(a for _, a, _ in g["savings"])
            is_completed = g["completed_at"] is not None

            cursor.execute(
                "INSERT INTO goals "
                "(user_id, name, target_amount, current_amount, deadline, is_completed, created_at, completed_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (user_id, g["name"], g["target"], current, g["deadline"],
                 is_completed, g["created_at"], g["completed_at"])
            )
            goal_id = cursor.fetchone()[0]

            dates = spread_dates(g["window"], len(g["savings"]))
            for (category, amount, memo), epoch in zip(g["savings"], dates):
                created_at = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO savings (user_id, goal_id, category, amount, memo, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (user_id, goal_id, category, amount, memo, created_at)
                )

            total_savings += len(g["savings"])
            state = "완료" if is_completed else "진행 중"
            print(f"  목표 '{g['name']}' ({state}) — {current:,}/{g['target']:,}원, 기록 {len(g['savings'])}건")

        conn.commit()
        print(f"완료. 절약 기록 총 {total_savings}건 심음.")
        print(f"로그인: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
