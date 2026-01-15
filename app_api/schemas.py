from pydantic import BaseModel
from typing import Optional

# --- MODELO DE EVENTO ---
class EventoCreate(BaseModel):
    nome: str
    data: str
    preco: float
    quantidade_total: int
    descricao: Optional[str] = None

class EventoResponse(EventoCreate):
    id: str  # O ID que vem do Mongo

# MODELO DE USUÁRIO
class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str 

class UsuarioLogin(BaseModel):
    email: str
    senha: str

class UsuarioResponse(BaseModel):
    id: str
    nome: str
    email: str

# MODELO DE COMPRA (Atualizado) 
class PedidoCreate(BaseModel):
    evento_id: str  # Agora exigimos o ID real do evento
    usuario_id: str
    quantidade: int
    cartao_credito: str # Simulação