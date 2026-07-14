from fastapi import FastAPI
from database import init_db
from auth import router as auth_router
from goals import router as goals_router
from savings import router as savings_router
from fastapi.staticfiles import StaticFiles

app = FastAPI()

init_db()

app.include_router(auth_router)
app.include_router(goals_router)
app.include_router(savings_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return {"message": "SavingApp server is running"}