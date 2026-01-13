from pydantic import BaseModel, Field, PositiveInt, PositiveFloat
from datetime import datetime
import uuid

# Modelo de Entrada (O que o usuário manda no Swagger)
class TicketPurchaseRequest(BaseModel):
    usuario_id: str = Field(..., description="ID do usuário que está comprando")
    evento_id: str = Field(..., description="ID do evento desejado")
    quantidade: PositiveInt = Field(..., description="Quantidade de ingressos")
    valor: PositiveFloat = Field(..., description="Valor total da compra") # Adicionado pois o Worker exige

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "usuario_id": "user_123",
                    "evento_id": "evento_rock_in_rio",
                    "quantidade": 2,
                    "valor": 500.00
                }
            ]
        }
    }

# Modelo da Mensagem (O que vai para a fila)
class TicketPurchaseMessage(TicketPurchaseRequest):
    pedido_id: str = Field(default_factory=lambda: str(uuid.uuid4())) # Renomeado de request_id
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat()) # Renomeado de created_at e formatado como string
    status: str = "CONFIRMADO" # O worker espera CONFIRMADO para salvar