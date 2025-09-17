import os
import json
import requests
from typing import Any, Dict, List, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class EvolutionAPIError(Exception):
    """Erro de alto nível ao chamar a Evolution API."""
    pass


class EvolutionAPIProvider:
    """
    Cliente minimalista e robusto para Evolution API.

    Variáveis de ambiente suportadas:
      - EVOLUTION_SERVER_URL (ex.: https://api.seudominio.com)
      - EVOLUTION_INSTANCE   (ex.: instance001)
      - EVOLUTION_API_KEY    (chave da API)

    Parâmetros do construtor sobrescrevem o que estiver no ambiente.
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        instance: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        verify_ssl: bool = True,
    ) -> None:
        self.server_url = (server_url or os.getenv(
            "EVOLUTION_SERVER_URL") or "").strip().rstrip('/')
        self.instance = (instance or os.getenv(
            "EVOLUTION_INSTANCE") or "").strip()
        self.api_key = (api_key or os.getenv(
            "EVOLUTION_API_KEY") or "").strip()
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        missing = [name for name, val in [
            ("EVOLUTION_SERVER_URL/server_url", self.server_url),
            ("EVOLUTION_INSTANCE/instance", self.instance),
            ("EVOLUTION_API_KEY/api_key", self.api_key),
        ] if not val]
        if missing:
            raise RuntimeError(
                "Configuração Evolution API ausente: " + ", ".join(missing)
            )

        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=frozenset(
                ["GET", "POST", "PUT", "DELETE", "PATCH"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self._base_headers = {
            "apikey": self.api_key,
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        data_payload: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Método central para realizar requisições à API.
        """
        url = f"{self.server_url}/{endpoint}/{self.instance}"
        headers = self._base_headers.copy()

        if json_payload:
            headers["Content-Type"] = "application/json"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=json_payload,
                data=data_payload,
                files=files,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

            if method.upper() in ['DELETE', 'POST'] and response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"status": "success", "message": f"{method.capitalize()} operation successful."}

            if not 200 <= response.status_code < 300:
                try:
                    error_data = response.json()
                except json.JSONDecodeError:
                    error_data = response.text
                raise EvolutionAPIError(
                    f"Erro na API ({response.status_code}) em '{endpoint}': {error_data}"
                )

            return response.json()

        except requests.exceptions.RequestException as e:
            raise EvolutionAPIError(f"Erro de conexão com a API: {e}") from e

    # --- Métodos de Envio de Mensagem ---

    def send_text(self, number: str, text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Envia uma mensagem de texto."""
        # Exemplo(s) de uso:
        #
        # 1. Envio simples
        # api_client.send_text("5511999998888", "Olá, tudo bem?")
        #
        # 2. Respondendo a uma mensagem específica
        # options = {
        #     "quoted": { "key": { "id": "ID_DA_MENSAGEM_ORIGINAL" } }
        # }
        # api_client.send_text("5511999998888", "Esta é uma resposta.", options=options)
        payload = {"number": number, "text": text}
        if options:
            payload.update(options)
        return self._request("POST", "message/sendText", json_payload=payload)

    def send_media_url(
        self,
        number: str,
        mediatype: str,
        media_url: str,
        caption: Optional[str] = None,
        mimetype: Optional[str] = None,
        file_name: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Envia uma mídia a partir de uma URL."""
        # Exemplo(s) de uso:
        #
        # 1. Enviar uma imagem simples
        # api_client.send_media_url(
        #     number="5511999998888",
        #     mediatype="image",
        #     media_url="https://s3.amazonaws.com/atendai/image.jpeg",
        #     caption="Olha esta imagem!"
        # )
        #
        # 2. Enviar um documento PDF com nome de arquivo customizado
        # api_client.send_media_url(
        #     number="5511999998888",
        #     mediatype="document",
        #     media_url="https://s3.amazonaws.com/atendai/documento.pdf",
        #     file_name="Relatorio.pdf",
        #     mimetype="application/pdf"
        # )
        payload = {
            "number": number,
            "mediatype": mediatype,
            "media": media_url,
        }
        if caption:
            payload["caption"] = caption
        if mimetype:
            payload["mimetype"] = mimetype
        if file_name:
            payload["fileName"] = file_name
        if options:
            payload.update(options)
        return self._request("POST", "message/sendMedia", json_payload=payload)

    def send_media_file(self, number: str, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Envia uma mídia a partir de um arquivo local."""
        # Exemplo(s) de uso:
        #
        # 1. Enviar um vídeo local
        # options = { "mediatype": "video", "caption": "Vídeo gravado hoje!" }
        # api_client.send_media_file("5511999998888", "/caminho/para/meu_video.mp4", options=options)
        data = {"number": number}
        if options:
            data.update(options)
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            return self._request("POST", "message/sendMedia", data_payload=data, files=files)

    def send_buttons(
        self,
        number: str,
        title: str,
        description: str,
        buttons: List[Dict[str, Any]],
        footer: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Envia uma mensagem com botões."""
        # Exemplo(s) de uso:
        #
        # 1. Botão simples
        # botoes = [{"type": "reply", "displayText": "Opção 1", "id": "opt1"}]
        # api_client.send_buttons(
        #     number="5511999998888",
        #     title="Escolha uma opção",
        #     description="Clique no botão abaixo",
        #     buttons=botoes
        # )
        #
        # 2. Botão com rodapé
        # botoes = [
        #   {"type": "url", "displayText": "Nosso Site", "url": "https://evolution-api.com"},
        #   {"type": "call", "displayText": "Ligue para nós", "phoneNumber": "5511999998888"}
        # ]
        # api_client.send_buttons(
        #     number="5511999998888",
        #     title="Entre em contato",
        #     description="Use uma das opções",
        #     buttons=botoes,
        #     footer="Atendimento 24h"
        # )
        payload = {
            "number": number,
            "title": title,
            "description": description,
            "buttons": buttons,
        }
        if footer:
            payload["footer"] = footer
        if options:
            payload.update(options)
        return self._request("POST", "message/sendButtons", json_payload=payload)

    # --- Métodos de Chamada ---

    def send_fake_call(self, number: str, is_video: bool = False, duration_seconds: int = 3) -> Dict[str, Any]:
        """Inicia uma chamada 'fake' para o número especificado."""
        # Exemplo(s) de uso:
        #
        # 1. Chamada de áudio fake
        # api_client.send_fake_call("5511999998888")
        #
        # 2. Chamada de vídeo fake com duração de 10 segundos
        # api_client.send_fake_call("5511999998888", is_video=True, duration_seconds=10)
        payload = {
            "number": number,
            "isVideo": is_video,
            "callDuration": duration_seconds,
        }
        return self._request("POST", "call/offer", json_payload=payload)

    # --- Métodos de Gerenciamento de Chat ---

    def check_whatsapp_numbers(self, numbers: List[str]) -> Dict[str, Any]:
        """Verifica se uma lista de números possui WhatsApp."""
        # Exemplo de uso:
        #
        # lista_telefones = ["5511999998888", "5521988887777", "1122334455"]
        # resultado = api_client.check_whatsapp_numbers(lista_telefones)
        payload = {"numbers": numbers}
        return self._request("POST", "chat/whatsappNumbers", json_payload=payload)

    def mark_messages_as_read(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Marca uma ou mais mensagens como lidas."""
        # Exemplo de uso:
        #
        # mensagens_para_ler = [
        #     {
        #         "remoteJid": "5511999998888@s.whatsapp.net",
        #         "fromMe": False,
        #         "id": "ID_DA_MENSAGEM_1"
        #     }
        # ]
        # api_client.mark_messages_as_read(mensagens_para_ler)
        payload = {"readMessages": messages}
        return self._request("POST", "chat/markMessageAsRead", json_payload=payload)

    def archive_chat(self, chat_jid: str, archive: bool, last_message_key: Dict[str, Any]) -> Dict[str, Any]:
        """Arquiva ou desarquiva um chat."""
        # Exemplo(s) de uso:
        #
        # chave_msg = {"remoteJid": "5511999998888@s.whatsapp.net", "id": "ULTIMA_MSG_ID"}
        #
        # 1. Arquivar o chat
        # api_client.archive_chat("5511999998888@s.whatsapp.net", archive=True, last_message_key=chave_msg)
        #
        # 2. Desarquivar o chat
        # api_client.archive_chat("5511999998888@s.whatsapp.net", archive=False, last_message_key=chave_msg)
        payload = {
            "lastMessage": {"key": last_message_key},
            "chat": chat_jid,
            "archive": archive
        }
        return self._request("POST", "chat/archiveChat", json_payload=payload)

    def delete_message(self, remote_jid: str, message_id: str, from_me: bool, participant: Optional[str] = None) -> Dict[str, Any]:
        """Deleta uma mensagem para todos."""
        # Exemplo(s) de uso:
        #
        # 1. Deletar uma mensagem que eu enviei em um chat privado
        # api_client.delete_message(
        #     remote_jid="5511999998888@s.whatsapp.net",
        #     message_id="ID_DA_MINHA_MENSAGEM",
        #     from_me=True
        # )
        #
        # 2. Deletar uma mensagem que eu enviei em um grupo
        # api_client.delete_message(
        #     remote_jid="ID_DO_GRUPO@g.us",
        #     message_id="ID_DA_MINHA_MENSAGEM",
        #     from_me=True,
        #     participant="MEU_NUMERO@s.whatsapp.net"
        # )
        payload = {
            "id": message_id,
            "remoteJid": remote_jid,
            "fromMe": from_me,
        }
        if participant:
            payload["participant"] = participant
        return self._request("DELETE", "chat/deleteMessageForEveryone", json_payload=payload)

    def update_message(self, number: str, message_key: Dict[str, Any], new_text: str) -> Dict[str, Any]:
        """Edita o texto de uma mensagem já enviada."""
        # Exemplo de uso:
        #
        # chave_da_mensagem = {
        #     "remoteJid": "5511999998888@s.whatsapp.net",
        #     "fromMe": True,
        #     "id": "ID_DA_MENSAGEM_A_SER_EDITADA"
        # }
        # api_client.update_message(
        #     number="5511999998888",
        #     message_key=chave_da_mensagem,
        #     new_text="Este é o novo texto da mensagem."
        # )
        payload = {
            "number": number,
            "key": message_key,
            "text": new_text
        }
        return self._request("POST", "chat/updateMessage", json_payload=payload)

    def send_presence(self, number: str, presence: str, delay: int = 1200) -> Dict[str, Any]:
        """Envia um status de presença (digitando, gravando, online)."""
        # Exemplo(s) de uso:
        #
        # 1. Mostrar "digitando..."
        # api_client.send_presence("5511999998888", "composing")
        #
        # 2. Mostrar "gravando áudio..." por 5 segundos
        # api_client.send_presence("5511999998888", "recording", delay=5000)
        payload = {"number": number, "delay": delay, "presence": presence}
        return self._request("POST", "chat/sendPresence", json_payload=payload)

    def update_block_status(self, number: str, status: str) -> Dict[str, Any]:
        """Bloqueia ou desbloqueia um contato. 'status' deve ser 'block' ou 'unblock'."""
        # Exemplo(s) de uso:
        #
        # 1. Bloquear um número
        # api_client.update_block_status("5511987654321", "block")
        #
        # 2. Desbloquear um número
        # api_client.update_block_status("5511987654321", "unblock")
        payload = {"number": number, "status": status}
        return self._request("POST", "message/updateBlockStatus", json_payload=payload)

    # --- Métodos de Busca ---

    def find_contacts(self, where_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Busca contatos. Se 'where_filter' for omitido, lista todos."""
        # Exemplo(s) de uso:
        #
        # 1. Listar todos os contatos
        # todos_contatos = api_client.find_contacts()
        #
        # 2. Encontrar um contato específico pelo ID (JID)
        # filtro = {"id": "5511999998888@s.whatsapp.net"}
        # contato_especifico = api_client.find_contacts(where_filter=filtro)
        payload = {"where": where_filter or {}}
        return self._request("POST", "chat/findContacts", json_payload=payload)

    def find_chats(self, where_filter: Optional[Dict[str, Any]] = None, page: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """Busca chats. Se 'where_filter' for omitido, lista todos."""
        # Exemplo(s) de uso:
        #
        # 1. Listar todos os chats
        # todos_chats = api_client.find_chats()
        #
        # 2. Listar os 20 primeiros chats da segunda página
        # chats_paginados = api_client.find_chats(page=2, offset=20)
        payload = {"where": where_filter or {}}
        if page:
            payload["page"] = page
        if offset:
            payload["offset"] = offset
        return self._request("POST", "chat/findChats", json_payload=payload)

    def find_messages(self, where_filter: Dict[str, Any], page: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """Busca mensagens com base em um filtro."""
        # Exemplo(s) de uso:
        #
        # 1. Buscar todas as mensagens de um chat específico
        # filtro = {"key": {"remoteJid": "5511999998888@s.whatsapp.net"}}
        # mensagens_chat = api_client.find_messages(where_filter=filtro)
        #
        # 2. Buscar as 50 mensagens mais recentes do chat
        # mensagens_chat = api_client.find_messages(where_filter=filtro, offset=50)
        payload = {"where": where_filter}
        if page:
            payload["page"] = page
        if offset:
            payload["offset"] = offset
        return self._request("POST", "chat/findMessages", json_payload=payload)

    # --- Métodos de Gerenciamento de Grupos ---

    def create_group(self, subject: str, participants: List[str], description: Optional[str] = None) -> Dict[str, Any]:
        """Cria um novo grupo."""
        # Exemplo(s) de uso:
        #
        # 1. Criar grupo com descrição
        # participantes = ["5511999998888", "5521988887777"]
        # api_client.create_group("Grupo de Teste", participantes, "Descrição do nosso grupo.")
        #
        # 2. Criar grupo sem descrição
        # api_client.create_group("Grupo Rápido", ["5531977776666"])
        payload = {"subject": subject, "participants": participants}
        if description:
            payload["description"] = description
        return self._request("POST", "group/create", json_payload=payload)

    def update_group_picture(self, group_jid: str, image_url: str) -> Dict[str, Any]:
        """Atualiza a foto de um grupo a partir de uma URL."""
        # Exemplo de uso:
        #
        # group_id = "1234567890@g.us"
        # url_da_foto = "https://example.com/nova_foto.png"
        # api_client.update_group_picture(group_id, url_da_foto)
        params = {"groupJid": group_jid}
        payload = {"image": image_url}
        return self._request("POST", "group/updateGroupPicture", params=params, json_payload=payload)

    def update_group_subject(self, group_jid: str, subject: str) -> Dict[str, Any]:
        """Atualiza o nome (assunto) de um grupo."""
        # Exemplo de uso:
        #
        # group_id = "1234567890@g.us"
        # api_client.update_group_subject(group_id, "Novo Nome do Grupo")
        params = {"groupJid": group_jid}
        payload = {"subject": subject}
        return self._request("POST", "group/updateGroupSubject", params=params, json_payload=payload)

    def update_group_description(self, group_jid: str, description: str) -> Dict[str, Any]:
        """Atualiza a descrição de um grupo."""
        # Exemplo de uso:
        #
        # group_id = "1234567890@g.us"
        # api_client.update_group_description(group_id, "Regras atualizadas do grupo.")
        params = {"groupJid": group_jid}
        payload = {"description": description}
        return self._request("POST", "group/updateGroupDescription", params=params, json_payload=payload)

    def fetch_invite_code(self, group_jid: str) -> Dict[str, Any]:
        """Obtém o código de convite de um grupo."""
        # Exemplo de uso:
        #
        # group_id = "1234567890@g.us"
        # invite_info = api_client.fetch_invite_code(group_id)
        # print(invite_info.get("inviteCode"))
        params = {"groupJid": group_jid}
        return self._request("GET", "group/inviteCode", params=params)

    def revoke_invite_code(self, group_jid: str) -> Dict[str, Any]:
        """Revoga (reseta) o código de convite de um grupo."""
        # Exemplo de uso:
        #
        # group_id = "1234567890@g.us"
        # api_client.revoke_invite_code(group_id)
        params = {"groupJid": group_jid}
        return self._request("POST", "group/revokeInviteCode", params=params)

    def fetch_all_groups(self, get_participants: bool = False) -> Dict[str, Any]:
        """Busca todos os grupos da instância."""
        # Exemplo(s) de uso:
        #
        # 1. Listar grupos sem os participantes (mais rápido)
        # lista_grupos = api_client.fetch_all_groups()
        #
        # 2. Listar grupos incluindo a lista de participantes de cada um
        # lista_completa = api_client.fetch_all_groups(get_participants=True)
        params = {"getParticipants": str(get_participants).lower()}
        return self._request("GET", "group/fetchAllGroups", params=params)

    def update_group_participants(self, group_jid: str, action: str, participants: List[str]) -> Dict[str, Any]:
        """Adiciona, remove, promove ou rebaixa participantes de um grupo."""
        # Exemplo(s) de uso:
        #
        # group_id = "1234567890@g.us"
        # membros = ["5511999998888", "5521988887777"]
        #
        # 1. Adicionar membros
        # api_client.update_group_participants(group_id, "add", membros)
        #
        # 2. Remover um membro
        # api_client.update_group_participants(group_id, "remove", ["5531977776666"])
        #
        # 3. Promover a admin
        # api_client.update_group_participants(group_id, "promote", ["5511999998888"])
        params = {"groupJid": group_jid}
        payload = {"action": action, "participants": participants}
        return self._request("POST", "group/updateParticipant", params=params, json_payload=payload)

    def update_group_setting(self, group_jid: str, action: str) -> Dict[str, Any]:
        """Altera as configurações do grupo (quem pode enviar msg ou editar dados)."""
        # Exemplo(s) de uso:
        #
        # group_id = "1234567890@g.us"
        #
        # 1. Fechar o grupo (só admins enviam mensagens)
        # api_client.update_group_setting(group_id, "announcement")
        #
        # 2. Abrir o grupo (todos enviam mensagens)
        # api_client.update_group_setting(group_id, "not_announcement")
        params = {"groupJid": group_jid}
        payload = {"action": action}
        return self._request("POST", "group/updateSetting", params=params, json_payload=payload)

    def leave_group(self, group_jid: str) -> Dict[str, Any]:
        """Faz com que a instância saia de um grupo."""
        # Exemplo de uso:
        #
        # group_id = "1234567890@g.us"
        # api_client.leave_group(group_id)
        params = {"groupJid": group_jid}
        return self._request("DELETE", "group/leaveGroup", params=params)
