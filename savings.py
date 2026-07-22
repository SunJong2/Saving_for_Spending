from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime          # created_at 만들 때 필요
from database import get_connection
from auth import get_current_user

router = APIRouter()


# 요청 본문(JSON)의 형식 정의
# str | None = None → 안 보내면 None (DB에 NULL로 저장됨)
class SavingCreate(BaseModel):
    category: str
    amount: int
    memo: str | None = None
    image_url: str | None = None


@router.post("/savings")
def create_saving(req: SavingCreate, user_id: int = Depends(get_current_user)):
    # 0. 입력 검증
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="금액은 0보다 커야 합니다")
    # user_id는 토큰에서 꺼내지만, goal_id는 아래에서 DB 조회로 알아냄
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 이 사용자의 "진행 중인 목표"를 찾는다
    cursor.execute(
        "SELECT id FROM goals WHERE user_id = ? AND is_completed = 0",
        (user_id,)
    )
    goal = cursor.fetchone()          # 결과를 변수에 받는다 (버리지 않기!)

    if goal is None:                  # 진행 중 목표가 없으면 기록할 대상이 없음
        conn.close()
        raise HTTPException(status_code=404, detail="기록할 목표가 없습니다")

    goal_id = goal[0]                 # SELECT id 했으니 튜플의 0번째가 목표 id

    # 2. 절약 기록 저장
    cursor.execute(
        "INSERT INTO savings (user_id, goal_id, category, amount, memo, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, goal_id, req.category, req.amount, req.memo, req.image_url,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    # 3. 그 목표의 모인 금액을 기록한 만큼 증가
    cursor.execute(
        "UPDATE goals SET current_amount = current_amount + ? WHERE id = ?",
        (req.amount, goal_id)
    )

    cursor.execute(
        "SELECT current_amount, target_amount FROM goals WHERE id = ?",
        (goal_id,)
    )

    current, target = cursor.fetchone()

    if current >= target:
        cursor.execute(
            "UPDATE goals SET is_completed = 1, completed_at = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), goal_id)
        )
        conn.commit()
        conn.close()

        progress = round(current / target * 100, 1)
        return {"message": "saving created", "goal_completed": True, "progress": progress}
    
    # 4. commit 시점에 위의 INSERT + UPDATE가 한꺼번에 확정된다 (트랜잭션)
    #    중간에 에러가 나서 여기 도달 못 하면 둘 다 저장 안 됨 → 데이터 안 어긋남
    conn.commit()
    conn.close()

    return {"message": "saving created", "goal_completed": False }

@router.get("/savings")
def get_current_savings(user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 진행 중인 목표 찾기 — 이 목표의 기록만 보여줄 것
    cursor.execute(
        "SELECT id FROM goals WHERE user_id = ? AND is_completed = 0",
        (user_id,)
    )
    goal = cursor.fetchone()

    if goal is None:
        conn.close()
        raise HTTPException(status_code=404, detail="진행 중인 목표가 없습니다")

    goal_id = goal[0]

    # 2. 이 사용자의 + 이 목표의 기록만, 최신순으로
    #    (goal_id 조건 덕분에 과거 목표의 기록은 섞이지 않음)
    cursor.execute(
        """SELECT id, category, amount, memo, image_url, created_at
           FROM savings
           WHERE user_id = ? AND goal_id = ?
           ORDER BY created_at DESC""",
        (user_id, goal_id)
    )
    rows = cursor.fetchall()
    conn.close()                      # ★ 정상 경로에서도 반드시 닫기

    # 3. 튜플 리스트 → 딕셔너리 리스트로 변환해 응답
    #    기록이 없으면 빈 리스트 → 에러 아님 (프론트가 "기록 없음" 화면 처리)
    return {"savings": [
        {"id": row[0], "category": row[1], "amount": row[2], "memo": row[3],
         "image_url": row[4], "created_at": row[5]}
        for row in rows
    ]}

@router.delete("/savings/{saving_id}")
def delete_saving(saving_id: int, user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT goal_id, amount FROM savings WHERE id = ? AND user_id = ?",
    (saving_id, user_id))
    saving = cursor.fetchone()
    if saving is None:
        conn.close()
        raise HTTPException(status_code= 404, detail= "지울 수 있는 기록이 없습니다")
    
    goal_id, amount = saving
    cursor.execute("SELECT is_completed FROM goals WHERE id = ?", (goal_id,))
    goal = cursor.fetchone()

    if goal[0] == 1:
        conn.close()
        raise HTTPException(status_code=400, detail="완료된 목표의 기록은 삭제할 수 없습니다")
    
    cursor.execute("DELETE FROM savings WHERE id = ?", (saving_id,))
    cursor.execute("UPDATE goals SET current_amount = current_amount - ? WHERE id = ?",
    (amount, goal_id))

    conn.commit()
    conn.close()

    return {"message": "saving deleted"}



