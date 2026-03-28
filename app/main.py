cat << 'EOF' > app/main.py
from fastapi import FastAPI
from app.routes.verdict import router as verdict_router

app = FastAPI(title="Verdict API", version="0.1.0")

app.include_router(verdict_router, prefix="/api/verdict", tags=["Verdict"])

@app.get("/")
async def root():
    return {"message": "Verdict API running"}
EOF