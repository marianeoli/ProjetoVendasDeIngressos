import asyncio
import json
from aio_pika import connect_robust
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from bson import ObjectId

# Conexão
RABBIT_URL = "amqp://guest:guest@rabbitmq:5672/"
MONGO_URL = "mongodb://mongos:27017"

# Conexão ao Cluster
client = AsyncIOMotorClient(MONGO_URL)
db = client.bilheteria # Banco

async def processar_vendas(message):
    payload = json.loads(message.body)
    
    try:
        # Verifica se o usuário que está tentando comprar existe
        usuario = await db.usuarios.find_one({"_id": payload["usuario_id"]})
        if not usuario:
            print(f"Erro: Usuário {payload['usuario_id']} não encontrado.")
            return

        # Operação atômica na coleção eventos (Controle de estoque)
        # O uso de find_one_and_update garante que o decremento seja seguro entre múltiplos workers
        evento_id = ObjectId(payload["evento_id"])
        resultado_estoque = await db.eventos.find_one_and_update(
            {
                "_id": evento_id, 
                "quantidade_disponivel": {"$gte": payload["quantidade"]}
            },
            {"$inc": {"quantidade_disponivel": -payload["quantidade"]}},
            return_document=True
        )

        if resultado_estoque:
            # Persistência na coleção vendas (Coleção Sharded)
            # O campo 'usuario_id' aqui é a Shard Key que vai distribuir o dado no cluster
            nova_venda = {
                "evento_id": evento_id,
                "usuario_id": payload["usuario_id"], 
                "quantidade": payload["quantidade"],
                "valor_total": payload["valor_total"],
                "data_hora": datetime.now(timezone.utc).isoformat(),
                "status": "CONFIRMADO",
                "detalhes_usuario": { "nome": usuario["nome"], "email": usuario["email"] } # Denormalização
            }
            
            await db.vendas.insert_one(nova_venda)
            print(f"Venda {payload.get('vendas_id', 'S/N')} gravada com sucesso no Cluster!")
        else:
            print(f"Falha: Stock esgotado para o evento {payload['evento_id']}")

    except Exception as e:
        print(f"Erro crítico no processamento: {e}")

async def main():
    while True:
        try:
            connection = await connect_robust(RABBIT_URL)
            channel = await connection.channel()
            
            # Garante que um worker não pegue mensagens demais se estiver lento
            await channel.set_qos(prefetch_count=1)

            queue = await channel.declare_queue("fila_vendas", durable=True)

            print("Worker aguardando pedidos dos 3 Shards...")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process(): # Envia ACK automático ao terminar
                        await processar_vendas(message)

        except Exception as e:
            print(f"Falha de conexão. {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())