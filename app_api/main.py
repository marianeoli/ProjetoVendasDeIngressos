from fastapi import FastAPI
from app_api.routers import events, auth
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Sistema de Vendas",
    version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Isso permite que seu HTML fale com a API
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui as rotas de Eventos (prefixo /api/v1 já cobre eventos e compras)
app.include_router(events.router, prefix="/api/v1", tags=["Eventos"])

# Inclui as rotas de Autenticação
app.include_router(auth.router, prefix="/api/v1", tags=["Autenticação"])

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Serviço de Vendas operante!"}

