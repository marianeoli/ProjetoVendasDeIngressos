from fastapi import APIRouter, HTTPException
from app_api.schemas import UsuarioCreate, UsuarioLogin
from app_api.database import usuarios_collection

router = APIRouter()

@router.post("/auth/register")
async def registrar_usuario(usuario: UsuarioCreate):
    existente = await usuarios_collection.find_one({"email": usuario.email})
    if existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    usuario_dict = usuario.model_dump()
    result = await usuarios_collection.insert_one(usuario_dict)
    return {"id": str(result.inserted_id), "mensagem": "Usuário criado"}

@router.post("/auth/login")
async def login(dados: UsuarioLogin):
    usuario = await usuarios_collection.find_one({"email": dados.email, "senha": dados.senha})
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    return {"usuario_id": str(usuario["_id"]), "nome": usuario["nome"]}