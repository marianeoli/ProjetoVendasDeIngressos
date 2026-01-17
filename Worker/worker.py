import asyncio
import json
from aio_pika import connect_robust
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os

# Use variáveis de ambiente (boa prática do Docker)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongos:27017")
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")

async def processar_vendas(message, db): # Receba o db como argumento
    payload = json.loads(message.body)
    
    try:
        # .strip() previne caracteres invisíveis/newlines do JSON
        u_id = payload["usuario_id"].strip()
        usuario_oid = ObjectId(u_id)
        
        # DEBUG: Log para conferir o que o worker está tentando buscar
        print(f"Buscando usuário: {usuario_oid} tipo: {type(usuario_oid)}")

        usuario = await db.usuarios.find_one({"_id": usuario_oid})
        
        if not usuario:
            # TENTATIVA DE ESCAPE: Se não achar como ObjectId, tenta como String
            # Isso ajuda a diagnosticar se o erro é o tipo de dado
            usuario = await db.usuarios.find_one({"_id": u_id})
            if usuario:
                print("AVISO: Usuário encontrado como STRING, não como ObjectId!")
            else:
                print(f"Erro: Usuário {u_id} não encontrado de nenhuma forma.")
                return

        # ... resto do código (vendas, estoque, etc)
        print(f"Usuário encontrado: {usuario['nome']}")

    except Exception as e:
        print(f"Erro no processamento: {e}")

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