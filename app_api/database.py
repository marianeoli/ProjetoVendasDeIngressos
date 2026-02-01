import os
from motor.motor_asyncio import AsyncIOMotorClient

# Tenta pegar a variável do Docker, senão usa localhost
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongos:27017")

client = AsyncIOMotorClient(
    MONGO_URL,
    retryWrites=True,           # Tenta novamente se um shard oscilar
    serverSelectionTimeoutMS=5000
)

db = client.bilheteria

# Exportamos as coleções para facilitar o uso
eventos_collection = db.eventos
vendas_collection = db.vendas
usuarios_collection = db.usuarios
