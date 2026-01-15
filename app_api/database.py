import os
from motor.motor_asyncio import AsyncIOMotorClient

# Tenta pegar a variável do Docker, senão usa localhost
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

client = AsyncIOMotorClient(MONGO_URL)
db = client.vendas_ingressos

# Exportamos as coleções para facilitar o uso
eventos_collection = db.eventos
usuarios_collection = db.usuarios