from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from bson import ObjectId
from datetime import datetime
from app_api.schemas import EventoCreate, EventoResponse, PedidoCreate, TokenData, HistoricoVendaResponse
from app_api.database import eventos_collection, vendas_collection
from app_api.producer import publicar_mensagem
from app_api.routers.auth import obter_usuario_atual, obter_admin_atual

router = APIRouter()

# --- 1. ROTAS DE EVENTOS ---
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

# --- 2. ROTA DE COMPRA ---
@router.post("/comprar")
async def comprar_ingresso(pedido: PedidoCreate, usuario: TokenData = Depends(obter_usuario_atual)):
    evento = await eventos_collection.find_one({"_id": ObjectId(pedido.evento_id)})
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    novo_pedido_id = str(ObjectId()) 
    mensagem = {
        "pedido_id": novo_pedido_id,
        "evento_id": pedido.evento_id,
        "nome_evento": evento.get("nome"), # Guardamos o nome para o histórico ser bonito
        "usuario_id": usuario.usuario_id,
        "quantidade": pedido.quantidade,
        "valor_unitario": evento.get("preco", 0.0),
        "status": "PENDENTE"
    }
    await publicar_mensagem(mensagem)
    return {"status": "recebido", "pedido_id": novo_pedido_id}

# --- 3. HISTÓRICO (DEVE VIR ANTES DA ROTA COM ID) ---
@router.get("/vendas/historico", response_model=List[HistoricoVendaResponse])
async def obter_historico(token_data: TokenData = Depends(obter_usuario_atual)):
    usuario_oid = ObjectId(token_data.usuario_id)
    
    # Busca vendas do usuário logado
    cursor = vendas_collection.find({"usuario_id": usuario_oid})
    vendas_raw = await cursor.to_list(length=100)
    
    vendas_processadas = []
    for v in vendas_raw:
        v["id"] = str(v["_id"])
        
        # Tenta pegar o nome salvo pelo Worker. Se não tiver, busca no banco de eventos.
        nome_show = v.get("nome_evento")
        if not nome_show:
            ev_id = v.get("evento_id")
            # Busca o evento para pegar o nome real
            evento_doc = await eventos_collection.find_one({"_id": ObjectId(ev_id) if isinstance(ev_id, str) else ev_id})
            nome_show = evento_doc.get("nome") if evento_doc else "Evento Removido"
        
        v["evento_id"] = nome_show # O Front exibirá o Nome agora
        v["valor_unitario"] = v.get("valor_unitario") or v.get("valor_total") or 0.0
        v["data_processamento"] = v.get("data_processamento") or v.get("data_hora") or datetime.now()
        vendas_processadas.append(v)
        
    return vendas_processadas

# --- 4. CONSULTA DE STATUS ---
@router.get("/vendas/{pedido_id}")
async def consultar_status_pedido(pedido_id: str, usuario: TokenData = Depends(obter_usuario_atual)):
    # Busca pelo pedido_id (string) que geramos na rota /comprar
    venda = await vendas_collection.find_one({"pedido_id": pedido_id})
    
    if not venda:
        # Retornamos 404. O JavaScript do seu index.html já sabe tratar isso e tentar de novo.
        raise HTTPException(status_code=404, detail="Aguardando Worker...")
        
    venda["id"] = str(venda["_id"])
    return venda

# --- 5. DASHBOARD ADMIN ---
@router.get("/dashboard/vendas")
async def dashboard_vendas(usuario: TokenData = Depends(obter_admin_atual)):
    resumo = []
    async for evento in eventos_collection.find():
        ev_id = evento["_id"]
        
        # BUSCA HÍBRIDA: Procura o ID como ObjectId E como String
        vendas_evento = await vendas_collection.find({
            "$or": [
                {"evento_id": ev_id},
                {"evento_id": str(ev_id)}
            ]
        }).to_list(None)
        
        total_vendido = sum(v.get("quantidade", 0) for v in vendas_evento)
        
        resumo.append({
            "evento": evento.get("nome"),
            "id_evento": str(ev_id),
            "estoque_atual": evento.get("quantidade_disponivel"),
            "total_ingressos_vendidos": total_vendido,
            "preco_unitario": evento.get("preco"),
            "arrecadacao_total": total_vendido * evento.get("preco", 0)
        })
    return resumo