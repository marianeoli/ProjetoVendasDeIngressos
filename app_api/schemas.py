from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

# --- MODELO DE EVENTO ---
class EventoCreate(BaseModel):
    nome: str
    data: str
    local: str
    preco: float
    quantidade_total: int
    quantidade_disponivel: int
    descricao: Optional[str] = None
    status: str

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
    data_nascimento: date
    data_compra: datetime
    quantidade: int
    valor_total: float
    cartao_credito: str # Simulação
    status: str