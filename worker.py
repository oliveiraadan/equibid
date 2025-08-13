import json
from time import sleep
# Altere o import para o novo provider
from providers.telegram import TelegramProvider
from typing import List, Dict
import os

# Instancia o provider do Telegram
try:
    telegram_provider = TelegramProvider()
    # Pega o CHAT_ID do .env para onde as mensagens serão enviadas
    TARGET_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
except RuntimeError as e:
    print(f"ERRO CRÍTICO: {e}")
    telegram_provider = None
    TARGET_CHAT_ID = None


def enviar_notificacao_telegram(
    nome_usuario: str,
    nome_lote: str
):
    """
    Usa o TelegramProvider para enviar a notificação.
    """
    if not telegram_provider or not TARGET_CHAT_ID:
        print("Worker não pode enviar: Telegram Provider ou CHAT_ID não está disponível.")
        return

    print(
        f"\nWORKER: Buscando notificação para {nome_usuario} sobre o lote {nome_lote}")

    # Mensagem formatada para o Telegram (usando Markdown)
    mensagem = f"👋 Olá, *{nome_usuario}*!\n\nEncontramos um lote que pode te interessar:\n🐴 _{nome_lote}_\n\nDeseja receber mais detalhes?"

    # Botões para o Telegram (formato de 'inline_keyboard')
    botoes = [
        {"text": "Sim, por favor", "callback_data": "yes_details"},
        {"text": "Não, obrigado", "callback_data": "no_details"}
    ]

    try:
        print("WORKER: Enviando pergunta de confirmação via Telegram...")
        # A API do Telegram lida com botões de resposta e de link de forma diferente.
        # Para "Sim/Não", usamos 'callback_data'. O webhook lidaria com isso.
        # Para testes, podemos usar botões de link.
        botoes_de_link = [
            {"text": "Ver Lote (Exemplo)",
             "url": "https://equibid.com.br/lote/exemplo"},
            {"text": "Ver Buscas (Exemplo)",
             "url": "https://equibid.com.br/buscas/exemplo"}
        ]

        resultado = telegram_provider.send_message(
            chat_id=TARGET_CHAT_ID,
            text=mensagem,
            buttons=botoes_de_link
        )
        print("WORKER: Pergunta enviada. Resposta da API:",
              json.dumps(resultado, indent=2))
    except RuntimeError as e:
        print(f"WORKER: Falha ao enviar notificação: {e}")


def main():
    """Função principal do worker."""
    print("WORKER: Iniciado e pronto para processar notificações via TELEGRAM.")
    while True:
        print("WORKER: Simulando o envio de uma notificação pendente...")
        enviar_notificacao_telegram(
            nome_usuario="Daniel (via Telegram)",
            nome_lote="Lote 25 - Cavalo Campeão de Marcha"
        )

        print("WORKER: Ciclo finalizado. Aguardando 60 segundos.")
        sleep(60)


if __name__ == '__main__':
    main()
