import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Request, HTTPException
import uvicorn
import json
from dotenv import load_dotenv
from providers.telegram import TelegramProvider

# Carrega as variáveis de ambiente do .env
load_dotenv()

# --- Conexão com Banco de Dados ---
# (Em uma aplicação real, considere usar um pool de conexões)


def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except psycopg2.OperationalError as e:
        print(
            f"ERRO CRÍTICO: Webhook não pôde conectar ao banco de dados: {e}")
        return None


def buscar_dados_completos_por_correlation_id(correlation_id: str):
    """
    Busca os dados completos da notificação e do lote associado,
    usando o ID de correlação para enviar a mensagem de detalhes.
    """
    print(
        f"WEBHOOK: Buscando dados no DB para o correlation_id: {correlation_id}")
    conn = get_db_connection()
    if not conn:
        return None

    query = """
        select
            l.name as lot_nome,
            a.event_name as lot_leilao,
            h.name as lot_leiloeira,
            l.birth_date as lot_data_nascimento,
            l.coat as lot_pelagem,
            l.breed as lot_raca,
            l.gender as lot_sexo,
            l.sire as lot_pai,
            l.dam as lot_mae,
            l.website_url as lot_url
        from
            public.notifications_queue nq
            join public.lots l on nq.entity_id = l.id
            join public.auctions a on a.id = l.auction_id
            join public.auction_houses h on h.id = a.auction_house_id
        where
        nq.correlation_id =  %s;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (correlation_id,))
        data = cur.fetchone()
    conn.close()

    if not data:
        return None

    # Renomeia as chaves para corresponder ao formato esperado pela lógica de mensagem
    return {"found_lot": dict(data)}

# Adicione esta nova função em webhook.py


def registrar_resposta_do_usuario(correlation_id: str, acao: str):
    """
    Atualiza a tabela notifications_queue com a resposta do usuário.
    """
    print(
        f"WEBHOOK: Registrando ação '{acao}' para o correlation_id: {correlation_id}")
    conn = get_db_connection()
    if not conn:
        print("WEBHOOK: ERRO - Não foi possível conectar ao DB para registrar a resposta.")
        return

    query = """
        UPDATE public.notifications_queue
        SET
            responded = TRUE,
            response_value = %s,
            response_at = NOW()
        WHERE correlation_id = %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (acao, correlation_id))
        conn.commit()
        print("WEBHOOK: Resposta registrada com sucesso no banco de dados.")
    except (Exception, psycopg2.Error) as error:
        print(f"WEBHOOK: ERRO ao registrar resposta no DB: {error}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


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
            status_code=500, detail="Provider do Telegram não inicializado")

    dados = await request.json()
    print("\n--- ✅ WEBHOOK RECEBIDO ---")
    print(json.dumps(dados, indent=2))

    if "callback_query" not in dados:
        return {"status": "ok", "message": "Não é um callback de botão, ignorando."}

    callback_data = dados["callback_query"]["data"]
    chat_id = dados["callback_query"]["message"]["chat"]["id"]

    try:
        acao, correlation_id = callback_data.split(":", 1)
    except ValueError:
        return {"status": "error", "message": "Formato de callback_data inválido."}

    registrar_resposta_do_usuario(correlation_id=correlation_id, acao=acao)

    # Busca os dados completos DO LOTE usando o correlation_id
    notificacao = buscar_dados_completos_por_correlation_id(correlation_id)
    if not notificacao:
        # TODO: Adicionar lógica para lidar com notificação não encontrada.
        # Poderia ser uma mensagem de erro para o usuário.
        print(
            f"WEBHOOK: ERRO - Notificação com correlation_id {correlation_id} não encontrada.")
        raise HTTPException(
            status_code=404, detail="Notificação original não encontrada.")

    # LÓGICA DE RESPOSTA
    try:
        if acao == "show_details":
            lote = notificacao["found_lot"]
            # Formata a data de nascimento se ela existir
            data_nasc_formatada = lote['lot_data_nascimento'].strftime(
                '%d/%m/%Y') if lote.get('lot_data_nascimento') else 'N/A'

            mensagem = (
                f"🐴 *Detalhes do Lote: {lote['lot_nome']}*\n\n"
                f"Leilão: *{lote['lot_leilao']}*\n"
                f"Leiloeira: *{lote['lot_leiloeira']}*\n"
                f"Nascimento: *{data_nasc_formatada}*\n"
                f"Raça: *{lote['lot_raca']}*\n"
                f"Pelagem: *{lote['lot_pelagem']}*\n"
                f"Sexo: *{lote['lot_sexo']}*\n"
                f"Pai: *{lote['lot_pai']}*\n"
                f"Mãe: *{lote['lot_mae']}*"
            )
            botoes = [
                {"text": "➡️ Abrir pagina do lote", "url": lote['lot_url']}]
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
        # A exceção será capturada pelo FastAPI e retornará um erro 500.

    return {"status": "success", "message": "Ação processada."}


if __name__ == "__main__":
    print("🚀 Iniciando servidor de Webhook com Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8010)
