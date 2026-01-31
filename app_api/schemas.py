from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date

# --- MODELO DE EVENTO ---
class EventoCreate(BaseModel):
    nome: str
    data: str
    local: str
    valor_total: float
    quantidade_total: int
    quantidade_disponivel: int
    descricao: Optional[str] = None
    status: Optional[str] = "EM ESPERA"  # Valor padrão

class EventoResponse(EventoCreate):
    id: str

# --- MODELO DE USUÁRIO (Com Roles e JWT) ---
class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    role: str = "cliente"  # Valor padrão: cliente

class UsuarioResponse(BaseModel):
    id: str
    nome: str 
    email: EmailStr
    role: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str

# Esquema para o Token JWT que devolveremos no login
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    usuario_id: Optional[str] = None
    role: Optional[str] = None

# --- MODELO DE COMPRA (Otimizado) ---
class PedidoCreate(BaseModel):
    evento_id: str
    usuario_id: str
    quantidade: int
    # Tornamos os campos abaixo opcionais para o usuário não precisar enviá-los no POST
    # O Worker e a API cuidarão desses valores internamente
    data_nascimento: Optional[date] = None
    data_hora: Optional[datetime] = None
    valor_total: Optional[float] = 0.0
    status: Optional[str] = "PENDENTE"
