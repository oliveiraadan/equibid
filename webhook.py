from fastapi import FastAPI, Request, HTTPException
import uvicorn
import json
from dotenv import load_dotenv
from providers.telegram import TelegramProvider
import os

# Carrega as variáveis de ambiente do .env
load_dotenv()

# --- Simulação de Banco de Dados ---
# Em um projeto real, você buscaria estes dados do seu banco de dados PostgreSQL.


def buscar_notificacao_por_correlation_id(correlation_id: str):
    """Simula a busca dos dados da notificação original usando o ID de correlação."""
    print(
        f"WEBHOOK: Buscando dados no DB para o correlation_id: {correlation_id}")
    # Retorna um dicionário com os dados do lote para que o webhook saiba o que responder.
    # Este dicionário precisa ser consistente com o que o worker teria acesso.
    return {
        "correlation_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "user_name": "Daniel",
        "saved_search_details": "Cavalo Quarto de Milha, Fêmea, até 3 anos",
        "found_lot": {
            "id": 12345,
            "nome": "Lote 25 - Potra Quarto de Milha Pura",
            "leilao": "Leilão Virtual Haras Primavera",
            "leiloeira": "Agro Leilões",
            "data_nascimento": "2023-01-15",
            "raca": "Quarto de Milha",
            "sexo": "Fêmea",
            "pai": "Campeão Mr. King",
            "mae": "Dama da Primavera",
            "url": "https://www.equibid.com.br/lotes/12345"
        }
    }


# --- Lógica do Webhook ---
app = FastAPI(title="EquiBid Webhook")

try:
    telegram = TelegramProvider()
except RuntimeError as e:
    print(f"ERRO CRÍTICO: {e}")
    telegram = None


@app.post("/webhook")
async def processar_webhook(request: Request):
    """Endpoint para processar cliques nos botões do Telegram (callback_query)."""
    if not telegram:
        raise HTTPException(
            status_code=500, detail="Provider não inicializado")

    dados = await request.json()
    print("\n--- ✅ WEBHOOK RECEBIDO ---")
    print(json.dumps(dados, indent=2))

    # Verifica se a notificação é um clique em botão (callback_query)
    if "callback_query" not in dados:
        return {"status": "ok", "message": "Não é um callback de botão, ignorando."}

    callback_data = dados["callback_query"]["data"]
    chat_id = dados["callback_query"]["message"]["chat"]["id"]

    # Extrai a ação e o ID da notificação do callback_data (formato: "acao:correlation_id")
    try:
        acao, correlation_id = callback_data.split(":", 1)
    except ValueError:
        return {"status": "error", "message": "Formato de callback_data inválido."}

    # Busca os dados da notificação original para ter o contexto
    notificacao = buscar_notificacao_por_correlation_id(correlation_id)
    if not notificacao:
        raise HTTPException(
            status_code=404, detail="Notificação original não encontrada.")

    # =========================================================================
    # # LÓGICA DE RESPOSTA (A PARTE QUE ESTAVA FALTANDO)
    # =========================================================================
    try:
        # Responde de acordo com a ação do usuário
        if acao == "show_details":
            lote = notificacao["found_lot"]
            mensagem = (
                f"🐴 *Detalhes do Lote: {lote['nome']}*\n\n"
                f"Leilão: *{lote['leilao']}*\n"
                f"Leiloeira: *{lote['leiloeira']}*\n"
                f"Nascimento: *{lote['data_nascimento']}*\n"
                f"Raça: *{lote['raca']}*\n"
                f"Sexo: *{lote['sexo']}*\n"
                f"Pai: *{lote['pai']}*\n"
                f"Mãe: *{lote['mae']}*"
            )
            botoes = [
                {"text": "➡️ Abrir no site da Equibid", "url": lote['url']}]
            telegram.send_message(
                chat_id=chat_id, text=mensagem, buttons=botoes)

        elif acao == "no_thanks":
            mensagem = "Entendido. Você gostaria de ajustar os critérios desta busca para receber notificações mais precisas no futuro?"
            botoes = [
                {"text": "🔧 Sim, revisar busca",
                    "url": "https://equibid.com.br/minhas-buscas"},
                {"text": "👍 Deixar para depois",
                    "callback_data": f"close_convo:{correlation_id}"}
            ]
            telegram.send_message(
                chat_id=chat_id, text=mensagem, buttons=botoes)

        elif acao == "close_convo":
            mensagem = "Tudo bem! Continuaremos de olho para você. 😉"
            telegram.send_message(chat_id=chat_id, text=mensagem)

    except RuntimeError as e:
        print(f"WEBHOOK: Erro ao enviar mensagem de resposta: {e}")

    return {"status": "success", "message": "Ação processada."}


if __name__ == "__main__":
    print("🚀 Iniciando servidor de Webhook com Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8010)
