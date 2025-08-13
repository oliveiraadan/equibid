import json
from time import sleep
from dotenv import load_dotenv
from providers.telegram import TelegramProvider
import os

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Simulação de Banco de Dados ---
# Em um cenário real, esta função faria uma query no seu banco de dados.


def buscar_notificacao_pendente_do_db():
    """Simula a busca por uma notificação pendente no banco de dados."""
    print("\nWORKER: Buscando notificações pendentes no banco de dados...")
    # Retorna um dicionário com os dados necessários para a notificação
    return {
        "correlation_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "user_name": "Daniel",
        "user_telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
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


# --- Lógica do Worker ---
try:
    telegram = TelegramProvider()
except RuntimeError as e:
    print(f"ERRO CRÍTICO: {e}")
    telegram = None


def enviar_pergunta_inicial(notificacao):
    """Envia a primeira mensagem do fluxo: a pergunta de interesse."""
    if not telegram:
        print("Worker não pode enviar: Provider não está disponível.")
        return

    # Mensagem informando sobre o match e perguntando o interesse
    mensagem = (
        f"Olá, *{notificacao['user_name']}*! 👋\n\n"
        f"Encontramos um resultado para sua busca salva: *'{notificacao['saved_search_details']}'*.\n\n"
        "Deseja ver os detalhes do lote encontrado?"
    )

    # Botões de Sim/Não. O `callback_data` é crucial para o webhook saber o que fazer.
    botoes = [
        {"text": "✅ Sim, ver detalhes",
            "callback_data": f"show_details:{notificacao['correlation_id']}"},
        {"text": "❌ Não, obrigado",
            "callback_data": f"no_thanks:{notificacao['correlation_id']}"}
    ]

    try:
        print(
            f"WORKER: Enviando pergunta inicial para o chat ID {notificacao['user_telegram_chat_id']}...")
        resultado = telegram.send_message(
            chat_id=notificacao['user_telegram_chat_id'],
            text=mensagem,
            buttons=botoes
        )
        # TODO: Salvar o `message_id` retornado pela API no banco de dados,
        # junto com o `correlation_id`, para ter um rastreamento completo.
        print("WORKER: Pergunta inicial enviada com sucesso.")
    except RuntimeError as e:
        print(f"WORKER: Falha ao enviar notificação: {e}")


def main():
    """Função principal do worker."""
    print("WORKER: Iniciado e pronto para processar notificações.")
    while True:
        notificacao = buscar_notificacao_pendente_do_db()
        if notificacao:
            enviar_pergunta_inicial(notificacao)
            # TODO: Marcar a notificação como 'sent' no banco para não ser enviada de novo.
        else:
            print("WORKER: Nenhuma notificação pendente encontrada.")

        print("WORKER: Ciclo finalizado. Aguardando 60 segundos.")
        sleep(60)


if __name__ == '__main__':
    main()
