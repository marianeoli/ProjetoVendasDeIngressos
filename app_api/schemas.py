from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date

# --- MODELO DE EVENTO ---
class CategoriaIngresso(BaseModel):
    nome: str        # Ex: "Pista", "Camarote"
    preco: float     # Ex: 200.0
    disponivel: int

class EventoCreate(BaseModel):
    nome: str
    data: str
    local: str
    categorias: List[CategoriaIngresso]
    preco: float
    quantidade_total: int
    quantidade_disponivel: int
    descricao: Optional[str] = None
    status: Optional[str] = "ATIVO" # Valor padrão

class EventoUpdate(BaseModel):
    nome: Optional[str] = None
    data: Optional[str] = None
    local: Optional[str] = None
    preco: Optional[float] = None
    descricao: Optional[str] = None
    categorias: Optional[List[CategoriaIngresso]] = None

class EventoResponse(EventoCreate):
    id: str
    nome: str
    data: str
    local: str
    preco: float
    quantidade_disponivel: int
    descricao: Optional[str] = None
    status: Optional[str] = "ATIVO"

    # Isso aqui é para a conversão de dados
    class Config:
        from_attributes = True

# --- MODELO DE USUÁRIO (Com Roles e JWT) ---
class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    role: str = "cliente"  # Valor padrão: cliente

class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None

class UsuarioResponse(BaseModel):
    id: str
    nome: str 
    email: EmailStr
    role: str

    class Config:
        from_attributes = True

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str

# Esquema para o Token JWT que devolve no login
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
    categoria: str        # "Pista" ou "Camarote"
    tipo_ingresso: str    # "inteira", "meia", "idoso"
    # Torna os campos abaixo opcionais para o usuário não precisar enviá-los no POST
    # O Worker e a API cuidarão desses valores internamente
    data_nascimento: Optional[date] = None
    data_hora: Optional[datetime] = None
    valor_total: Optional[float] = 0.0
    status: Optional[str] = "PENDENTE"

class HistoricoVendaResponse(BaseModel):
    id: str
    pedido_id: str
    evento_id: str
    quantidade: int
    valor_unitario: float
    valor_total: float  # O novo campo do Worker
    status: str
    data_processamento: datetime

    class Config:
        from_attributes = True

