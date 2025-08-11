import os
import requests
from typing import Any, Dict, List, Optional


class ZApiProvider:
    """
    Provider para encapsular todas as interações com a Z-API.
    """

    def __init__(self):
        """
        Inicializa o provider, carregando as credenciais do ambiente.
        Levanta um erro se as configurações essenciais não estiverem presentes.
        """
        self.base_url = "https://api.z-api.io"
        self.instance_id = os.getenv('INSTANCE_ID')
        self.instance_token = os.getenv('INSTANCE_TOKEN')
        self.client_token = os.getenv('CLIENT_TOKEN')

        if not all([self.instance_id, self.instance_token, self.client_token]):
            raise RuntimeError(
                "Z-API não configurada. Verifique as variáveis de ambiente: INSTANCE_ID, INSTANCE_TOKEN, CLIENT_TOKEN.")

        self.headers = {
            "Content-Type": "application/json",
            "Client-Token": self.client_token
        }
        print("✅ ZApiProvider inicializado com sucesso.")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Método auxiliar para realizar as requisições HTTP e tratar a resposta.

        Args:
            method (str): Método HTTP (e.g., 'POST', 'GET').
            endpoint (str): Endpoint da API (e.g., 'send-text').
            **kwargs: Argumentos adicionais para a requisição (e.g., json, params).

        Returns:
            Dict[str, Any]: A resposta da API em formato JSON.

        Raises:
            RuntimeError: Se a chamada da API falhar (status code >= 300).
        """
        url = f"{self.base_url}/instances/{self.instance_id}/token/{self.instance_token}/{endpoint}"

        try:
            response = requests.request(
                method, url, headers=self.headers, timeout=30, **kwargs)
            # Levanta um erro para respostas com status de erro (4xx ou 5xx)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            raise RuntimeError(
                f"Z-API Error: {err.response.status_code} - {err.response.text}")
        except requests.exceptions.RequestException as err:
            raise RuntimeError(f"Z-API Request Error: {err}")

    def _format_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Formata a resposta da Z-API para o nosso padrão interno."""
        # A Z-API retorna um 'zaapId' para mensagens enviadas com sucesso.
        message_id = api_response.get("zaapId")
        return {
            "ok": True,
            "message_id": message_id,
            "status": "queued",  # A Z-API enfileira as mensagens
            "raw": api_response
        }

    def send_text(self, phone: str, message: str) -> Dict[str, Any]:
        """Envia uma mensagem de texto simples."""
        payload = {"phone": phone, "message": message}
        api_response = self._make_request("POST", "send-text", json=payload)
        return self._format_response(api_response)

    def send_image(self, phone: str, image_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Envia uma imagem com uma legenda opcional."""
        payload = {"phone": phone, "image": image_url,
                   "caption": caption or ""}
        api_response = self._make_request("POST", "send-image", json=payload)
        return self._format_response(api_response)

    def send_button_actions(
        self,
        phone: str,
        message: str,
        actions: List[Dict[str, Any]],
        title: Optional[str] = None,
        footer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia uma mensagem com botões de ação (URL ou Chamada).
        Perfeito para o caso de uso da Equibid.

        Args:
            actions (List[Dict]): Uma lista de dicionários, cada um representando um botão.
                                 Ex: [{"id": "1", "type": "URL", "label": "Ver", "url": "..."}]
        """
        payload = {
            "phone": phone,
            "message": message,
            "title": title,
            "footer": footer,
            "buttonActions": actions
        }
        api_response = self._make_request(
            "POST", "send-button-actions", json=payload)
        return self._format_response(api_response)

    def get_instance_status(self) -> Dict[str, Any]:
        """Verifica o status da conexão da instância."""
        # Este endpoint retorna diretamente os dados de status
        return self._make_request("GET", "status")

    def check_phone_exists(self, phone: str) -> Dict[str, Any]:
        """Verifica se um número de telefone possui uma conta no WhatsApp."""
        return self._make_request("GET", f"phone-exists/{phone}")
