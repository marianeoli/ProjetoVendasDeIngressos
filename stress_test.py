import asyncio
import httpx
import time
import uuid

# --- CONFIGURAÇÕES ---
BASE_URL = "http://127.0.0.1:8000"
REGISTER_URL = f"{BASE_URL}/api/v1/auth/register"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
COMPRAR_URL = f"{BASE_URL}/api/v1/comprar"

EVENTO_ID = "697855bfeedca5bac500a14d" # <--- ID REAL DO SEU EVENTO
TOTAL_REQUISICOES = 51

async def registrar_logar_e_comprar(client, i):
    email = f"teste_{uuid.uuid4().hex[:8]}@stress.com"
    senha = "123"
    token = None # 1. Inicializamos como None para evitar o NameError

    try:
        # --- PASSO 1: REGISTRO ---
        user_payload = {"nome": f"User Stress {i}", "email": email, "senha": senha, "role": "cliente"}
        reg_resp = await client.post(REGISTER_URL, json=user_payload)
        
        if reg_resp.status_code != 200:
            print(f"Tarefa {i} - Erro Registro: {reg_resp.status_code}")
            return

        # --- PASSO 2: LOGIN (O PULO DO GATO) ---
        # O FastAPI (OAuth2) espera 'username' e 'password' via FORM DATA
        login_data = {
            "username": email,
            "password": senha
        }
        
        # USAMOS 'data=' para enviar como formulário, não 'json='
        login_resp = await client.post(LOGIN_URL, data=login_data)

        if login_resp.status_code == 200:
            token = login_resp.json().get("access_token")
        else:
            print(f"Tarefa {i} - Erro Login: {login_resp.status_code} - {login_resp.text}")
            return

        # --- PASSO 3: COMPRA ---
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            compra_payload = {
                "evento_id": EVENTO_ID,
                "usuario_id": "60d5ecb5b4877ed35e7d51cc", 
                "quantidade": 1,
                "data_nascimento": "2000-01-01",
                "data_hora": "2026-01-27T10:00:00Z",
                "valor_total": 0,
                "status": "PENDENTE"
            }
            compra_resp = await client.post(COMPRAR_URL, json=compra_payload, headers=headers)
            print(f"Tarefa {i} - Compra: {compra_resp.status_code}")

    except Exception as e:
        print(f"Erro crítico na tarefa {i}: {e}")
        
async def rodar_teste():
    print(f"🚀 Stress Test Protegido: {TOTAL_REQUISICOES} usuários com JWT...")
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [registrar_logar_e_comprar(client, i) for i in range(TOTAL_REQUISICOES)]
        await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    print(f"\n✅ Teste finalizado em {duration:.2f} segundos.")

if __name__ == "__main__":
    asyncio.run(rodar_teste())