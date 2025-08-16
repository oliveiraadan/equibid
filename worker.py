import os
import psycopg2
import psycopg2.extras
from time import sleep
from dotenv import load_dotenv
from providers.telegram import TelegramProvider
from providers.z_api import ZApiProvider

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração dos Providers ---
PROVIDERS = {}
try:
    PROVIDERS['telegram'] = TelegramProvider()
except RuntimeError as e:
    print(f"AVISO: {e}")

try:
    PROVIDERS['whatsapp'] = ZApiProvider()
except RuntimeError as e:
    print(f"AVISO: {e}")

# --- Funções de Banco de Dados ---


def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    try:

        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except psycopg2.OperationalError as e:
        print(
            f"ERRO CRÍTICO: Não foi possível conectar ao banco de dados: {e}")
        return None


def buscar_notificacao_pendente_do_db(conn):
    """
    Busca a próxima notificação pendente, juntando apenas as informações
    necessárias para a pergunta inicial (usuário e busca salva).
    """
    print("\nWORKER: Buscando notificações pendentes no banco de dados...")
    query = """
        select
            nq.id as notification_id,
            nq.correlation_id,
            --nq.channel channel,
            'telegram' channel,
            up.first_name as user_name,
            --up.phone_number as user_phone,
            '5511996347828' as user_phone,
            ss.filters as saved_search_detail
            --select *
        from
        public.notifications_queue nq
            join public.user_profiles up on nq.user_id = up.user_id
            join public.saved_searches ss on nq.saved_search_id = ss.id
            where
            nq.status = 'pending'
            and nq.channel = 'whatsapp'
            order by
            nq.created_at
            limit
            1
        FOR UPDATE SKIP LOCKED;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query)
        return cur.fetchone()


def marcar_notificacao_como_enviada(conn, notification_id, provider_message_id):
    """Atualiza o status de uma notificação para 'sent' e armazena o ID da mensagem."""
    query = """
        UPDATE notifications_queue
        SET
            status = 'sent',
            sent_at = NOW()
        WHERE id = %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (provider_message_id, notification_id))
    print(f"WORKER: Notificação {notification_id} marcada como 'sent'.")


# --- Lógica do Worker ---

def enviar_pergunta_inicial(notificacao):
    """Envia a primeira mensagem do fluxo usando o provedor correto."""
    channel = notificacao.get("channel")
    provider = PROVIDERS.get(channel)

    if not provider:
        print(
            f"WORKER: Nenhum provider configurado para o canal '{channel}'. Pulando.")
        return None

    mensagem = (
        f"Olá, *{notificacao['user_name']}*! 👋\n\n"
        f"Encontramos um resultado para sua busca salva: *'{notificacao['saved_search_detail']}'*.\n\n"
        "Deseja ver os detalhes do lote encontrado?"
    )
    correlation_id = str(notificacao['correlation_id'])

    try:
        if channel == 'telegram':
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            print(
                f"WORKER: Enviando pergunta (Telegram) para o chat ID {chat_id}...")
            botoes = [
                {"text": "✅ Sim, ver detalhes",
                    "callback_data": f"show_details:{correlation_id}"},
                {"text": "❌ Não, obrigado",
                    "callback_data": f"no_thanks:{correlation_id}"}
            ]
            resultado = provider.send_message(
                chat_id=chat_id, text=mensagem, buttons=botoes)
            return resultado.get('result', {}).get('message_id')

        elif channel == 'whatsapp':
            phone = notificacao['user_phone']
            print(
                f"WORKER: Enviando pergunta (WhatsApp) para o número {phone}...")
            botoes = [
                {"id": f"show_details:{correlation_id}",
                    "label": "✅ Sim, ver detalhes"},
                {"id": f"no_thanks:{correlation_id}", "label": "❌ Não, obrigado"}
            ]
            payload = {"message": mensagem, "buttons": botoes}
            resultado = provider.send_button_list(
                phone=phone, button_payload=payload)
            return resultado.get('message_id')

    except RuntimeError as e:
        print(f"WORKER: Falha ao enviar notificação: {e}")
        return None


def main():
    """Função principal do worker."""
    print("WORKER: Iniciado e pronto para processar notificações.")
    if not PROVIDERS:
        print("ERRO CRÍTICO: Nenhum provider de notificação foi inicializado. Encerrando.")
        return

    while True:
        conn = get_db_connection()
        if not conn:
            sleep(60)
            continue

        try:
            notification = buscar_notificacao_pendente_do_db(conn)

            if notification:
                provider_message_id = enviar_pergunta_inicial(notification)
                if provider_message_id:
                    marcar_notificacao_como_enviada(
                        conn, notification['notification_id'], provider_message_id)
                else:
                    print(
                        "WORKER: Falha no envio, a notificação não será marcada como enviada.")
                conn.commit()
            else:
                print("WORKER: Nenhuma notificação pendente encontrada.")

        except (Exception, psycopg2.Error) as error:
            print(f"WORKER: Ocorreu um erro de banco de dados: {error}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        print("WORKER: Ciclo finalizado. Aguardando 30 segundos.")
        sleep(30)


if __name__ == '__main__':
    main()
