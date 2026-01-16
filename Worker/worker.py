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
        # --- AJUSTE 1: Conversão de String para ObjectId ---
        # Obrigatório para o MongoDB achar os documentos
        try:
            usuario_oid = ObjectId(payload["usuario_id"])
            evento_oid = ObjectId(payload["evento_id"])
        except Exception as e:
            print(f"Erro: IDs inválidos recebidos. {e}")
            return

        # Verifica se o usuário existe (Usando o ID convertido)
        usuario = await db.usuarios.find_one({"_id": usuario_oid})
        if not usuario:
            print(f"Erro: Usuário {payload['usuario_id']} não encontrado.")
            return

        # --- AJUSTE 2: Calcular Valor Total ---
        # Como a API não manda o preço, buscamos o evento para calcular
        dados_evento = await db.eventos.find_one({"_id": evento_oid})
        if not dados_evento:
            print("Erro: Evento não encontrado para consultar preço.")
            return
            
        preco_unitario = dados_evento.get("preco", 0)
        valor_total_calculado = preco_unitario * payload["quantidade"]

        # Operação atômica na coleção eventos (Controle de estoque)
        resultado_estoque = await db.eventos.find_one_and_update(
            {
                "_id": evento_oid, # Usando ID convertido
                "quantidade_disponivel": {"$gte": payload["quantidade"]}
            },
            {"$inc": {"quantidade_disponivel": -payload["quantidade"]}},
            return_document=True
        )

        if resultado_estoque:
            # Persistência na coleção vendas (Coleção Sharded)
            # O campo 'usuario_id' é sua Shard Key. Passando como ObjectId, o Mongo distribui corretamente.
            nova_venda = {
                "pedido_id": payload.get("pedido_id"),
                "evento_id": evento_oid,
                "usuario_id": usuario_oid, 
                "quantidade": payload["quantidade"],
                "valor_total": valor_total_calculado,
                "data_hora": datetime.now(timezone.utc).isoformat(),
                "status": "CONFIRMADO",
                "detalhes_usuario": { "nome": usuario["nome"], "email": usuario["email"] }
            }
            
            await db.vendas.insert_one(nova_venda)
            print(f"Venda confirmada! ID: {payload.get('pedido_id')}")
        else:
            print(f"Falha: Estoque esgotado para o evento {payload['evento_id']}")

    except Exception as e:
        print(f"Erro crítico no processamento: {e}")

async def main():
    while True:
        try:
            connection = await connect_robust(RABBIT_URL)
            channel = await connection.channel()
            
            await channel.set_qos(prefetch_count=1)

            # --- AJUSTE 3: Nome da fila correto ---
            queue = await channel.declare_queue("fila_pedidos", durable=True)

            print("Worker aguardando na fila 'fila_pedidos'...")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process(): 
                        await processar_vendas(message)

        except Exception as e:
            print(f"Falha de conexão: {e}. Tentando em 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())