import os
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import uvicorn
import json
from providers.z_api import ZApiProvider

# Cria a instância do FastAPI
app = FastAPI(title="EquiBid Webhook")

# É uma boa prática definir o modelo de dados esperado


class WebhookPayload(BaseModel):
    zaapId: str
    messageId: str
    phone: str
    text: str | None = None
    # Adicione outros campos que a Z-API envia e que são importantes para você


# Instancia o provider
try:
    z_api = ZApiProvider()
except RuntimeError as e:
    print(f"ERRO CRÍTICO: {e}")
    z_api = None


@app.post("/webhook")
async def receber_webhook(payload: Request):
    """Endpoint para receber e processar webhooks da Z-API."""
    if not z_api:
        raise HTTPException(
            status_code=500, detail="Z-API Provider não inicializado")

    dados_recebidos = await payload.json()
    print("\n--- ✅ MENSAGEM RECEBIDA (VIA WEBHOOK) ---")
    print(json.dumps(dados_recebidos, indent=2))

    # TODO: Aqui vai a sua lógica principal.
    # Ex: 1. Pegar o `messageId` ou `phone` da resposta.
    #     2. Buscar no banco de dados a notificação original relacionada a esse ID.
    #     3. Se a resposta for "sim" ou "1", chamar o z_api.send_text() com os detalhes do lote.
    #     4. Se a resposta for "não" ou "2", chamar o z_api.send_text() com o link para editar a busca.
    #     5. Atualizar o status da notificação no banco de dados.

    return {"status": "success", "message": "Webhook processado"}

if __name__ == "__main__":
    print("🚀 Iniciando servidor de Webhook com Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
