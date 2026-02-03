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
        evento["preco"] = evento.get("preco") or 0.0
        evento["status"] = evento.get("status", "ATIVO") # Garante que o status vá para o Front
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

    if evento.get("status") == "PAUSADO":
        raise HTTPException(status_code=400, detail="Vendas suspensas para este evento.")

    if evento.get("quantidade_disponivel") <= 0:
        raise HTTPException(status_code=400, detail="Ingressos esgotados!")

    novo_pedido_id = str(ObjectId()) 
    
    # As variáveis 'setor' e 'tipo' precisam vir do seu PedidoCreate no schemas.py
    # Se ainda não existem lá, você deve adicioná-las.
    mensagem = {
        "pedido_id": novo_pedido_id,
        "evento_id": pedido.evento_id,
        "nome_evento": evento.get("nome"),
        "usuario_id": usuario.usuario_id,
        "quantidade": pedido.quantidade,
        "valor_unitario": evento.get("preco") or 0.0,
        "categoria": getattr(pedido, 'categoria', 'Pista'), # Fallback se não enviado
        "tipo_ingresso": getattr(pedido, 'tipo_ingresso', 'Inteira'),
        "status": "PENDENTE"
    }
    await publicar_mensagem(mensagem)
    return {"status": "recebido", "pedido_id": novo_pedido_id}

# --- 3. HISTÓRICO (DEVE VIR ANTES DA ROTA COM ID) ---
@router.get("/vendas/historico", response_model=List[HistoricoVendaResponse])
async def obter_historico(token_data: TokenData = Depends(obter_usuario_atual)):
    usuario_oid = ObjectId(token_data.usuario_id)
    cursor = vendas_collection.find({"usuario_id": usuario_oid})
    vendas_raw = await cursor.to_list(length=100)
    
    vendas_processadas = []
    for v in vendas_raw:
        v["id"] = str(v["_id"])
        v["usuario_id"] = str(v.get("usuario_id"))
        v["pedido_id"] = v.get("pedido_id") or v["id"]
        
        # Nome do Evento
        nome_show = v.get("nome_evento")
        if not nome_show:
            evento_doc = await eventos_collection.find_one({"_id": v.get("evento_id")})
            nome_show = evento_doc.get("nome") if evento_doc else "Evento"
        
        v["evento_id"] = nome_show
        
        # --- CÁLCULO DO TOTAL ---
        # Garante que valor_total exista para o Pydantic não dar erro
        v["valor_unitario"] = v.get("valor_unitario") or 0.0
        v["valor_total"] = v.get("valor_total") or (v.get("quantidade", 0) * v["valor_unitario"])
        
        v["data_processamento"] = v.get("data_processamento") or v.get("data_hora") or datetime.now()
        vendas_processadas.append(v)
        
    return vendas_processadas

# --- 4. CONSULTA DE STATUS ---
@router.get("/vendas/{pedido_id}")
async def consultar_status_pedido(pedido_id: str, usuario: TokenData = Depends(obter_usuario_atual)):
    # Busca pelo pedido_id (string) gerado na rota /comprar
    venda = await vendas_collection.find_one({"pedido_id": pedido_id})
    
    if not venda:
        # Retornamos 404. O JavaScript do seu index.html já sabe tratar isso e tentar de novo.
        raise HTTPException(status_code=404, detail="Aguardando Worker...")
        
    venda["id"] = str(venda["_id"])
    venda["usuario_id"] = str(venda.get("usuario_id", ""))
    venda["evento_id"] = str(venda.get("evento_id", ""))

    del venda["_id"]

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
            "arrecadacao_total": total_vendido * evento.get("valor_total", 0),
            "status": evento.get("status", "ATIVO")
        })

    return resumo

# Alterar status ingresso

@router.patch("/eventos/{evento_id}/status")
async def alterar_status_evento(
    evento_id: str, 
    status: str, # "ATIVO", "PAUSADO" ou "ESGOTADO"
    usuario: TokenData = Depends(obter_admin_atual)
):
    resultado = await eventos_collection.update_one(
        {"_id": ObjectId(evento_id)},
        {"$set": {"status": status}}
    )
    
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
        
    return {"status": "sucesso", "novo_status": status}

@router.post("/vendas/{pedido_id}/confirmar")
async def confirmar_pagamento(pedido_id: str, usuario: TokenData = Depends(obter_usuario_atual)):
    # 1. Transforma o ID do usuário logado em ObjectId (pois é como o Worker salvou)
    usuario_oid = ObjectId(usuario.usuario_id)

    # 2. Faz o update incluindo a SHARD KEY (usuario_id) no filtro
    # Isso permite que o mongos direcione a requisição para o shard correto
    resultado = await vendas_collection.update_one(
        {
            "pedido_id": pedido_id, 
            "usuario_id": usuario_oid  # <--- O SEGREDO ESTÁ AQUI
        },
        {"$set": {"status": "PAGO", "data_confirmacao": datetime.now()}}
    )
    
    if resultado.matched_count == 0:
        raise HTTPException(
            status_code=404, 
            detail="Reserva não encontrada ou Shard Key incorreta."
        )
    
    return {"status": "sucesso", "mensagem": "Pagamento confirmado via Shard!"}

@router.post("/vendas/{pedido_id}/cancelar")
async def cancelar_reserva(pedido_id: str, usuario: TokenData = Depends(obter_usuario_atual)):
    venda = await vendas_collection.find_one({"pedido_id": pedido_id})
    
    if not venda or venda["status"] == "PAGO":
        raise HTTPException(status_code=400, detail="Não é possível cancelar uma venda paga.")

    # 1. Devolve ao estoque de forma atômica
    await eventos_collection.update_one(
        {"_id": venda["evento_id"]},
        {"$inc": {"quantidade_disponivel": venda["quantidade"]}}
    )

    # 2. Atualiza o status da venda
    await vendas_collection.update_one(
        {"pedido_id": pedido_id},
        {"$set": {"status": "CANCELADO"}}
    )
    
    return {"status": "cancelado", "mensagem": "Ingresso devolvido ao estoque."}
