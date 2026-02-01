import os
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from app_api.schemas import UsuarioCreate, Token, TokenData # UsuarioLogin removido (não usado aqui)
from app_api.database import usuarios_collection, db
from bson import ObjectId

# --- CONFIGURAÇÕES DE SEGURANÇA ---
SECRET_KEY = os.getenv("SECRET_KEY", "chave-temporaria-para-desenvolvimento-123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# O tokenUrl deve ser o caminho COMPLETO para o Swagger encontrar a rota
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

router = APIRouter()

# --- FUNÇÕES UTILITÁRIAS ---
def gerar_hash_senha(senha: str):
    return pwd_context.hash(senha)

def verificar_senha(senha_pura, senha_hash):
    return pwd_context.verify(senha_pura, senha_hash)

def criar_token_acesso(dados: dict):
    para_codificar = dados.copy()
    # Usando timezone.utc para compatibilidade com Python 3.12+
    expira = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    para_codificar.update({"exp": expira})
    return jwt.encode(para_codificar, SECRET_KEY, algorithm=ALGORITHM)

# --- ROTAS DE AUTENTICAÇÃO ---

@router.post("/auth/register")
async def registrar_usuario(usuario: UsuarioCreate):
    existente = await usuarios_collection.find_one({"email": usuario.email})
    if existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    usuario_dict = usuario.model_dump()
    usuario_dict["senha"] = gerar_hash_senha(usuario.senha)
    
    # Garante que todo novo usuário tenha a role 'cliente' se não for especificado
    if "role" not in usuario_dict or not usuario_dict["role"]:
        usuario_dict["role"] = "cliente"
    
    result = await usuarios_collection.insert_one(usuario_dict)
    return {"id": str(result.inserted_id), "mensagem": "Usuário criado com sucesso"}

@router.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    usuario = await usuarios_collection.find_one({"email": form_data.username})
    
    if not usuario or not verificar_senha(form_data.password, usuario["senha"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_acesso = criar_token_acesso(
        dados={"sub": str(usuario["_id"]), "role": usuario.get("role", "cliente")}
    )
    return {"access_token": token_acesso, "token_type": "bearer"}

# --- DEPENDÊNCIAS DE SEGURANÇA ---

async def obter_usuario_atual(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = payload.get("sub")
        role: str = payload.get("role")
        if usuario_id is None:
            raise credentials_exception
        return TokenData(usuario_id=usuario_id, role=role)
    except JWTError:
        raise credentials_exception

# Nova dependência para proteger o Dashboard
async def obter_admin_atual(usuario: TokenData = Depends(obter_usuario_atual)):
    if usuario.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores"
        )
    return usuario

