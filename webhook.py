import os, re, uvicorn, json, asyncio
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import uvicorn
import json
from dotenv import load_dotenv
from providers.telegram import TelegramProvider
from providers.evolution_api import EvolutionAPIProvider
from fastapi.responses import JSONResponse
import logging

# Carrega as variáveis de ambiente do .env
load_dotenv()

YOUTUBE_CHAT_ID = os.getenv("YOUTUBE_CHAT_ID")
if YOUTUBE_CHAT_ID:
    YOUTUBE_CHAT_ID = int(YOUTUBE_CHAT_ID) # O ID vem como string, convertemos para inteiro
    print(f"Funcionalidade de download de vídeos restrita ao chat ID: {YOUTUBE_CHAT_ID}")
else:
    print("AVISO: YOUTUBE_CHAT_ID não definido no .env. A funcionalidade de download está desativada.")

async def run_download_and_notify(chat_id: int, url: str):
    """
    Esta função roda em segundo plano para não bloquear o webhook.
    """
    print(f"BACKGROUND: Iniciando processo de download para o chat {chat_id}")
    
    await telegram.send_message(chat_id=chat_id, text="🔍 Verificando o status do vídeo...")
    
    status = await asyncio.to_thread(downloader.get_stream_status, url)
    
    if status in ["LIVE", "FINISHED", "NOT_A_LIVE_STREAM"]:
        mensagem_status = {
            "LIVE": "🔴 Status: Live em andamento. Iniciando gravação...",
            "FINISHED": "✅ Status: Live finalizada. Iniciando download...",
            "NOT_A_LIVE_STREAM": "📹 Status: Vídeo comum. Iniciando download..."
        }[status]
        
        await telegram.send_message(chat_id=chat_id, text=mensagem_status)
        download_function = downloader.record_live_stream if status == "LIVE" else downloader.download_finished_stream
        final_filepath = await asyncio.to_thread(download_function, url)

        if final_filepath:
            filename = os.path.basename(final_filepath)
            await telegram.send_message(
                chat_id=chat_id,
                text=f"✅ Download concluído com sucesso!\n\nSalvo como: `{filename}`"
            )
        else:
            await telegram.send_message(
                chat_id=chat_id,
                text="❌ Ocorreu um erro durante o download. Verifique os logs do servidor."
            )
    else:
        await telegram.send_message(
            chat_id=chat_id,
            text="❌ Não foi possível verificar o status do link. A URL pode ser inválida."
        )

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


app = FastAPI(title="EquiBid Webhook")

try:
    telegram = TelegramProvider()
except RuntimeError as e:
    print(f"ERRO CRÍTICO - Telegram: {e}")
    telegram = None

try:
    whatsapp = EvolutionAPIProvider()
except RuntimeError as e:
    print(f"ERRO CRÍTICO - WhatsApp: {e}")
    whatsapp = None


@app.post("/webhook-telegram")
async def processar_webhook(request: Request, background_tasks: BackgroundTasks):
    """Endpoint para processar cliques nos botões do Telegram (callback_query)."""
    if not telegram:
        raise HTTPException(
            status_code=500, detail="Provider do Telegram não inicializado")

    dados = await request.json()
    print("\n--- ✅ WEBHOOK RECEBIDO ---")
    print(json.dumps(dados, indent=2))


    if "message" in dados and "text" in dados["message"]:
        message = dados["message"]
        chat_id = message["chat"]["id"]
        
        # <<< PONTO CRÍTICO DE SEGURANÇA >>>
        # Verifica se a mensagem veio do chat permitido E se a funcionalidade está ativa.
        if YOUTUBE_CHAT_ID and chat_id == YOUTUBE_CHAT_ID:
            text = message["text"]
            youtube_regex = r"(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
            match = re.search(youtube_regex, text)

            if match:
                url_encontrada = match.group(0)
                await telegram.send_message(
                    chat_id=chat_id, 
                    text="✅ Link do YouTube recebido! Processando em segundo plano. 🚀"
                )
                background_tasks.add_task(run_download_and_notify, chat_id, url_encontrada)
            
        return {"status": "ok", "message": "Mensagem recebida e processada."}
        
    # --- LÓGICA PARA CALLBACKS DE BOTÕES (EXISTENTE) ---
    elif "callback_query" in dados:


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


def process_payload(payload):
    # Exemplo de processamento: apenas logar o payload
    print(f"Processando payload")
    # Aqui você pode adicionar lógica para salvar em banco, chamar outro serviço, etc.
    if isinstance(payload, str):
        payload = json.loads(payload)

    data = (payload.get("data") or {})
    key = (data.get("key") or {})

    remote_jid = key.get("remoteJid")
    participant = key.get("participant")
    from_me = bool(key.get("fromMe", False))
    push_name = data.get("pushName")

    is_group = isinstance(remote_jid, str) and remote_jid.endswith("@g.us")

    # Determina o remetente (JID)
    if is_group and participant:
        sender_id = participant
    elif not from_me and isinstance(remote_jid, str):
        sender_id = remote_jid
    else:
        sender_id = payload.get(
            "sender") or participant or remote_jid or "desconhecido"

    sender_name = push_name or sender_id

    # Extrai o texto (considera diversos tipos de mensagem)
    msg = (data.get("message") or {})
    m = msg
    # Desembrulha wrappers comuns
    while True:
        if isinstance(m.get("ephemeralMessage"), dict) and m["ephemeralMessage"].get("message"):
            m = m["ephemeralMessage"]["message"]
            continue
        if isinstance(m.get("viewOnceMessage"), dict) and m["viewOnceMessage"].get("message"):
            m = m["viewOnceMessage"]["message"]
            continue
        if isinstance(m.get("message"), dict):
            m = m["message"]
            continue
        break

    text = None
    if isinstance(m.get("conversation"), str):
        text = m["conversation"]
    elif isinstance(m.get("extendedTextMessage"), dict):
        text = m["extendedTextMessage"].get(
            "text") or m["extendedTextMessage"].get("caption")
    elif isinstance(m.get("imageMessage"), dict):
        text = m["imageMessage"].get("caption")
    elif isinstance(m.get("videoMessage"), dict):
        text = m["videoMessage"].get("caption")
    elif isinstance(m.get("documentMessage"), dict):
        text = m["documentMessage"].get(
            "caption") or m["documentMessage"].get("fileName")
    elif isinstance(m.get("buttonsResponseMessage"), dict):
        br = m["buttonsResponseMessage"]
        text = br.get("selectedDisplayText") or br.get("selectedButtonId")
    elif isinstance(m.get("listResponseMessage"), dict):
        lr = m["listResponseMessage"]
        ssr = lr.get("singleSelectReply") or {}
        text = ssr.get("selectedRowId") or lr.get("title")

    if not text:
        for k in ("text", "caption", "contentText", "body"):
            v = m.get(k)
            if isinstance(v, str) and v.strip():
                text = v
                break

    text = text or ""

    whatsapp.send_text('119963478280', f"{sender_name} — {sender_id}: {text}")

    # Formato final em uma única string
    return True


@app.post("/webhook-evolution")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logging.info(f"📩 Payload recebido: {payload}")

        print("\n--- ✅ WEBHOOK RECEBIDO ---")
        print(json.dumps(payload, indent=2))

        # Aqui você adiciona a lógica de processamento
        # Exemplo: salvar em banco, chamar outro serviço, etc.
        process_payload(payload)

        return JSONResponse(content={"status": "success", "message": "Webhook recebido"}, status_code=200)

    except Exception as e:
        logging.error(f"❌ Erro ao processar webhook: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)


if __name__ == "__main__":
    print("🚀 Iniciando servidor de Webhook com Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8010)
