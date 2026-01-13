import asyncio
import json
from aio_pika import connect_robust
from motor.motor_asyncio import AsyncIOMotorClient

RABBIT_URL = "amqp://guest:guest@rabbitmq:5672/"
MONGO_URL = "mongodb://mongos:27017"

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.ingressos
pedidos = db.pedidos

async def processar_pedido(msg):
    pedido = json.loads(msg.body)
    try:
        await pedidos.insert_one({
            "_id": pedido["pedido_id"],
            "evento_id": pedido["evento_id"],
            "usuario_id": pedido["usuario_id"],
            "quantidade": pedido["quantidade"],
            "valor": pedido["valor"],
            "status": "CONFIRMADO",
            "timestamp": pedido["timestamp"]
        })

        print("Pedido gravado:", pedido, flush=True)

    except Exception as e:
        print(f"Erro ou pedido duplicado: {e}", flush=True)

async def main():
    while True:
        try:
            connection = await connect_robust(RABBIT_URL)
            channel = await connection.channel()

            queue = await channel.declare_queue("fila_pedidos", durable=True)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        await processar_pedido(message)

            break

        except Exception as e:
            print(f"Aguardando RabbitMQ... {e}", flush=True)
            await asyncio.sleep(5)

asyncio.run(main())
