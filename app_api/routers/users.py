from fastapi import APIRouter, HTTPException, Depends, status
from bson import ObjectId
from app_api.database import usuarios_collection
from app_api.schemas import UsuarioUpdate, UsuarioResponse
from .auth import obter_usuario_atual, obter_admin_atual, gerar_hash_senha, TokenData

router = APIRouter(prefix="/users", tags=["Usuários"])

@router.put("/{usuario_id}", response_model=UsuarioResponse)
async def atualizar_perfil(
    usuario_id: str, 
    dados: UsuarioUpdate, 
    token_data: TokenData = Depends(obter_usuario_atual)
):
    # SEGURANÇA: Só o próprio usuário ou um Admin pode editar
    if token_data.usuario_id != usuario_id and token_data.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado para esta alteração")

    # Filtra apenas campos preenchidos no front
    update_data = {k: v for k, v in dados.model_dump().items() if v is not None}
    
    if "senha" in update_data:
        update_data["senha"] = gerar_hash_senha(update_data["senha"])

    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado fornecido para atualização")

    result = await usuarios_collection.update_one(
        {"_id": ObjectId(usuario_id)}, 
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Busca o usuário atualizado para retornar ao front
    user_doc = await usuarios_collection.find_one({"_id": ObjectId(usuario_id)})
    user_doc["id"] = str(user_doc["_id"])
    return user_doc

@router.delete("/{usuario_id}")
async def deletar_perfil(
    usuario_id: str, 
    token_data: TokenData = Depends(obter_usuario_atual)
):
    # SEGURANÇA: Só o próprio usuário ou um Admin pode deletar
    if token_data.usuario_id != usuario_id and token_data.role != "admin":
        raise HTTPException(status_code=403, detail="Sem permissão para excluir esta conta")

    result = await usuarios_collection.delete_one({"_id": ObjectId(usuario_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return {"mensagem": "Conta removida com sucesso"}

@router.get("/me", response_model=UsuarioResponse)
async def ler_meu_perfil(token_data: TokenData = Depends(obter_usuario_atual)):
    user_doc = await usuarios_collection.find_one({"_id": ObjectId(token_data.usuario_id)})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user_doc["id"] = str(user_doc["_id"])
    return user_doc