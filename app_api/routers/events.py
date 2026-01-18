from fastapi import APIRouter, HTTPException
from typing import List
from bson import ObjectId
from app_api.schemas import EventoCreate, EventoResponse, PedidoCreate
from app_api.database import eventos_collection 
from app_api.producer import publicar_mensagem # <--- Import agora funciona!
from app_api.database import eventos_collection, vendas_collection

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

@router.get("/vendas/{pedido_id}")
async def consultar_status_pedido(pedido_id: str):
    """
    Busca os detalhes de uma venda no banco de dados usando o pedido_id.
    """
    # Busca na coleção 'vendas' que o Worker preenche
    venda = await vendas_collection.find_one({"pedido_id": pedido_id})
    
    if not venda:
        raise HTTPException(
            status_code=404, 
            detail="Pedido não encontrado ou ainda em processamento"
        )
    
    # Converte os campos ObjectId para String para o JSON não quebrar
    venda["id"] = str(venda["_id"])
    venda["evento_id"] = str(venda["evento_id"])
    venda["usuario_id"] = str(venda["usuario_id"])
    del venda["_id"] # Remove o original para evitar duplicidade
    
    return venda

@router.get("/vendas/usuario/{usuario_id}")
async def listar_vendas_usuario(usuario_id: str):
    """
    Retorna todo o histórico de compras de um usuário específico.
    """
    # 1. Validação do ID do usuário
    try:
        usuario_oid = ObjectId(usuario_id)
    except:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")

    # 2. Busca as vendas vinculadas ao usuario_id
    # Como usuario_id é a Shard Key, a consulta é direcionada e eficiente.
    vendas = []
    async for venda in vendas_collection.find({"usuario_id": usuario_oid}):
        venda["id"] = str(venda["_id"])
        venda["evento_id"] = str(venda["evento_id"])
        venda["usuario_id"] = str(venda["usuario_id"])
        del venda["_id"]
        vendas.append(venda)

    if not vendas:
        return {"mensagem": "Nenhuma compra encontrada para este usuário", "vendas": []}

    return vendas

@router.get("/dashboard/vendas")
async def dashboard_vendas():
    """
    Retorna um resumo de todos os eventos, 
    mostrando o estoque atual e o status das vendas.
    """
    resumo = []
    
    # Busca todos os eventos no banco sharded
    async for evento in eventos_collection.find():
        # Para cada evento, vamos contar quantas vendas foram confirmadas
        # Nota: Em clusters muito grandes, faríamos um lookup ou aggregation.
        total_vendido = 0
        vendas_cursor = vendas_collection.find({"evento_id": evento["_id"]})
        
        async for venda in vendas_cursor:
            total_vendido += venda.get("quantidade", 0)

        resumo.append({
            "evento": evento.get("nome"),
            "id_evento": str(evento["_id"]),
            "estoque_atual": evento.get("quantidade_disponivel"),
            "total_ingressos_vendidos": total_vendido,
            "preco_unitario": evento.get("preco")
        })
    
    return resumo