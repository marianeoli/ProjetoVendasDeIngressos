import aio_pika
import os
from shared.schemas import TicketPurchaseMessage

# Configurações de conexão (Padrão do Docker: guest/guest)
rabbit_host = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_URL = f"amqp://guest:guest@{rabbit_host}:5672/"
QUEUE_NAME = "fila_pedidos"

async def publish_message(message: TicketPurchaseMessage):
    """
    Conecta ao RabbitMQ e publica a mensagem de compra na fila.
    """
    # Conectar ao Broker
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    
    async with connection:
        # Criar um canal de comunicação
        channel = await connection.channel()
        
        # Declarar a fila (garante que ela existe)
        # 'durable=True' garante que a fila sobreviva se o RabbitMQ reiniciar
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        
        # Preparação da mensagem
        # Transformamos o objeto Pydantic em JSON string e depois em bytes
        message_body = message.model_dump_json().encode("utf-8")
        
        # Publicar
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT # Mensagem salva em disco
            ),
            routing_key=QUEUE_NAME,
        )
        
        print(f" [x] Enviado para fila: {message.pedido_id}")