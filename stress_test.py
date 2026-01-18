import asyncio
import httpx
import time
import uuid

# --- CONFIGURAÇÕES ---
BASE_URL = "http://127.0.0.1:8000"
REGISTER_URL = f"{BASE_URL}/api/v1/auth/register"
COMPRAR_URL = f"{BASE_URL}/api/v1/comprar" # Ajuste se houver prefixo /api/v1/

EVENTO_ID = "696bfcba752c88ddd05c2dd6" # ID real do seu evento
TOTAL_REQUISICOES = 50

async def registrar_e_comprar(client, i):
    # 1. Dados para UsuarioCreate
    user_payload = {
        "nome": f"Usuario Teste {i}",
        "email": f"teste_{uuid.uuid4().hex[:8]}@stress.com",
        "senha": "123"
    }
    
    try:
        # Registro do Usuário
        reg_resp = await client.post(REGISTER_URL, json=user_payload)
        if reg_resp.status_code != 200:
            print(f"Erro no Registro {i}: {reg_resp.text}")
            return

        usuario_id = reg_resp.json().get("id")

        # 2. Dados para PedidoCreate (Incluindo campos para evitar 422)
        compra_payload = {
            "evento_id": EVENTO_ID,
            "usuario_id": usuario_id,
            "quantidade": 1,
            "data_nascimento": "2000-01-01",
            "data_hora": "2026-01-17T21:20:02.010Z",
            "valor_total": 0,
            "status": "string"
        }

        compra_resp = await client.post(COMPRAR_URL, json=compra_payload)
        print(f"User {i} ({usuario_id}): Status {compra_resp.status_code}")

    except Exception as e:
        print(f"Erro na tarefa {i}: {e}")

async def rodar_teste():
    print(f"🚀 Iniciando Stress Test com {TOTAL_REQUISICOES} usuários diferentes...")
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [registrar_e_comprar(client, i) for i in range(TOTAL_REQUISICOES)]
        await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    print(f"\n✅ Teste finalizado em {duration:.2f} segundos.")

if __name__ == "__main__":
    asyncio.run(rodar_teste())