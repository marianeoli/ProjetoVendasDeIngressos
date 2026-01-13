from fastapi import FastAPI
from app_api.routers import events

app = FastAPI(
    title="Sistema de Vendas",
    version="1.0.0")

app.include_router(events.router, prefix="/api/v1", tags=["Vendas"])

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Serviço de Vendas operante!"}