from app import app
from providers.z_api import ZApiProvider
from typing import List, Dict

# Instancia o provider para usar no exemplo
try:
    z_api = ZApiProvider()
except RuntimeError as e:
    print(f"ERRO CRÍTICO ao iniciar: {e}")
    z_api = None


def notificar_match_equibid(
    numero_destino: str,
    nome_usuario: str,
    nome_lote: str,
    url_lote: str,
    url_buscas: str
):
    """
    Função de exemplo que usa o ZApiProvider para enviar a notificação da Equibid.
    """
    if not z_api:
        print("Não foi possível enviar notificação: Z-API Provider não está disponível.")
        return

    print("\n--- INICIANDO TESTE DE NOTIFICAÇÃO EQUİBİD ---")
    
    # Monta a mensagem e os botões
    mensagem = f"Olá, {nome_usuario}! 👋\n\nEncontramos um novo lote que corresponde à sua busca:\n\n🐴 *{nome_lote}*"
    
    botoes: List[Dict] = [
        {"id": "1", "type": "URL", "label": "Ver Detalhes do Lote", "url": url_lote},
        {"id": "2", "type": "URL", "label": "Gerenciar Minhas Buscas", "url": url_buscas}
    ]
    
    try:
        resultado = z_api.send_button_actions(
            phone=numero_destino,
            message=mensagem,
            title="🎉 Novo Match na Equibid!",
            footer="Clique nos botões para mais informações.",
            actions=botoes
        )
        print("Resultado do envio:", json.dumps(resultado, indent=2))
    except RuntimeError as e:
        print(f"Falha ao enviar notificação: {e}")
    
    print("--- TESTE DE NOTIFICAÇÃO FINALIZADO ---\n")


if __name__ == '__main__':
    
    # --- Bloco de Exemplo: Como chamar a notificação da Equibid ---
    # Descomente para testar
    
    notificar_match_equibid(
        numero_destino="5511996347828",  # <-- Substitua pelo seu WhatsApp
        nome_usuario="Daniel",
        nome_lote="Lote 25 - Cavalo Campeão de Marcha",
        url_lote="https://www.equibid.com.br/lotes/12345",
        url_buscas="https://www.equibid.com.br/minhas-buscas"
    )
   

    # O host '0.0.0.0' é crucial para que o container Docker possa expor a porta corretamente.
  #  app.run(host='0.0.0.0', port=5000)