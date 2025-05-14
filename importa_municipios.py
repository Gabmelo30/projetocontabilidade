#!/usr/bin/env python3
"""
Script para importar municípios de um arquivo TXT para o banco de dados.

Uso: python import_municipios.py arquivo.txt

O script identifica automaticamente o formato do arquivo:
- CODIGO;NOME;UF (ponto e vírgula)
- CODIGO,NOME,UF (vírgula)

Exemplo:
    python import_municipios.py municipios.txt
"""

import os
import sys
import sqlite3
import logging
import chardet
from typing import List, Dict, Any, Tuple, Optional

# Configuração de logging
LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'importacao_municipios.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class MunicipioImporter:
    """Classe para importação de municípios a partir de arquivos TXT"""
    
    def __init__(self, db_path="app_rest_gyn.db"):
        """
        Inicializa o importador
        
        :param db_path: Caminho para o banco de dados SQLite
        """
        self.db_path = db_path
        logger.info(f"Usando banco de dados: {db_path}")
        
    def create_connection(self) -> Optional[sqlite3.Connection]:
        """Cria uma conexão com o banco de dados SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Para acessar colunas pelo nome
            return conn
        except sqlite3.Error as e:
            logger.error(f"Erro ao conectar ao banco de dados: {e}")
            return None
    
    def detect_encoding(self, filepath: str) -> Tuple[str, float]:
        """
        Detecta o encoding do arquivo
        
        :param filepath: Caminho para o arquivo
        :return: Tupla (encoding, confiança)
        """
        with open(filepath, 'rb') as file:
            raw_data = file.read(10000)  # Primeiros 10 KB
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            
        logger.info(f"Encoding detectado: {encoding} (Confiança: {confidence * 100:.2f}%)")
        return encoding, confidence
    
    def detect_format(self, lines: List[str]) -> Dict[str, Any]:
        """
        Detecta o formato do arquivo com base nas primeiras linhas
        
        :param lines: Lista com as primeiras linhas do arquivo
        :return: Dicionário com informações do formato
        """
        # Verificar o formato com a primeira linha não vazia
        first_line = next((line for line in lines if line.strip()), "")
        
        if ';' in first_line:
            # Formato com ponto-e-vírgula
            parts = first_line.split(';')
            if len(parts) != 3:
                raise ValueError(f"Formato inválido: esperado 3 partes separadas por ';', encontrado {len(parts)}")
            
            # Determinar qual coluna é a UF
            if len(parts[2].strip()) == 2 and parts[2].strip().isalpha():
                # CODIGO;NOME;UF
                logger.info("Formato detectado: CODIGO;NOME;UF")
                return {
                    'tipo': 'ponto_virgula',
                    'ordem': ['codigo', 'nome', 'uf']
                }
            else:
                raise ValueError(f"Não foi possível determinar a ordem das colunas: {first_line}")
            
        elif ',' in first_line:
            # Formato com vírgula
            parts = first_line.split(',')
            if len(parts) != 3:
                raise ValueError(f"Formato inválido: esperado 3 partes separadas por ',', encontrado {len(parts)}")
            
            # Determinar qual coluna é a UF
            if len(parts[2].strip()) == 2 and parts[2].strip().isalpha():
                # CODIGO,NOME,UF
                logger.info("Formato detectado: CODIGO,NOME,UF")
                return {
                    'tipo': 'virgula',
                    'ordem': ['codigo', 'nome', 'uf']
                }
            else:
                raise ValueError(f"Não foi possível determinar a ordem das colunas: {first_line}")
        else:
            raise ValueError(f"Formato não suportado: {first_line}")
    
    def import_municipios(self, filepath: str) -> int:
        """
        Importa municípios de um arquivo TXT para o banco de dados
        
        :param filepath: Caminho para o arquivo
        :return: Número de municípios importados
        """
        # Verificar se o arquivo existe
        if not os.path.exists(filepath):
            logger.error(f"Arquivo não encontrado: {filepath}")
            return 0
        
        # Detectar encoding
        encoding, _ = self.detect_encoding(filepath)
        
        # Definir encodings alternativos para tentar
        encodings_to_try = [encoding, 'utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        
        # Remover duplicatas
        encodings_to_try = list(dict.fromkeys(encodings_to_try))
        
        # Tentar cada encoding
        for encoding in encodings_to_try:
            try:
                logger.info(f"Tentando ler o arquivo com encoding: {encoding}")
                
                # Ler as primeiras linhas para detectar o formato
                with open(filepath, 'r', encoding=encoding) as file:
                    lines = [line.strip() for line in file.readlines()[:10] if line.strip()]
                
                if not lines:
                    logger.warning("Arquivo vazio ou não contém linhas válidas.")
                    continue
                
                # Detectar formato
                formato = self.detect_format(lines)
                
                # Criar conexão com o banco
                conn = self.create_connection()
                if not conn:
                    logger.error("Falha ao conectar ao banco de dados.")
                    return 0
                
                try:
                    cursor = conn.cursor()
                    
                    # Verificar se a tabela de municípios existe
                    cursor.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='tb_municipios'
                    """)
                    
                    if not cursor.fetchone():
                        # Criar a tabela
                        logger.info("Criando tabela tb_municipios...")
                        cursor.execute('''
                            CREATE TABLE tb_municipios (
                                uf TEXT,
                                cod_municipio TEXT,
                                nome_municipio TEXT,
                                PRIMARY KEY (uf, cod_municipio)
                            )
                        ''')
                    
                    # Limpar a tabela
                    logger.info("Limpando registros existentes...")
                    cursor.execute("DELETE FROM tb_municipios")
                    
                    # Processar o arquivo
                    return self._process_file(filepath, encoding, formato, conn)
                    
                finally:
                    if conn:
                        conn.close()
                        
            except UnicodeDecodeError:
                logger.warning(f"Não foi possível decodificar o arquivo com encoding {encoding}")
            except Exception as e:
                logger.error(f"Erro ao processar arquivo com encoding {encoding}: {e}")
        
        logger.error("Falha ao processar o arquivo com qualquer encoding.")
        return 0
    
    def _process_file(self, filepath: str, encoding: str, formato: Dict[str, Any], conn: sqlite3.Connection) -> int:
        """
        Processa o arquivo e importa os municípios
        
        :param filepath: Caminho para o arquivo
        :param encoding: Encoding do arquivo
        :param formato: Informações do formato
        :param conn: Conexão com o banco de dados
        :return: Número de municípios importados
        """
        cursor = conn.cursor()
        count = 0
        errors = 0
        
        try:
            # Reabrir o arquivo para processamento
            with open(filepath, 'r', encoding=encoding) as file:
                # Processar linha por linha
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Extrair dados conforme o formato
                        if formato['tipo'] == 'ponto_virgula':
                            parts = [part.strip() for part in line.split(';')]
                        elif formato['tipo'] == 'virgula':
                            parts = [part.strip() for part in line.split(',')]
                        else:
                            logger.warning(f"Formato não suportado na linha {line_num}")
                            continue
                        
                        # Verificar número de partes
                        if len(parts) != 3:
                            logger.warning(f"Linha {line_num} inválida, número incorreto de campos: {line}")
                            errors += 1
                            continue
                        
                        # Obter valores de acordo com a ordem detectada
                        cod_municipio = parts[0]
                        nome_municipio = parts[1]
                        uf = parts[2]
                        
                        # Validar valores
                        if not cod_municipio or not nome_municipio or not uf:
                            logger.warning(f"Linha {line_num} contém valores vazios: {line}")
                            errors += 1
                            continue
                        
                        # Validar UF (2 letras)
                        if len(uf) != 2 or not uf.isalpha():
                            logger.warning(f"Linha {line_num} contém UF inválida: {uf}")
                            errors += 1
                            continue
                        
                        # Normalizar dados
                        uf = uf.upper()
                        nome_municipio = nome_municipio.upper()
                        
                        # Inserir no banco
                        cursor.execute("""
                            INSERT OR REPLACE INTO tb_municipios 
                            (uf, cod_municipio, nome_municipio) 
                            VALUES (?, ?, ?)
                        """, (uf, cod_municipio, nome_municipio))
                        
                        count += 1
                        
                        # Log de progresso a cada 100 municípios
                        if count % 100 == 0:
                            logger.info(f"Processados {count} municípios...")
                            
                    except Exception as e:
                        logger.error(f"Erro ao processar linha {line_num}: {e}")
                        errors += 1
            
            # Commit das alterações
            conn.commit()
            
            # Log final
            logger.info(f"Importação concluída: {count} municípios importados")
            if errors > 0:
                logger.warning(f"Encontrados {errors} erros durante a importação")
                
            return count
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Erro durante importação: {e}")
            return 0

def main():
    """Função principal"""
    # Verificar argumentos
    if len(sys.argv) < 2:
        print(f"Uso: python {os.path.basename(__file__)} arquivo.txt")
        return 1
    
    arquivo = sys.argv[1]
    
    # Inicializar importador
    importer = MunicipioImporter()
    
    # Importar municípios
    count = importer.import_municipios(arquivo)
    
    if count > 0:
        print(f"\nSucesso! {count} municípios importados para o banco de dados.")
        return 0
    else:
        print("\nFalha na importação. Verifique os logs para mais detalhes.")
        return 1

if __name__ == "__main__":
    sys.exit(main())