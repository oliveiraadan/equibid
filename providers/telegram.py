import os
import requests
from typing import Any, Dict, List, Optional

class TelegramProvider:
    """
    Provider para encapsular todas as interações com a API do Telegram Bot.
    """
    def __init__(self):
        """
        Inicializa o provider, carregando o token do ambiente.
        """
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise RuntimeError("Telegram não configurado. Verifique a variável de ambiente: TELEGRAM_BOT_TOKEN.")
        
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        print("✅ TelegramProvider inicializado com sucesso.")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Método auxiliar para realizar as requisições HTTP."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            raise RuntimeError(f"Telegram API Error: {err.response.status_code} - {err.response.text}")
        except requests.exceptions.RequestException as err:
            raise RuntimeError(f"Telegram Request Error: {err}")

    def send_message(self, chat_id: str, text: str, buttons: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Envia uma mensagem de texto com botões de link (inline keyboard).

        Args:
            chat_id (str): ID do chat de destino.
            text (str): Conteúdo da mensagem. Suporta Markdown.
            buttons (Optional[List[Dict]]): Lista de botões. 
                                            Ex: [{"text": "Google", "url": "https://google.com"}]
        """
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown" # Permite usar negrito, itálico, etc.
        }

        if buttons:
            # A API do Telegram espera um array de arrays para o teclado
            inline_keyboard = [[btn for btn in buttons]]
            payload["reply_markup"] = json.dumps({"inline_keyboard": inline_keyboard})

        return self._make_request("POST", "sendMessage", json=payload)