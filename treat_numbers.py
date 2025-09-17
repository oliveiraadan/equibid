import json
import re
import pandas as pd
import sys # Módulo para interagir com o sistema

# --------------------------------------------------------------------------
# As funções de processamento permanecem exatamente as mesmas
# --------------------------------------------------------------------------
def analisar_numero_whatsapp(numero_completo):
    """
    Analisa uma string numérica de telefone para extrair DDI, DDD e número.
    """
    if numero_completo.startswith('55') and len(numero_completo) in [12, 13]:
        return {'DDI': '55', 'DDD': numero_completo[2:4], 'Telefone': numero_completo[4:]}
    elif numero_completo.startswith('1') and len(numero_completo) == 11:
        return {'DDI': '1', 'DDD': numero_completo[1:4], 'Telefone': numero_completo[4:]}
    else:
        return {'DDI': None, 'DDD': None, 'Telefone': None}

def processar_json_agregado_para_csv(dados_json):
    """
    Processa um dicionário JSON, agrega os dados por contato e retorna
    uma lista de dicionários pronta para ser convertida em CSV.
    """
    dados_para_planilha = []
    regex_numero = re.compile(r"^(\d+)@s\.whatsapp\.net$")

    for contato_str, info in dados_json.items():
        match = regex_numero.match(contato_str)
        info_numero = {'DDI': None, 'DDD': None, 'Telefone': None}
        if match:
            numero_completo = match.group(1)
            info_numero = analisar_numero_whatsapp(numero_completo)

        quantidade_grupos = 0
        eh_admin = False

        if 'groups' in info and isinstance(info['groups'], list):
            quantidade_grupos = len(info['groups'])
            for grupo in info['groups']:
                if grupo.get('role_in_group') in ['admin', 'superadmin']:
                    eh_admin = True
                    break
        
        linha = {
            'Contato Original': contato_str,
            'DDI': info_numero.get('DDI'),
            'DDD': info_numero.get('DDD'),
            'Telefone': info_numero.get('Telefone'),
            'É Admin?': "Sim" if eh_admin else "Não",
            'Quantidade de Grupos': quantidade_grupos
        }
        dados_para_planilha.append(linha)
    
    return dados_para_planilha

# --------------------------------------------------------------------------
# PASSO PRINCIPAL: Carregar, Processar e Salvar
# --------------------------------------------------------------------------
def main():
    """
    Função principal que orquestra o processo de carregar o arquivo,
    processar os dados e salvar o CSV.
    """
    # <<< ALTERE O NOME DO ARQUIVO AQUI SE NECESSÁRIO
    caminho_do_arquivo_json = "D:\equibid-storage\whatsapp\participantes_grupos.json"
    
    print(f"Tentando carregar dados do arquivo: '{caminho_do_arquivo_json}'")

    try:
        # Abre o arquivo JSON para leitura ('r') com codificação UTF-8
        with open(caminho_do_arquivo_json, 'r', encoding='utf-8') as f:
            # json.load() lê o conteúdo do arquivo e converte para um dicionário Python
            json_data = json.load(f)
        print("Arquivo JSON carregado com sucesso!")

    except FileNotFoundError:
        print(f"ERRO: Arquivo não encontrado no caminho especificado: '{caminho_do_arquivo_json}'")
        print("Por favor, verifique se o nome do arquivo está correto e se ele está na mesma pasta do script.")
        sys.exit() # Encerra o script se o arquivo não for encontrado
    except json.JSONDecodeError:
        print(f"ERRO: O arquivo '{caminho_do_arquivo_json}' não contém um JSON válido.")
        print("Por favor, verifique a formatação do arquivo.")
        sys.exit() # Encerra o script se o JSON for inválido

    # Processa os dados que foram carregados do arquivo
    dados_finais = processar_json_agregado_para_csv(json_data)

    # Converte a lista de resultados em um DataFrame do Pandas
    df = pd.DataFrame(dados_finais)

    print("\n--- Dados Agregados a serem salvos no CSV ---")
    print(df)

    # Salva o DataFrame em um único arquivo CSV
    nome_do_arquivo_saida = 'relatorio_consolidado_contatos1.csv'
    df.to_csv(nome_do_arquivo_saida, index=False, encoding='utf-8-sig')

    print(f"\nProcesso concluído! Arquivo '{nome_do_arquivo_saida}' salvo com sucesso!")

# --- Executa a função principal ---
if __name__ == "__main__":
    main()