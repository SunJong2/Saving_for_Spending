from fastapi import FastAPI
from database import init_db
from auth import router as auth_router

app = FastAPI()

init_db()

app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "SavingApp server is running"}