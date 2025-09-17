# gerar_indice_participantes.py
import os
import json
from evolution_api import EvolutionAPIProvider, EvolutionAPIError
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
  # Certifique-se de importar datetime corretamente

# Nome do arquivo de saída para o novo índice
NOME_ARQUIVO_SAIDA = f"D:/equibid-storage/whatsapp/participantes_grupos_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"


def gerar_indice_de_participantes():
    """
    Script rápido para gerar um índice de todos os participantes e os grupos
    aos quais pertencem, sem buscar detalhes de contato adicionais.
    """
    print("Iniciando a geração do índice de participantes por grupo...")
    print("="*60)

    try:
        api_client = EvolutionAPIProvider()
    except RuntimeError as e:
        print(f"❌ Erro de Configuração: {e}")
        print("\n[ATENÇÃO] Configure as variáveis de ambiente antes de executar:")
        print("  - EVOLUTION_SERVER_URL, EVOLUTION_INSTANCE, EVOLUTION_API_KEY")
        return

    # O índice começa vazio a cada execução
    participants_index = {}

    try:
        # 1. Busca a lista de grupos e participantes em uma única chamada
        print("\nBuscando a lista de grupos e participantes da API...")
        all_groups = api_client.fetch_all_groups(get_participants=True)

        if not all_groups:
            print("\nNenhum grupo foi encontrado na varredura da API.")
            return

        total_grupos = len(all_groups)
        print(f"✅ Sucesso! {total_grupos} grupo(s) encontrado(s).")
        print("Processando e criando o índice...")
        print("-" * 60)

        # 2. Itera sobre os grupos para construir o índice
        for index, group in enumerate(all_groups, 1):
            group_name = group.get('subject', 'Grupo Sem Nome')
            group_id = group.get('id')
            print(f"Processando grupo {index}/{total_grupos}: {group_name}")

            participants_no_grupo = group.get('participants', [])

            for participant in participants_no_grupo:
                participant_id = participant.get('id')
                if not participant_id:
                    continue

                # Se o participante ainda não está no nosso índice, cria a entrada base
                if participant_id not in participants_index:
                    participants_index[participant_id] = {
                        "groups": []
                    }
                # Adiciona o grupo atual à lista de grupos deste participante
                participants_index[participant_id]['groups'].append({
                    "group_id": group_id,
                    "group_name": group_name,
                    "role_in_group": participant.get('admin', 'member')
                })

        # 3. Garante que o diretório de saída existe
        diretorio_saida = os.path.dirname(NOME_ARQUIVO_SAIDA)
        if diretorio_saida and not os.path.exists(diretorio_saida):
            os.makedirs(diretorio_saida)

        # 4. Salva o índice recém-criado no arquivo
        with open(NOME_ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
            json.dump(participants_index, f, indent=4, ensure_ascii=False)

        print("-" * 60)
        message = f"_find_group_participants.py_\n\n✅ Operação concluída! *{len(participants_index)} participantes* únicos em *{total_grupos} grupos.*"

        print(message)
        api_client.send_text("5511996347828", message)

    except EvolutionAPIError as e:
        print(f"\n❌ Erro ao se comunicar com a Evolution API: {e}")
    except Exception as e:
        print(f"\n❌ Ocorreu um erro inesperado: {e}")


if __name__ == "__main__":
    gerar_indice_de_participantes()
