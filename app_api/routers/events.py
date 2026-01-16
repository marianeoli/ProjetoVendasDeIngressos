from fastapi import APIRouter, HTTPException
from typing import List
from bson import ObjectId
from app_api.schemas import EventoCreate, EventoResponse, PedidoCreate
from app_api.database import eventos_collection 
from app_api.producer import publicar_mensagem # <--- Import agora funciona!

router = APIRouter()

# --- ROTAS DE EVENTOS ---

@router.get("/eventos", response_model=List[EventoResponse])
async def listar_eventos():
    eventos = []
    async for evento in eventos_collection.find():
        evento["id"] = str(evento["_id"])
        eventos.append(evento)
    return eventos

@router.post("/eventos", response_model=EventoResponse)
async def criar_evento(evento: EventoCreate):
    evento_dict = evento.model_dump()
    resultado = await eventos_collection.insert_one(evento_dict)
    evento_dict["id"] = str(resultado.inserted_id)
    return evento_dict

# --- ROTA DE COMPRA ---

@router.post("/comprar")
async def comprar_ingresso(pedido: PedidoCreate):
    # 1. Verifica se evento existe
    try:
        evento_oid = ObjectId(pedido.evento_id)
    except:
        raise HTTPException(status_code=400, detail="ID do evento inválido")

    evento = await eventos_collection.find_one({"_id": evento_oid})
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    # --- MUDANÇA AQUI 👇 ---
    
    # Geramos um ID único para o pedido AGORA
    novo_pedido_id = str(ObjectId()) 

    # 2. Monta mensagem COM O ID
    mensagem = {
        "pedido_id": novo_pedido_id,  # <--- O Worker exige esse campo!
        "evento_id": pedido.evento_id,
        "usuario_id": pedido.usuario_id,
        "quantidade": pedido.quantidade,
        "status": "PENDENTE"
    }

    print(f"DEBUG: Enviando para fila -> {mensagem}")

    # 3. Envia para fila
    await publicar_mensagem(mensagem)

    return {
        "status": "recebido", 
        "mensagem": "Pedido em processamento", 
        "pedido_id": novo_pedido_id # Devolvemos o ID pro usuário saber
    }