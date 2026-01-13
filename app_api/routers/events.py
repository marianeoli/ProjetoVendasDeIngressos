from fastapi import APIRouter, HTTPException
from shared.schemas import TicketPurchaseRequest, TicketPurchaseMessage
from app_api.producer import publish_message

router = APIRouter()

@router.post("/comprar", status_code=202)
async def buy_ticket(purchase: TicketPurchaseRequest):
    # Cria a mensagem completa (com ID e Data)
    message = TicketPurchaseMessage(**purchase.model_dump())
    
    try:
        # Envia para o RabbitMQ
        await publish_message(message)
        
        return {
            "request_id": message.pedido_id,
            "status": "received",
            "message": "Pedido recebido e enfileirado com sucesso!"
        }
        
    except Exception as e:
        print(f"Erro ao conectar no RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar pedido.")