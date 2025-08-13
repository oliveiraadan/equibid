from flask import request, jsonify, json
from app import app
from providers.z_api import ZApiProvider

# Instancia o provider. A configuração é lida automaticamente do .env
try:
    z_api = ZApiProvider()
except RuntimeError as e:
    # Se a configuração falhar, a aplicação não deve iniciar.
    # Em um app real, você usaria um logger mais robusto.
    print(f"ERRO CRÍTICO: {e}")
    z_api = None


@app.route('/webhook', methods=['POST'])
def receber_webhook():
    """Endpoint para receber notificações de mensagens da Z-API."""
    if not z_api:
        return jsonify({"status": "error", "message": "Z-API Provider não inicializado"}), 500

    dados_recebidos = request.get_json()

    print("\n--- ✅ MENSAGEM RECEBIDA (VIA WEBHOOK) ---")
    print(json.dumps(dados_recebidos, indent=2))

    # Exemplo de resposta automática usando o provider
    if dados_recebidos and dados_recebidos.get("text", "").lower() == 'olá':
        remetente = dados_recebidos.get('phone')
        if remetente:
            try:
                z_api.send_text(
                    remetente, "Olá! Recebi sua mensagem de volta.")
            except RuntimeError as e:
                print(f"Erro ao enviar resposta automática: {e}")

    return jsonify({"status": "success"}), 200
