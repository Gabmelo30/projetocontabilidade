import os
import logging
import sqlite3
import chardet
from typing import List, Tuple, Optional, Dict, Any

class MunicipioService:
    """
    Serviço para gerenciamento de municípios brasileiros
    """
    def __init__(self, db_path: str = "app_rest_gyn.db"):
        self.db_path = db_path
        self._setup_logging()
        
    def _setup_logging(self):
        """Configura o sistema de logging"""
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _create_connection(self):
        """Cria uma conexão com o banco de dados SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao conectar ao banco de dados: {e}")
            return None
    
    def get_municipios_by_uf(self, uf: str) -> List[Tuple[str, str]]:
        """
        Obtém todos os municípios de uma determinada UF
        
        :param uf: Sigla da UF (ex: GO, SP, RJ)
        :return: Lista de tuplas (nome_municipio, cod_municipio)
        """
        self.logger.info(f"Buscando municípios para UF: {uf}")
        
        # Validar UF
        if not uf or len(uf) != 2:
            self.logger.warning(f"UF inválida: {uf}")
            return []
            
        uf = uf.upper()  # Normalizar para maiúsculas
        
        conn = self._create_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            
            # Verificar tabelas existentes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas = [row[0] for row in cursor.fetchall()]
            
            # Estratégia 1: Verificar tabela tb_municipios (estrutura padrão)
            if 'tb_municipios' in tabelas:
                self.logger.debug("Buscando em tb_municipios")
                cursor.execute("""
                    SELECT nome_municipio, cod_municipio 
                    FROM tb_municipios 
                    WHERE uf = ? 
                    ORDER BY nome_municipio
                """, (uf,))
                
                municipios = cursor.fetchall()
                if municipios:
                    self.logger.info(f"Encontrados {len(municipios)} municípios para UF {uf} em tb_municipios")
                    return municipios
            
            # Estratégia 2: Verificar tabela tb_cod_municipio (estrutura alternativa)
            if 'tb_cod_municipio' in tabelas:
                self.logger.debug("Buscando em tb_cod_municipio")
                cursor.execute("""
                    SELECT municipio, cod_municipio 
                    FROM tb_cod_municipio 
                    WHERE UF = ? 
                    ORDER BY municipio
                """, (uf,))
                
                municipios = cursor.fetchall()
                if municipios:
                    self.logger.info(f"Encontrados {len(municipios)} municípios para UF {uf} em tb_cod_municipio")
                    return municipios
            
            # Estratégia 3: Detectar tabela automaticamente
            for tabela in tabelas:
                if 'munic' in tabela.lower() and tabela not in ['tb_municipios', 'tb_cod_municipio']:
                    try:
                        # Obter estrutura da tabela
                        cursor.execute(f"PRAGMA table_info({tabela})")
                        colunas = [(row[1], row[2].lower()) for row in cursor.fetchall()]
                        
                        # Identificar colunas relevantes
                        col_uf = next((col[0] for col in colunas if col[0].lower() in ['uf']), None)
                        col_municipio = next((col[0] for col in colunas 
                                            if 'munic' in col[0].lower() or 'nome' in col[0].lower()), None)
                        col_codigo = next((col[0] for col in colunas 
                                        if 'cod' in col[0].lower() or 'id' in col[0].lower()), None)
                        
                        if col_uf and col_municipio and col_codigo:
                            query = f"""
                                SELECT {col_municipio}, {col_codigo} 
                                FROM {tabela} 
                                WHERE {col_uf} = ? 
                                ORDER BY {col_municipio}
                            """
                            cursor.execute(query, (uf,))
                            
                            municipios = cursor.fetchall()
                            if municipios:
                                self.logger.info(f"Encontrados {len(municipios)} municípios para UF {uf} em {tabela}")
                                return municipios
                    except Exception as e:
                        self.logger.error(f"Erro ao tentar detectar estrutura em {tabela}: {e}")
            
            self.logger.warning(f"Nenhum município encontrado para UF {uf}")
            return []
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar municípios: {e}")
            return []
        finally:
            conn.close()
    
    def import_municipios_from_txt(self, filepath: str) -> int:
        """
        Importa municípios de um arquivo TXT
        
        :param filepath: Caminho para o arquivo de municípios
        :return: Número de municípios importados
        """
        self.logger.info(f"Iniciando importação de municípios: {filepath}")
        
        # Verificar existência do arquivo
        if not os.path.exists(filepath):
            self.logger.error(f"Arquivo não encontrado: {filepath}")
            return 0
            
        # Detectar encoding do arquivo
        try:
            with open(filepath, 'rb') as file:
                raw_data = file.read(10000)  # Ler primeiros 10 KB
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']
                
            self.logger.info(f"Encoding detectado: {encoding} (Confiança: {confidence * 100:.2f}%)")
            
            # Lista de encodings para tentar
            encodings_to_try = [
                encoding,       # Encoding detectado
                'utf-8',        # UTF-8 padrão
                'latin1',       # Alternativa comum
                'iso-8859-1',   # Alternativa comum
                'cp1252'        # Windows Latin-1
            ]
            
            # Remover duplicatas e None
            encodings_to_try = list(dict.fromkeys([e for e in encodings_to_try if e]))
            
            # Determinar formato do arquivo
            formato = self._detectar_formato_arquivo(filepath, encodings_to_try)
            if not formato:
                self.logger.error("Não foi possível determinar o formato do arquivo")
                return 0
                
            self.logger.info(f"Formato detectado: {formato['tipo']}")
            
            # Criar ou verificar tabela
            conn = self._create_connection()
            if not conn:
                return 0
                
            try:
                cursor = conn.cursor()
                
                # Criar tabela se não existir
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tb_municipios (
                        uf TEXT,
                        cod_municipio TEXT,
                        nome_municipio TEXT,
                        PRIMARY KEY (uf, cod_municipio)
                    )
                ''')
                
                # Limpar tabela existente
                cursor.execute("DELETE FROM tb_municipios")
                
                # Importar municípios
                imported_count = self._importar_arquivo(filepath, formato, conn)
                
                # Commit das alterações
                conn.commit()
                
                return imported_count
                
            except Exception as e:
                self.logger.error(f"Erro durante a importação: {e}")
                return 0
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Erro ao processar arquivo: {e}")
            return 0
    
    def _detectar_formato_arquivo(self, filepath: str, encodings: List[str]) -> Optional[Dict[str, Any]]:
        """
        Detecta o formato do arquivo de municípios
        
        :param filepath: Caminho para o arquivo
        :param encodings: Lista de encodings para tentar
        :return: Dicionário com informações do formato ou None se não detectado
        """
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as file:
                    # Ler primeiras linhas não vazias
                    linhas = []
                    for _ in range(10):  # Ler até 10 linhas
                        linha = file.readline().strip()
                        if linha:
                            linhas.append(linha)
                        if len(linhas) >= 3:
                            break
                    
                    if not linhas:
                        continue
                        
                    # Verificar formato pelo separador
                    primeira_linha = linhas[0]
                    
                    # Formato 1: codigo;nome;uf
                    if ';' in primeira_linha:
                        parts = primeira_linha.split(';')
                        if len(parts) == 3:
                            # Verificar qual elemento é a UF (geralmente tem 2 caracteres)
                            if len(parts[0].strip()) == 2 and parts[0].strip().isalpha():
                                # Formato: UF;NOME;CODIGO
                                return {
                                    'tipo': 'ponto_virgula',
                                    'encoding': encoding,
                                    'ordem': ['uf', 'nome', 'codigo']
                                }
                            elif len(parts[2].strip()) == 2 and parts[2].strip().isalpha():
                                # Formato: CODIGO;NOME;UF
                                return {
                                    'tipo': 'ponto_virgula',
                                    'encoding': encoding,
                                    'ordem': ['codigo', 'nome', 'uf']
                                }
                    
                    # Formato 2: codigo,nome,uf
                    elif ',' in primeira_linha and not "Código=" in primeira_linha:
                        parts = primeira_linha.split(',')
                        if len(parts) == 3:
                            # Verificar qual elemento é a UF (geralmente tem 2 caracteres)
                            if len(parts[0].strip()) == 2 and parts[0].strip().isalpha():
                                # Formato: UF,NOME,CODIGO
                                return {
                                    'tipo': 'virgula',
                                    'encoding': encoding,
                                    'ordem': ['uf', 'nome', 'codigo']
                                }
                            elif len(parts[2].strip()) == 2 and parts[2].strip().isalpha():
                                # Formato: CODIGO,NOME,UF
                                return {
                                    'tipo': 'virgula',
                                    'encoding': encoding,
                                    'ordem': ['codigo', 'nome', 'uf']
                                }
                    
                    # Formato 3: Processando: Código=123, Município=Nome, UF=XX
                    elif "Código=" in primeira_linha and "Município=" in primeira_linha and "UF=" in primeira_linha:
                        return {
                            'tipo': 'chave_valor',
                            'encoding': encoding
                        }
            
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.logger.error(f"Erro ao detectar formato com encoding {encoding}: {e}")
                
        return None
    
    def _importar_arquivo(self, filepath: str, formato: Dict[str, Any], conn: sqlite3.Connection) -> int:
        """
        Importa os municípios do arquivo para o banco de dados
        
        :param filepath: Caminho para o arquivo
        :param formato: Informações do formato
        :param conn: Conexão com o banco de dados
        :return: Número de municípios importados
        """
        cursor = conn.cursor()
        imported_count = 0
        error_count = 0
        
        try:
            with open(filepath, 'r', encoding=formato['encoding']) as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        # Extrair dados conforme o formato
                        cod_municipio = None
                        nome_municipio = None
                        uf = None
                        
                        if formato['tipo'] == 'ponto_virgula':
                            parts = [p.strip() for p in line.split(';')]
                            if len(parts) != 3:
                                self.logger.warning(f"Linha {line_num} inválida: {line}")
                                continue
                                
                            # Atribuir valores conforme a ordem detectada
                            for i, campo in enumerate(formato['ordem']):
                                if campo == 'codigo':
                                    cod_municipio = parts[i]
                                elif campo == 'nome':
                                    nome_municipio = parts[i]
                                elif campo == 'uf':
                                    uf = parts[i]
                                    
                        elif formato['tipo'] == 'virgula':
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) != 3:
                                self.logger.warning(f"Linha {line_num} inválida: {line}")
                                continue
                                
                            # Atribuir valores conforme a ordem detectada
                            for i, campo in enumerate(formato['ordem']):
                                if campo == 'codigo':
                                    cod_municipio = parts[i]
                                elif campo == 'nome':
                                    nome_municipio = parts[i]
                                elif campo == 'uf':
                                    uf = parts[i]
                                    
                        elif formato['tipo'] == 'chave_valor':
                            # Remover prefixo se existir
                            if line.startswith("Processando: "):
                                line = line.replace("Processando: ", "")
                                
                            # Extrair valores utilizando os identificadores
                            if "Código=" in line and "Município=" in line and "UF=" in line:
                                cod_municipio = line.split("Código=")[1].split(",")[0].strip()
                                nome_municipio = line.split("Município=")[1].split(",")[0].strip()
                                uf = line.split("UF=")[1].strip()
                        
                        # Validar dados
                        if not all([cod_municipio, nome_municipio, uf]):
                            self.logger.warning(
                                f"Dados incompletos na linha {line_num}: código={cod_municipio}, "
                                f"município={nome_municipio}, UF={uf}"
                            )
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
                        
                        imported_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Erro ao processar linha {line_num}: {e}")
                        error_count += 1
                        
            self.logger.info(f"Importação concluída: {imported_count} municípios importados, {error_count} erros")
            return imported_count
            
        except Exception as e:
            self.logger.error(f"Erro ao ler arquivo: {e}")
            return imported_count