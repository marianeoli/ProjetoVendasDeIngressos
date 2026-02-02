import asyncio
import os
import json
from aio_pika import connect_robust
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone

# Use variáveis de ambiente (boa prática do Docker)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongos:27017")
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")

async def processar_vendas(message, db):
    payload = json.loads(message.body)
    pedido_id = payload.get("pedido_id")
    
    try:
        # --- 1. FILTRO DE IDEMPOTÊNCIA ---
        # Verificamos se o pedido já existe na coleção de vendas
        pedido_ja_existe = await db.vendas.find_one({"pedido_id": pedido_id})
        
        if pedido_ja_existe:
            print(f"Pedido {pedido_id} já foi processado anteriormente. Ignorando.")
            return

        # --- 2. PREPARAÇÃO DOS DADOS ---
        u_id = payload["usuario_id"].strip()
        e_id = payload["evento_id"].strip()
        usuario_oid = ObjectId(u_id)
        evento_oid = ObjectId(e_id)
        quantidade = payload.get("quantidade", 1)

        # --- 3. VALIDAÇÃO DO USUÁRIO ---
        usuario = await db.usuarios.find_one({"_id": usuario_oid})
        if not usuario:
            print(f"Erro: Usuário {u_id} não encontrado.")
            return

        print(f"Processando Pedido: {pedido_id} | Usuário: {usuario['nome']}")

        # --- 4. TENTATIVA ATÓMICA DE ESTOQUE ---
        resultado_estoque = await db.eventos.update_one(
            {"_id": evento_oid, "quantidade_disponivel": {"$gte": quantidade}},
            {"$inc": {"quantidade_disponivel": -quantidade}}
        )
        
        quantidade = payload.get("quantidade", 1)
        valor_unitario = payload.get("valor_unitario", 0.0)
        valor_total = quantidade * valor_unitario # Cálculo do total

        # --- 5. DEFINIÇÃO DO RESULTADO ---
        venda_doc = {
            "pedido_id": pedido_id,
            "evento_id": evento_oid,  # ObjectId
            "usuario_id": usuario_oid, # ObjectId (Importante para o Sharding na AWS!)
            "quantidade": quantidade,
            "valor_total": valor_total,
            "data_hora": datetime.now(timezone.utc),      # Alinhado com Schema
            "status": "RESERVADO" if resultado_estoque.modified_count > 0 else "ERRO_ESTOQUE"
        }

        if resultado_estoque.modified_count > 0: 
            venda_doc["status"] = "RESERVADO" 
            print(f"SUCESSO: Venda {pedido_id} reservada no estoque.")
        
        else:
            venda_doc["status"] = "ERRO_ESTOQUE_ESGOTADO"
            print(f"--ERRO-- Estoque esgotado para o pedido {pedido_id}.")

        # --- 6. GRAVAÇÃO FINAL (A MEMÓRIA DO SISTEMA) ---
        await db.vendas.insert_one(venda_doc)

    except Exception as e:
        print(f"Erro crítico no processamento: {e}")

async def main():
    # INICIALIZAÇÃO DENTRO DO MAIN
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.bilheteria
    
    print("Conectando ao MongoDB e RabbitMQ...")
    
    while True:
        try:
            connection = await connect_robust(RABBIT_URL)
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            queue = await channel.declare_queue("fila_pedidos", durable=True)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process(): 
                        # Passa o banco de dados para a função
                        await processar_vendas(message, db)

        except Exception as e:
            print(f"Conexão falhou: {e}. Reiniciando em 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
