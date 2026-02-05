from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from bson import ObjectId
from datetime import datetime
from app_api.schemas import EventoCreate, EventoResponse, PedidoCreate, TokenData, HistoricoVendaResponse, EventoUpdate
from app_api.database import eventos_collection, vendas_collection
from app_api.producer import publicar_mensagem
from app_api.routers.auth import obter_usuario_atual, obter_admin_atual

router = APIRouter()

# --- 1. ROTAS DE EVENTOS (CRUD) ---

@router.get("/eventos", response_model=List[EventoResponse])
async def listar_eventos():
    eventos = []
    async for evento in eventos_collection.find():
        evento["id"] = str(evento["_id"])
        evento["preco"] = evento.get("preco") or 0.0
        evento["status"] = evento.get("status", "ATIVO") 
        eventos.append(evento)
    return eventos

@router.post("/eventos", response_model=EventoResponse)
async def criar_evento(evento: EventoCreate):
    evento_dict = evento.model_dump()
    resultado = await eventos_collection.insert_one(evento_dict)
    evento_dict["id"] = str(resultado.inserted_id)
    return evento_dict

@router.put("/eventos/{evento_id}", response_model=EventoResponse)
async def atualizar_evento(
    evento_id: str, 
    dados: EventoUpdate, 
    usuario: TokenData = Depends(obter_admin_atual)
):
    dados_atualizacao = {k: v for k, v in dados.model_dump().items() if v is not None}

    if not dados_atualizacao:
        raise HTTPException(status_code=400, detail="Nenhum dado enviado para atualização")

    resultado = await eventos_collection.find_one_and_update(
        {"_id": ObjectId(evento_id)},
        {"$set": dados_atualizacao},
        return_document=True
    )

    if not resultado:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    resultado["id"] = str(resultado["_id"])
    return resultado

@router.delete("/eventos/{evento_id}")
async def deletar_evento(
    evento_id: str, 
    usuario: TokenData = Depends(obter_admin_atual)):
    resultado = await eventos_collection.delete_one({"_id": ObjectId(evento_id)})

    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    return {"status": "sucesso", "mensagem": "Evento excluído permanentemente."}


# --- 2. ROTA DE COMPRA (COM CORREÇÃO DE OBJECTID) ---
@router.post("/comprar")
async def comprar_ingresso(pedido: PedidoCreate, usuario: TokenData = Depends(obter_usuario_atual)):
    # 1. Valores padrão
    categoria_nome = getattr(pedido, 'categoria', 'Pista')
    qtd = pedido.quantidade
    
    # 2. TENTATIVA DE RESERVA ATÔMICA
    filtro = {
        "_id": ObjectId(pedido.evento_id),
        "status": "ATIVO",
        "quantidade_disponivel": {"$gte": qtd},
        "categorias": {
            "$elemMatch": {
                "nome": categoria_nome,
                "disponivel": {"$gte": qtd}
            }
        }
    }

    atualizacao = {
        "$inc": {
            "quantidade_disponivel": -qtd,
            "categorias.$.disponivel": -qtd
        }
    }

    evento_atualizado = await eventos_collection.find_one_and_update(
        filtro,
        atualizacao,
        return_document=True
    )

    # 3. Validação de Estoque
    if not evento_atualizado:
        raise HTTPException(
            status_code=400, 
            detail=f"Não há ingressos disponíveis para a categoria '{categoria_nome}'."
        )

    # 4. Preço e Meia-Entrada
    novo_pedido_id = str(ObjectId()) 
    
    cat_obj = next((c for c in evento_atualizado['categorias'] if c['nome'] == categoria_nome), None)
    preco_base = cat_obj['preco'] if cat_obj else (evento_atualizado.get("preco") or 0.0)

    tipo_ingresso_str = getattr(pedido, 'tipo_ingresso', 'Inteira')
    tipo_normalizado = tipo_ingresso_str.lower()
    
    fator_preco = 1.0
    if tipo_normalizado in ['meia', 'idoso', 'estudante']:
        fator_preco = 0.5
    
    valor_real_unitario = preco_base * fator_preco

    # --- MONTAGEM DA MENSAGEM ---
    # Correção Crítica: Salvamos usuario_id e evento_id como ObjectId no banco
    # Isso garante que as buscas (pagamento, histórico) funcionem corretamente.
    mensagem = {
        "pedido_id": novo_pedido_id,
        "evento_id": ObjectId(pedido.evento_id),   # <--- AGORA COMO OBJECTID
        "nome_evento": evento_atualizado.get("nome"),
        "usuario_id": ObjectId(usuario.usuario_id), # <--- AGORA COMO OBJECTID
        "quantidade": qtd,
        "valor_unitario": valor_real_unitario,
        "valor_total": qtd * valor_real_unitario,
        "categoria": categoria_nome,
        "tipo_ingresso": tipo_ingresso_str,
        "status": "RESERVADO",
        "data_hora": datetime.now().isoformat()
    }

    # 5. Salva no MongoDB (Com ObjectIds)
    await vendas_collection.insert_one(mensagem)

    # 6. Prepara para JSON (RabbitMQ)
    # Convertemos de volta para String apenas para enviar na fila, pois JSON não aceita ObjectId
    mensagem["_id"] = str(mensagem["_id"])
    mensagem["evento_id"] = str(mensagem["evento_id"])
    mensagem["usuario_id"] = str(mensagem["usuario_id"])

    await publicar_mensagem(mensagem)

    return {"status": "reservado", "pedido_id": novo_pedido_id}


# --- 3. HISTÓRICO ---
@router.get("/vendas/historico", response_model=List[HistoricoVendaResponse])
async def obter_historico(token_data: TokenData = Depends(obter_usuario_atual)):
    usuario_oid = ObjectId(token_data.usuario_id)
    
    cursor = vendas_collection.find({
        "usuario_id": usuario_oid,
        "status": {"$nin": ["ERRO_ESTOQUE_ESGOTADO", "CANCELADO"]}
    }).sort("data_hora", -1)
    
    vendas_raw = await cursor.to_list(length=100)
    
    vendas_processadas = []
    for v in vendas_raw:
        v["id"] = str(v["_id"])
        v["usuario_id"] = str(v.get("usuario_id"))
        v["pedido_id"] = v.get("pedido_id") or v["id"]
        
        # Populate seguro
        nome_show = v.get("nome_evento")
        if not nome_show and v.get("evento_id"):
            # Só busca se evento_id for válido
            try:
                evento_doc = await eventos_collection.find_one({"_id": v.get("evento_id")})
                nome_show = evento_doc.get("nome") if evento_doc else "Evento Removido"
            except:
                nome_show = "Evento Indisponível"
        
        v["evento_id"] = nome_show or "Evento"
        
        v["valor_unitario"] = v.get("valor_unitario") or 0.0
        v["valor_total"] = v.get("valor_total") or (v.get("quantidade", 0) * v["valor_unitario"])
        v["data_processamento"] = v.get("data_processamento") or v.get("data_hora") or datetime.now()
        
        vendas_processadas.append(v)
        
    return vendas_processadas


# --- 4. CONSULTA DE STATUS ---
@router.get("/vendas/{pedido_id}")
async def consultar_status_pedido(pedido_id: str, usuario: TokenData = Depends(obter_usuario_atual)):
    venda = await vendas_collection.find_one({"pedido_id": pedido_id})
    
    if not venda:
        raise HTTPException(status_code=404, detail="Aguardando processamento...")
        
    venda["id"] = str(venda["_id"])
    venda["usuario_id"] = str(venda.get("usuario_id", ""))
    
    # Tratamento seguro para evento_id que agora é ObjectId no banco
    ev_id = venda.get("evento_id", "")
    venda["evento_id"] = str(ev_id)

    del venda["_id"]
    return venda


# --- 5. DASHBOARD ADMIN ---
@router.get("/dashboard/vendas")
async def dashboard_vendas(usuario: TokenData = Depends(obter_admin_atual)):
    resumo = []
    
    async for evento in eventos_collection.find():
        ev_id = evento["_id"]
        
        # Busca híbrida para compatibilidade (String antiga ou ObjectId novo)
        vendas_evento = await vendas_collection.find({
            "$or": [{"evento_id": ev_id}, {"evento_id": str(ev_id)}],
            "status": {"$in": ["PAGO", "RESERVADO", "PENDENTE"]}
        }).to_list(None)
        
        total_vendido = sum(v.get("quantidade", 0) for v in vendas_evento)
        
        arrecadacao = 0.0
        for v in vendas_evento:
            val_venda = v.get("valor_total")
            if not val_venda:
                val_venda = v.get("quantidade", 0) * v.get("valor_unitario", 0)
            arrecadacao += val_venda

        resumo.append({
            "evento": evento.get("nome"),
            "id_evento": str(ev_id),
            "estoque_atual": evento.get("quantidade_disponivel"),
            "total_ingressos_vendidos": total_vendido,
            "preco_unitario": evento.get("preco"),
            "arrecadacao_total": arrecadacao,
            "status": evento.get("status", "ATIVO")
        })

    return resumo

# --- 6. AÇÕES ADMINISTRATIVAS ---

@router.patch("/eventos/{evento_id}/status")
async def alterar_status_evento(
    evento_id: str, 
    status: str, 
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
    # Converte o ID do usuário logado para ObjectId para bater com o banco
    usuario_oid = ObjectId(usuario.usuario_id)

    resultado = await vendas_collection.update_one(
        {"pedido_id": pedido_id, "usuario_id": usuario_oid},
        {"$set": {"status": "PAGO", "data_confirmacao": datetime.now()}}
    )
    
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Reserva não encontrada (Verifique se é uma compra antiga).")
    
    return {"status": "sucesso", "mensagem": "Pagamento confirmado!"}

@router.post("/vendas/{pedido_id}/cancelar")
async def cancelar_reserva(pedido_id: str, usuario: TokenData = Depends(obter_usuario_atual)):
    venda = await vendas_collection.find_one({"pedido_id": pedido_id})
    
    if not venda or venda["status"] == "PAGO":
        raise HTTPException(status_code=400, detail="Não é possível cancelar uma venda paga.")

    # Devolve ao estoque
    # Agora que evento_id é ObjectId no banco, a busca funcionará
    await eventos_collection.update_one(
        {"_id": venda["evento_id"]},
        {"$inc": {
            "quantidade_disponivel": venda["quantidade"],
            "categorias.$[elem].disponivel": venda["quantidade"]
        }},
        array_filters=[{"elem.nome": venda.get("categoria", "Pista")}]
    )

    # Marca como cancelado
    await vendas_collection.update_one(
        {"pedido_id": pedido_id},
        {"$set": {"status": "CANCELADO"}}
    )
    
    return {"status": "cancelado", "mensagem": "Ingresso devolvido ao estoque."}