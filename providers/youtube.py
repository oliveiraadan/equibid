import os
import subprocess
import json
import re
from dotenv import load_dotenv
from pathlib import Path

class YouTubeLiveDownloader:
    """
    Uma classe para baixar e gerenciar transmissões ao vivo do YouTube.
    O caminho de saída é obtido da variável de ambiente YOUTUBE_DIR.
    O nome do arquivo de saída é formatado como 'AAAA-MM-DD-Titulo_Formatado_[videoId]'.
    """

    def __init__(self):
        """
        Inicializa o downloader.
        - Carrega variáveis do arquivo .env.
        - Obtém o diretório de saída da variável YOUTUBE_DIR.
        - Cria o diretório de saída, se ele não existir.
        """
        load_dotenv() # Carrega as variáveis do arquivo .env

        # Obtém o caminho do diretório da variável de ambiente
        output_dir_str = os.getenv("YOUTUBE_DIR")

        # Valida se a variável foi definida no arquivo .env
        if not output_dir_str:
            raise ValueError("A variável de ambiente 'YOUTUBE_DIR' não está definida no arquivo .env")

        # Usa pathlib para um tratamento de caminhos mais robusto e cria o diretório
        self.output_folder = Path(output_dir_str).resolve()
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"Downloader inicializado. Os vídeos serão salvos em: '{self.output_folder}'")

    def _format_filename_part(self, text: str) -> str:
        """
        Limpa uma string para ser usada como parte de um nome de arquivo.
        - Substitui espaços por underscores.
        - Remove caracteres inválidos na maioria dos sistemas de arquivos.
        """
        text = re.sub(r'\s+', '_', text)
        text = re.sub(r'[/\\?%*:|"<>]', '', text)
        return text
    
    def _get_video_metadata(self, url: str) -> dict | None:
        """Busca os metadados do vídeo usando yt-dlp --dump-json."""
        command = ['yt-dlp', '--dump-json', url]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            return json.loads(result.stdout)
        except Exception:
            return None

    def _execute_yt_dlp_command(self, command: list) -> bool:
        """Método interno para executar comandos yt-dlp e tratar erros."""
        try:
            subprocess.run(command, check=True)
            print("\nOperação concluída com sucesso!")
            return True
        except FileNotFoundError:
            print("\nERRO: Comando 'yt-dlp' não encontrado.")
            print("Por favor, garanta que o yt-dlp está instalado e acessível no PATH do sistema.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"\nOcorreu um erro ao executar o yt-dlp: {e}")
            return False

    def get_stream_status(self, url: str) -> str:
        """
        Verifica se uma URL do YouTube corresponde a uma transmissão ao vivo em andamento,
        uma transmissão finalizada (VOD), ou um vídeo comum.
        """
        print(f"\n🔍 Verificando status para a URL: {url}")
        metadata = self._get_video_metadata(url)

        if not metadata:
            print("❌ ERRO: URL inválida ou vídeo indisponível.")
            return "ERROR"
        
        if metadata.get('is_live'):
            print("✅ Status: Transmissão ao vivo em andamento.")
            return "LIVE"
        elif metadata.get('was_live'):
            print("✅ Status: Transmissão finalizada (VOD).")
            return "FINISHED"
        else:
            print("✅ Status: Não é uma transmissão ao vivo (vídeo comum).")
            return "NOT_A_LIVE_STREAM"

    def _download_with_custom_filename(self, url: str, is_live: bool = False):
        """Lógica interna de download para gerar o nome do arquivo."""
        print("\nBuscando metadados do vídeo para gerar o nome do arquivo...")
        metadata = self._get_video_metadata(url)
        
        if not metadata:
            print("❌ Não foi possível obter os metadados. Abortando o download.")
            return

        title = metadata.get('title', 'sem_titulo')
        video_id = metadata.get('id', 'sem_id')
        upload_date = metadata.get('upload_date', '00000000') # Formato AAAAMMDD

        # Formata a data de AAAAMMDD para AAAA-MM-DD
        formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        
        # Formata o título
        formatted_title = self._format_filename_part(title)

        # Constrói a base do nome final do arquivo
        final_filename_base = f"{formatted_date}-{formatted_title}[{video_id}]"
        
        # Cria o caminho de saída completo usando pathlib e converte para string
        output_path = str(self.output_folder / f"{final_filename_base}.mp4")

        print(f"Nome do arquivo gerado: {final_filename_base}.mp4")
        print(f"Iniciando download para: {output_path}")

        command = ['yt-dlp']
        if is_live:
            command.append('--live-from-start')
        
        command.extend([
            '--output', output_path,
            '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '--merge-output-format', 'mp4',
            url
        ])

        self._execute_yt_dlp_command(command)

    def download_finished_stream(self, url: str):
        """
        Baixa uma transmissão que já foi finalizada (VOD).
        """
        print(f"\n📥 Preparando para baixar transmissão finalizada: {url}")
        self._download_with_custom_filename(url, is_live=False)

    def record_live_stream(self, url: str):
        """
        Grava uma transmissão ao vivo que está ativa no momento.
        """
        print(f"\n🔴 Preparando para gravar transmissão ao vivo: {url}")
        print("Pressione Ctrl+C no terminal para parar a gravação manualmente.")
        self._download_with_custom_filename(url, is_live=True)

# --- Exemplo de Como Usar a Classe ---
if __name__ == "__main__":
    try:
        # Agora a classe é instanciada sem argumentos, pois o caminho vem do .env
        downloader = YouTubeLiveDownloader()

        # URL de exemplo (substitua por uma real para testar)
        test_url = "https://www.youtube.com/watch?v=bpBN7IVmHeM"
        
        status = downloader.get_stream_status(test_url)

        if status == "LIVE":
            downloader.record_live_stream(test_url)
        elif status in ["FINISHED", "NOT_A_LIVE_STREAM"]:
            downloader.download_finished_stream(test_url)
        else:
            print("\nNão foi possível processar a URL.")
            
    except ValueError as e:
        # Captura o erro se YOUTUBE_DIR não estiver no .env
        print(f"ERRO DE CONFIGURAÇÃO: {e}")