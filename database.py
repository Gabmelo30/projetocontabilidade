import dbm
import io
import sqlite3
from sqlite3 import Error
import os
import sys
import tempfile
from flask import make_response
import pandas as pd
import logging
import chardet
import re

class DatabaseManager:
    def __init__(self, db_file="app_rest_gyn.db"):
        app_path = self.get_application_path()
        self.db_file = os.path.join(app_path, db_file)
        self.create_tables()
        self.populate_default_data()
        self.logger = logging.getLogger(__name__)

        

    def validate_cnpj(self, cnpj):
        """
        Valida o CNPJ de acordo com as regras oficiais
        
        :param cnpj: CNPJ a ser validado
        :return: True se válido, False caso contrário
        """
        # Remover caracteres não numéricos
        cnpj = ''.join(filter(str.isdigit, str(cnpj)))
        
        # Verificar se tem 14 dígitos
        if len(cnpj) != 14:
            return False
        
        # Verificar se todos os dígitos são iguais
        if len(set(cnpj)) == 1:
            return False
        
        # Calcular primeiro dígito verificador
        soma = 0
        peso = 10
        for digito in cnpj[:9]:
            soma += int(digito) * peso
            peso -= 1
        
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto
        
        if int(cnpj[9]) != digito1:
            return False
        
        # Calcular segundo dígito verificador
        soma = 0
        peso = 11
        for digito in cnpj[:10]:
            soma += int(digito) * peso
            peso -= 1
        
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto
        
        return int(cnpj[10]) == digito2
    def format_cnpj(cnpj):
        """
        formata o CNPJ com pontuação
        :param cnpj: CNPJ a ser formatado
        :return: CNPJ formatado
        """
        cnpj = ''.join(filter(str.isdigit, str(cnpj)))

        if len(cnpj) != 14:
            return cnpj
        
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    
    def demo_validation():
        # Caoso de teste
        teste_cnpjs = [
            "",  # Válido
            "",  # Inválido
            "",  # Inválido
            "",  # Inválido
            ""   # Válido
        ]
        print("Demonstração de validação de CNPJ:")
        for cnpj in teste_cnpjs:
            resultado = validate_cnpj(cnpj)
            print(f"CNPJ: {cnpj} - Válido: {resultado}")

    def get_municipios_by_uf(self, uf):
        """
        Obtém todos os municípios de uma determinada UF de maneira robusta,
        verificando diferentes estruturas de tabelas no banco de dados.
        
        :param uf: Sigla da UF (ex: GO, SP, RJ)
        :return: Lista de tuplas (nome_municipio, cod_municipio)
        """
        # Validação básica da UF
        if not uf or len(uf) != 2:
            print(f"ERRO: UF inválida - {uf}")
            return []
        
        uf = uf.upper()  # Normalizar para maiúsculas
        
        conn = self.create_connection()
        if conn is None:
            print("Não foi possível conectar ao banco de dados")
            return []
        
        try:
            cursor = conn.cursor()
            
            # Verificar tabelas disponíveis
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas = [row[0] for row in cursor.fetchall()]
            
            # Estratégia 1: Tentar tabela tb_municipios (padrão mais recente)
            if 'tb_municipios' in tabelas:
                try:
                    cursor.execute("""
                        SELECT nome_municipio, cod_municipio 
                        FROM tb_municipios 
                        WHERE uf = ? 
                        ORDER BY nome_municipio
                    """, (uf,))
                    
                    municipios = cursor.fetchall()
                    if municipios:
                        print(f"Encontrados {len(municipios)} municípios para UF {uf} em tb_municipios")
                        return municipios
                except Exception as e:
                    print(f"Erro ao consultar tb_municipios: {e}")
            
            # Estratégia 2: Tentar tabela tb_cod_municipio (estrutura alternativa)
            if 'tb_cod_municipio' in tabelas:
                try:
                    cursor.execute("""
                        SELECT municipio, cod_municipio 
                        FROM tb_cod_municipio 
                        WHERE UF = ? 
                        ORDER BY municipio
                    """, (uf,))
                    
                    municipios = cursor.fetchall()
                    if municipios:
                        print(f"Encontrados {len(municipios)} municípios para UF {uf} em tb_cod_municipio")
                        return municipios
                except Exception as e:
                    print(f"Erro ao consultar tb_cod_municipio: {e}")
            
            # Estratégia 3: Busca automática em qualquer tabela com 'munic' no nome
            for tabela in tabelas:
                if 'munic' in tabela.lower() and tabela not in ['tb_municipios', 'tb_cod_municipio']:
                    try:
                        # Detectar estrutura da tabela
                        cursor.execute(f"PRAGMA table_info({tabela})")
                        colunas = [(row[1], row[2]) for row in cursor.fetchall()]
                        
                        # Tentar identificar as colunas relevantes
                        col_uf = next((col[0] for col in colunas if col[0].lower() in ['uf']), None)
                        col_nome = next((col[0] for col in colunas 
                                        if 'nome' in col[0].lower() or 'munic' in col[0].lower()), None)
                        col_codigo = next((col[0] for col in colunas 
                                        if 'cod' in col[0].lower()), None)
                        
                        if col_uf and col_nome and col_codigo:
                            query = f"""
                                SELECT {col_nome}, {col_codigo} 
                                FROM {tabela} 
                                WHERE {col_uf} = ? 
                                ORDER BY {col_nome}
                            """
                            cursor.execute(query, (uf,))
                            
                            municipios = cursor.fetchall()
                            if municipios:
                                print(f"Encontrados {len(municipios)} municípios para UF {uf} em {tabela} (detecção automática)")
                                return municipios
                    except Exception as e:
                        print(f"Erro ao analisar tabela {tabela}: {e}")
            
            # Se chegou até aqui, não encontrou municípios
            print(f"Nenhum município encontrado para UF {uf}")
            return []
            
        except Exception as e:
            print(f"Erro ao buscar municípios para UF {uf}: {e}")
            return []
            
        finally:
            if conn:
                conn.close()

    def get_application_path(self):
        """Obtém o caminho base da aplicação"""
        if getattr(sys, "frozen", False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        return application_path

    def create_connection(self):
        """Cria uma conexão com o banco de dados SQLite"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            return conn
        except Error as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
        return conn

    def create_tables(self):
        """Cria as tabelas do banco de dados"""
        conn = self.create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                # Criar tabela de notas fiscais
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tb_notas_fiscais (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        referencia TEXT NOT NULL,
                        cadastrado_goiania BOOLEAN,
                        fora_pais BOOLEAN,
                        cnpj TEXT,
                        fornecedor_id INTEGER,
                        inscricao_municipal TEXT,
                        tipo_servico TEXT,
                        base_calculo TEXT,
                        numero_nf TEXT,
                        dt_emissao DATE,
                        dt_pagamento DATE,
                        aliquota REAL,
                        valor_nf REAL,
                        recolhimento TEXT,
                        recibo TEXT,
                        FOREIGN KEY (fornecedor_id) REFERENCES tb_fornecedores (id),
                        FOREIGN KEY (recolhimento) REFERENCES tb_tipo_de_recolhimento (id)
                    )
                ''')
                # Criar tabela de fornecedores
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tb_fornecedores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        descricao_fornecedor TEXT NOT NULL,
                        uf TEXT,
                        municipio TEXT,
                        cod_municipio TEXT,
                        cadastrado_goiania BOOLEAN,
                        fora_pais BOOLEAN
                    )
                ''')
                # Criar tabela de municípios
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS tb_municipios (
                        uf TEXT,
                        cod_municipio TEXT,
                        nome_municipio TEXT,
                        PRIMARY KEY (uf, cod_municipio)
                    )
                ''')
                # Criar tabela de tomadores
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tb_tomadores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        razao_social TEXT NOT NULL,
                        cnpj TEXT NOT NULL,
                        inscricao TEXT,
                        usuario TEXT NOT NULL
                    )
                ''')
                conn.commit()
            except Error as e:
                print(f"Erro ao criar tabelas: {e}")
            finally:
                conn.close()

    def populate_default_data(self):
        """Popula dados padrão se necessário"""
        conn = self.create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                
                # Verificar se a tabela tb_tipo_de_recolhimento está vazia
                cursor.execute("SELECT COUNT(*) FROM tb_tipo_de_recolhimento")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    # Adicionar tipos de recolhimento padrão
                    tipos_recolhimento = [
                        ('Recolhimento Normal',),
                        ('Recolhimento Complementar',),
                        ('Recolhimento Substituto',),
                        ('Recolhimento ISS Fixo',),
                        ('Recolhimento Estimado',)
                    ]
                    
                    cursor.executemany("""
                        INSERT INTO tb_tipo_de_recolhimento (recolhimento)
                        VALUES (?)
                    """, tipos_recolhimento)
                    
                    conn.commit()
                    print(f"{len(tipos_recolhimento)} tipos de recolhimento adicionados com sucesso.")
                    
                # Verificar outras tabelas...
                
            except Error as e:
                print(f"Erro ao popular dados padrão: {e}")
            finally:
                conn.close()

    def get_all_ufs(self):
        """Obtém todas as UFs brasileiras"""
        conn = self.create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT uf FROM tb_municipios ORDER BY uf")
                ufs = [row[0] for row in cursor.fetchall()]
                if ufs:
                    return ufs
            except Error as e:
                print(f"Erro ao obter UFs do banco de dados: {e}")
            finally:
                conn.close()
        return [
            "AC", "AL", "AP", "AM", "BA", "CE", "DF",
            "ES", "GO", "MA", "MT", "MS", "MG", "PA",
            "PB", "PR", "PE", "PI", "RJ", "RN", "RS",
            "RO", "RR", "SC", "SP", "SE", "TO"
        ]

    def get_all_tipos_servico(self):
        """Obtém todos os tipos de serviço"""
        return ["00 - normal", "02 - Imune", "03 - Art 54 do CTM", "04 -Liminar",
                "05 - Simples Nacional", "07 - ISS Esrimado", "08 - Não Incidência",
                "09 - Isento", "10 - Imposto fixo"]

    def get_all_bases_calculo(self):
        """Obtém todas as bases de cálculo"""
        return ["00 - base de caluclo", "01 - Publicidade e propaganda", "02 - Representação",
                "03 - Corretagem de seguro", "04 - Construção civil", "05 - call center",
                "06 - Estação Digital", "07 - Serviços de saúde (órtese e prótese)"]

    def get_all_recolhimentos(self):
        """Obtém todos os tipos de recolhimento"""
        return ["Recolhimento "]

    def get_all_tomadores(self):
        """Obtém todos os tomadores"""
        conn = self.create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tb_tomadores")
                return cursor.fetchall()
            except Error as e:
                print(f"Erro ao obter tomadores: {e}")
            finally:
                conn.close()
        return []

    def get_notas_fiscais_paginadas(self, page=1, per_page=10, search=None):
        """Retorna notas fiscais paginadas com busca opcional"""
        conn = self.create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                query = """
                    SELECT
                        nf.id,
                        nf.referencia,
                        nf.cnpj,
                        f.descricao_fornecedor,
                        nf.tipo_servico,
                        nf.base_calculo,
                        nf.numero_nf,
                        nf.dt_emissao,
                        nf.dt_pagamento,
                        nf.aliquota,
                        nf.valor_nf,
                        tr.recolhimento
                    FROM tb_notas_fiscais nf
                    LEFT JOIN tb_fornecedores f ON nf.fornecedor_id = f.id
                    LEFT JOIN tb_tipo_de_recolhimento tr ON nf.recolhimento = tr.id
                """

                params = []
                if search:
                    query += """
                    WHERE nf.cnpj LIKE ? OR
                        f.descricao_fornecedor LIKE ? OR
                        nf.numero_nf LIKE ?
                    """
                    search_param = f"%{search}%"
                    params.extend([search_param, search_param, search_param])

                query += " ORDER BY nf.dt_emissao DESC"

                count_query = f"SELECT COUNT(*) FROM ({query}) as count_query"
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]

                query += " LIMIT ? OFFSET ?"
                offset = (page - 1) * per_page
                params.extend([per_page, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return {
                    'rows': rows,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page
                }

            except Error as e:
                print(f"Erro ao buscar notas fiscais: {e}")
                return {
                    'rows': [],
                    'total': 0,
                    'page': page,
                    'per_page': per_page,
                    'pages': 0
                }
            finally:
                conn.close()
        return {
            'rows': [],
            'total': 0,
            'page': page,
            'per_page': per_page,
            'pages': 0
        }
    def populate_default_data(self):
        """Popula dados padrão se necessário"""
        conn = self.create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                
                # Verificar se a tabela tb_tipo_de_recolhimento está vazia
                cursor.execute("SELECT COUNT(*) FROM tb_tipo_de_recolhimento")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    # Adicionar tipos de recolhimento padrão
                    tipos_recolhimento = [
                        ('Recolhimento Normal',),
                    ]
                    
                    cursor.executemany("""
                        INSERT INTO tb_tipo_de_recolhimento (recolhimento)
                        VALUES (?)
                    """, tipos_recolhimento)
                    
                    conn.commit()
                    print(f"{len(tipos_recolhimento)} tipos de recolhimento adicionados com sucesso.")
                    
            except Error as e:
                print(f"Erro ao popular dados padrão: {e}")
            finally:
                conn.close()
    def import_municipios_from_txt(self, filepath):
        """
        Importa municípios de um arquivo TXT

        :param filepath: Caminho para o arquivo de municípios
        :return: Número de municípios importados
        """
        import os
        import chardet

        logging.info(f"Iniciando importação de municípios: {filepath}")

        # Verificar existência do arquivo
        if not os.path.exists(filepath):
            logging.error(f"Arquivo não encontrado: {filepath}")
            return 0

        # Detectar encoding do arquivo
        try:
            with open(filepath, 'rb') as file:
                raw_data = file.read(10000)  # Ler primeiros 10 KB
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']

            logging.info(f"Encoding detectado: {encoding} (Confiança: {confidence * 100:.2f}%)")

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
                logging.error("Não foi possível determinar o formato do arquivo")
                return 0

            logging.info(f"Formato detectado: {formato['tipo']}")

            # Criar ou verificar tabela
            conn = self.create_connection()
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
                logging.error(f"Erro durante a importação: {e}")
                return 0
            finally:
                conn.close()

        except Exception as e:
            logging.error(f"Erro ao processar arquivo: {e}")
            return 0

    def _detectar_formato_arquivo(self, filepath, encodings):
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
                logging.error(f"Erro ao detectar formato com encoding {encoding}: {e}")

        return None

    def _importar_arquivo(self, filepath, formato, conn):
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
                                logging.error(f"Linha {line_num} inválida: {line}")
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
                                logging.error(f"Linha {line_num} inválida: {line}")
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
                            logging.error(
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
                        logging.error(f"Erro ao processar linha {line_num}: {e}")
                        error_count += 1

            logging.info(f"Importação concluída: {imported_count} municípios importados, {error_count} erros")
            return imported_count

        except Exception as e:
            logging.error(f"Erro ao ler arquivo: {e}")
            return imported_count


def update_tomador(self, dados):
    """
    Atualiza um tomador existente no banco de dados
    
    :param dados: Dicionário com os dados do tomador, incluindo o ID
    :return: True se bem-sucedido, False caso contrário
    """
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE tb_tomadores 
                SET razao_social = ?, 
                    cnpj = ?, 
                    inscricao = ?, 
                    usuario = ?
                WHERE id = ?
            """, (
                dados['razao_social'],
                dados['cnpj'],
                dados['inscricao'],
                dados['usuario'],
                dados['id']
            ))
                
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Erro ao atualizar tomador: {e}")
            return False
        finally:
            conn.close()
    return False

def delete_tomador(self, tomador_id):
    """
    Exclui um tomador do banco de dados
    
    :param tomador_id: ID do tomador a ser excluído
    :return: True se bem-sucedido, False caso contrário
    """
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Verificar se há notas fiscais associadas
            cursor.execute("SELECT COUNT(*) FROM tb_notas_fiscais WHERE tomador_id = ?", (tomador_id,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"Não é possível excluir o tomador: existem {count} notas fiscais associadas")
                return False
                
            # Excluir tomador
            cursor.execute("DELETE FROM tb_tomadores WHERE id = ?", (tomador_id,))
            conn.commit()
            
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Erro ao excluir tomador: {e}")
            return False
        finally:
            conn.close()
    return False

def export_to_excel(self, query, filename="export.xlsx"):
        """Exporta dados do banco de dados para um arquivo Excel"""
        try:
            with self.app.app_context():
                db = self.get_db()
                df = pd.read_sql_query(query, db)

                # Cria um buffer na memória para o arquivo Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Dados')

                # Prepara a resposta para download
                output.seek(0)
                response = make_response(output.getvalue())
                response.headers["Content-Disposition"] = f"attachment; filename={filename}"
                response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                self.logger.info(f"Dados exportados para Excel com sucesso: {filename}")
                return response

        except Exception as e:
            self.logger.error(f"Erro ao exportar dados para Excel: {str(e)}")
            raise


def insert_tomador(self, dados):
    """
    Insere um novo tomador no banco de dados
    
    :param dados: Dicionário com dados do tomador
    :return: ID do tomador inserido ou None se falhar
    """
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Remover caracteres não numéricos do CNPJ
            cnpj = ''.join(filter(str.isdigit, dados['cnpj']))
            
            # Validar campos obrigatórios
            if not dados.get('razao_social'):
                print("Erro: Razão social é obrigatória")
                return None
            
            if not cnpj or len(cnpj) < 11:
                print("Erro: CNPJ/CPF inválido")
                return None
            
            # Verificar se o tomador já existe pelo CNPJ
            cursor.execute("SELECT id FROM tb_tomadores WHERE cnpj = ?", (cnpj,))
            existing_tomador = cursor.fetchone()
            
            if existing_tomador:
                # Atualizar tomador existente
                cursor.execute("""
                    UPDATE tb_tomadores 
                    SET razao_social = ?, 
                        inscricao = ?, 
                        usuario = ? 
                    WHERE id = ?
                """, (
                    dados['razao_social'], 
                    dados.get('inscricao', ''), 
                    dados.get('usuario', ''),
                    existing_tomador[0]
                ))
                conn.commit()
                print(f"Tomador atualizado: {dados['razao_social']}")
                return existing_tomador[0]
            else:
                # Inserir novo tomador
                cursor.execute("""
                    INSERT INTO tb_tomadores 
                    (razao_social, cnpj, inscricao, usuario) 
                    VALUES (?, ?, ?, ?)
                """, (
                    dados['razao_social'], 
                    cnpj, 
                    dados.get('inscricao', ''), 
                    dados.get('usuario', '')
                ))
                conn.commit()
                tomador_id = cursor.lastrowid
                print(f"Novo tomador inserido: {dados['razao_social']}")
                return tomador_id
        
        except Exception as e:
            print(f"Erro ao inserir/atualizar tomador: {e}")
            conn.rollback()
            return None
        
        finally:
            if conn:
                conn.close()
    
    return None


def export_to_excel(self, filepath=None):
    """
    Exporta todas as notas fiscais para um arquivo Excel
    
    :param filepath: Caminho para salvar o arquivo. Se None, usa um arquivo temporário
    :return: Caminho do arquivo ou objeto de resposta para download
    """
    try:
        # Conectar ao banco de dados
        conn = self.create_connection()
        
        if conn is None:
            logging.error("Não foi possível conectar ao banco de dados")
            return False

        try:
            # Consulta para obter todas as notas fiscais com detalhes completos
            query = """
            SELECT 
                nf.id AS 'Identificador',
                nf.referencia AS 'Referência',
                nf.cnpj AS 'CNPJ',
                f.descricao_fornecedor AS 'Fornecedor',
                nf.tipo_servico AS 'Tipo de Serviço',
                nf.base_calculo AS 'Base de Cálculo',
                nf.numero_nf AS 'Número NF',
                nf.dt_emissao AS 'Data de Emissão',
                nf.dt_pagamento AS 'Data de Pagamento',
                nf.aliquota AS 'Alíquota',
                nf.valor_nf AS 'Valor NF',
                nf.recolhimento AS 'Recolhimento',
                nf.recibo AS 'Recibo',
                nf.inscricao_municipal AS 'Inscrição Municipal',
                CASE WHEN nf.cadastrado_goiania = 1 THEN 'Sim' ELSE 'Não' END AS 'Cadastrado em Goiânia',
                CASE WHEN nf.fora_pais = 1 THEN 'Sim' ELSE 'Não' END AS 'Fora do País'
            FROM tb_notas_fiscais nf
            LEFT JOIN tb_fornecedores f ON nf.fornecedor_id = f.id
            ORDER BY nf.dt_emissao DESC
            """
            
            # Ler dados para um DataFrame
            df = pd.read_sql_query(query, conn)
            
            # Criar arquivo temporário se não for fornecido
            close_temp = False
            if filepath is None:
                # Cria um arquivo temporário
                temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                filepath = temp.name
                close_temp = True
                temp.close()
            
            # Exportar para Excel
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            logging.info(f"Notas fiscais exportadas com sucesso para {filepath}")
            
            return filepath
        
        except Exception as e:
            logging.error(f"Erro ao exportar notas fiscais: {e}")
            return False
        
        finally:
            if conn:
                conn.close()
    
    except Exception as e:
        logging.error(f"Erro geral na exportação: {e}")
        return False

def export_to_excel_por_tomador(self, tomador_id, filepath=None):
    """
    Exporta notas fiscais de um tomador específico para Excel
    
    :param tomador_id: ID do tomador
    :param filepath: Caminho para salvar o arquivo. Se None, usa um arquivo temporário
    :return: Caminho do arquivo ou False se falhar
    """
    try:
        # Conectar ao banco de dados
        conn = self.create_connection()
        
        if conn is None:
            logging.error("Não foi possível conectar ao banco de dados")
            return False

        try:
            # Consulta para obter notas fiscais do tomador
            query = """
            SELECT 
                nf.id AS 'Identificador',
                nf.referencia AS 'Referência',
                nf.cnpj AS 'CNPJ',
                f.descricao_fornecedor AS 'Fornecedor',
                nf.tipo_servico AS 'Tipo de Serviço',
                nf.base_calculo AS 'Base de Cálculo',
                nf.numero_nf AS 'Número NF',
                nf.dt_emissao AS 'Data de Emissão',
                nf.dt_pagamento AS 'Data de Pagamento',
                nf.aliquota AS 'Alíquota',
                nf.valor_nf AS 'Valor NF',
                nf.recolhimento AS 'Recolhimento',
                nf.recibo AS 'Recibo',
                nf.inscricao_municipal AS 'Inscrição Municipal',
                CASE WHEN nf.cadastrado_goiania = 1 THEN 'Sim' ELSE 'Não' END AS 'Cadastrado em Goiânia',
                CASE WHEN nf.fora_pais = 1 THEN 'Sim' ELSE 'Não' END AS 'Fora do País'
            FROM tb_notas_fiscais nf
            LEFT JOIN tb_fornecedores f ON nf.fornecedor_id = f.id
            LEFT JOIN tb_tomadores t ON nf.tomador_id = t.id
            WHERE t.id = ?
            ORDER BY nf.dt_emissao DESC
            """
            
            # Ler dados para um DataFrame
            df = pd.read_sql_query(query, conn, params=(tomador_id,))
            
            # Criar arquivo temporário se não for fornecido
            close_temp = False
            if filepath is None:
                # Cria um arquivo temporário
                temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                filepath = temp.name
                close_temp = True
                temp.close()
            
            # Exportar para Excel
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            logging.info(f"Notas fiscais do tomador {tomador_id} exportadas com sucesso para {filepath}")
            
            return filepath
        
        except Exception as e:
            logging.error(f"Erro ao exportar notas fiscais do tomador: {e}")
            return False
        
        finally:
            if conn:
                conn.close()
    
    except Exception as e:
        logging.error(f"Erro geral na exportação: {e}")
        return False

def limpar_notas_fiscais(self):
    """
    Limpa todas as notas fiscais da tabela
    
    :return: True se a limpeza for bem-sucedida, False caso contrário
    """
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Excluir todas as notas fiscais
            cursor.execute("DELETE FROM tb_notas_fiscais")
            
            # Commit da transação
            conn.commit()
            
            logging.info("Todas as notas fiscais foram excluídas")
            return True
        
        except Exception as e:
            logging.error(f"Erro ao limpar notas fiscais: {e}")
            conn.rollback()
            return False
        
        finally:
            if conn:
                conn.close()
    
    return False


def validate_cnpj(self, cnpj):
    """
    Valida o CNPJ de acordo com as regras oficiais brasileiras
    
    :param cnpj: CNPJ a ser validado (aceita formatado ou não)
    :return: bool
    """
    # Remover caracteres não numéricos
    cnpj = ''.join(filter(str.isdigit, str(cnpj)))
    
    # Verificar se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verificar se todos os dígitos são iguais
    if len(set(cnpj)) == 1:
        return False
    
    # Calcular primeiro dígito verificador
    soma = 0
    peso = 5
    for i in range(12):
        soma += int(cnpj[i]) * peso
        peso = peso - 1 if peso > 2 else 9
    
    digito1 = 0 if soma % 11 < 2 else 11 - (soma % 11)
    if int(cnpj[12]) != digito1:
        return False
    
    # Calcular segundo dígito verificador
    soma = 0
    peso = 6
    for i in range(13):
        soma += int(cnpj[i]) * peso
        peso = peso - 1 if peso > 2 else 9
    
    digito2 = 0 if soma % 11 < 2 else 11 - (soma % 11)
    
    return int(cnpj[13]) == digito2

def format_cnpj(self, cnpj):
    """
    Formata o CNPJ com pontuação
    
    :param cnpj: CNPJ a ser formatado (apenas números)
    :return: CNPJ formatado
    """
    # Remover caracteres não numéricos
    cnpj = ''.join(filter(str.isdigit, str(cnpj)))
    
    # Verificar se o CNPJ tem 14 dígitos
    if len(cnpj) != 14:
        return cnpj
    
    # Formatar CNPJ
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

def clean_cnpj(self, cnpj):
    """
    Remove todos os caracteres não numéricos do CNPJ
    
    :param cnpj: CNPJ a ser limpo
    :return: CNPJ com apenas números
    """
    return ''.join(filter(str.isdigit, str(cnpj)))

def get_fornecedor_by_cnpj(self, cnpj):
    """
    Busca um fornecedor pelo CNPJ
    
    :param cnpj: CNPJ do fornecedor
    :return: Dados do fornecedor ou None
    """
    # Limpar CNPJ
    cnpj_limpo = self.clean_cnpj(cnpj)
    
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT descricao_fornecedor, uf, municipio, cod_municipio,
                       cadastrado_goiania, fora_pais
                FROM tb_fornecedores 
                WHERE REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') = ?
            """, (cnpj_limpo,))
            
            fornecedor = cursor.fetchone()
            return fornecedor
        
        except Exception as e:
            print(f"Erro ao buscar fornecedor por CNPJ: {e}")
            return None
        
        finally:
            if conn:
                conn.close()
    
    return None

def insert_fornecedor(self, cnpj, descricao, uf, municipio, cod_municipio, fora_pais=False, cadastrado_goiania=False):
    """
    Insere ou atualiza um fornecedor
    
    :param cnpj: CNPJ do fornecedor
    :param descricao: Nome/Descrição do fornecedor
    :param uf: UF do fornecedor
    :param municipio: Município do fornecedor
    :param cod_municipio: Código do município
    :param fora_pais: Se o fornecedor está fora do país
    :param cadastrado_goiania: Se o fornecedor está cadastrado em Goiânia
    :return: ID do fornecedor
    """
    # Validar CNPJ
    if not self.validate_cnpj(cnpj):
        print("CNPJ inválido")
        return None

    # Limpar CNPJ
    cnpj_limpo = self.clean_cnpj(cnpj)
    
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Verificar se o fornecedor já existe
            cursor.execute("""
                SELECT id FROM tb_fornecedores 
                WHERE REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') = ?
            """, (cnpj_limpo,))
            
            existing_fornecedor = cursor.fetchone()
            
            if existing_fornecedor:
                # Atualizar fornecedor existente
                cursor.execute("""
                    UPDATE tb_fornecedores 
                    SET descricao_fornecedor = ?, 
                        uf = ?, 
                        municipio = ?, 
                        cod_municipio = ?,
                        cadastrado_goiania = ?,
                        fora_pais = ?
                    WHERE id = ?
                """, (
                    descricao, 
                    uf, 
                    municipio, 
                    cod_municipio, 
                    cadastrado_goiania,
                    fora_pais,
                    existing_fornecedor[0]
                ))
                conn.commit()
                return existing_fornecedor[0]
            else:
                # Inserir novo fornecedor
                cursor.execute("""
                    INSERT INTO tb_fornecedores 
                    (descricao_fornecedor, uf, municipio, cod_municipio, 
                     cadastrado_goiania, fora_pais, cnpj) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    descricao, 
                    uf, 
                    municipio, 
                    cod_municipio, 
                    cadastrado_goiania,
                    fora_pais,
                    cnpj_limpo
                ))
                conn.commit()
                return cursor.lastrowid
        
        except Exception as e:
            print(f"Erro ao inserir/atualizar fornecedor: {e}")
            conn.rollback()
            return None
        
        finally:
            if conn:
                conn.close()
    
    return None


def get_notas_fiscais_paginadas(self, page=1, per_page=10, search=None):
    """Retorna notas fiscais paginadas com busca opcional"""
    # Primeiro, garantir que as tabelas estejam criadas
    self.diagnosticar_e_corrigir_tabelas()
    
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Criar tabela de tipos de recolhimento se não existir
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_tipo_de_recolhimento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recolhimento TEXT NOT NULL UNIQUE
                )
            """)
            
            # Inserir tipos de recolhimento padrão se não existirem
            cursor.execute("SELECT COUNT(*) FROM tb_tipo_de_recolhimento")
            count = cursor.fetchone()[0]
            
            if count == 0:
                tipos_recolhimento = [
                    ('Recolhimento Normal',),
                ]
                
                cursor.executemany("""
                    INSERT OR IGNORE INTO tb_tipo_de_recolhimento (recolhimento)
                    VALUES (?)
                """, tipos_recolhimento)
            
            # Query principal
            query = """
                SELECT
                    nf.id,
                    nf.referencia,
                    nf.cnpj,
                    f.descricao_fornecedor,
                    nf.tipo_servico,
                    nf.base_calculo,
                    nf.numero_nf,
                    nf.dt_emissao,
                    nf.dt_pagamento,
                    nf.aliquota,
                    nf.valor_nf,
                    COALESCE(nf.recolhimento, 'Recolhimento Normal') as recolhimento
                FROM tb_notas_fiscais nf
                LEFT JOIN tb_fornecedores f ON nf.fornecedor_id = f.id
            """

            params = []
            if search:
                query += """
                WHERE nf.cnpj LIKE ? OR
                    f.descricao_fornecedor LIKE ? OR
                    nf.numero_nf LIKE ?
                """
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])

            query += " ORDER BY nf.dt_emissao DESC"

            count_query = f"SELECT COUNT(*) FROM ({query}) as count_query"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            query += " LIMIT ? OFFSET ?"
            offset = (page - 1) * per_page
            params.extend([per_page, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return {
                'rows': rows,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }

        except Error as e:
            print(f"Erro ao buscar notas fiscais: {e}")
            return {
                'rows': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'pages': 0
            }
        finally:
            if conn:
                conn.close()
    
    return {
        'rows': [],
        'total': 0,
        'page': page,
        'per_page': per_page,
        'pages': 0
    }

def get_all_recolhimentos(self):
    """Obtém todos os tipos de recolhimento"""
    # Primeiro, garantir que a tabela exista
    self.criar_tabela_tipo_de_recolhimento()
    
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Buscar tipos de recolhimento
            cursor.execute("SELECT recolhimento FROM tb_tipo_de_recolhimento ORDER BY recolhimento")
            tipos = [row[0] for row in cursor.fetchall()]
            
            # Se não houver tipos, retornar lista padrão
            if not tipos:
                tipos = [
                    'Recolhimento',
                ]
            
            return tipos
        
        except Error as e:
            print(f"Erro ao obter tipos de recolhimento: {e}")
            # Retornar lista padrão em caso de erro
            return [
                'Recolhimento',
            ]
        
        finally:
            if conn:
                conn.close()
    
    # Retornar lista padrão se não conseguir conectar ao banco
    return [
        'Recolhimento',
    ]


def import_municipios_from_txt(self, filepath):
    """
    Importa municípios de um arquivo TXT com suporte robusto a múltiplos formatos
    
    :param filepath: Caminho para o arquivo de municípios
    :return: Tuple(bool, str) - Sucesso da operação e mensagem de resultado
    """
    import os
    import logging
    import chardet
    import re
    
    # Configurar logging básico
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'municipios_import.log'), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Verificar existência do arquivo
    if not os.path.exists(filepath):
        msg = f"Arquivo não encontrado: {filepath}"
        logger.error(msg)
        return False, msg
    
    # Analisar o arquivo antes de importar
    try:
        # Detectar encoding do arquivo
        with open(filepath, 'rb') as file:
            raw_data = file.read(10000)  # Ler primeiros 10 KB
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
        
        # Se a confiança for muito baixa, registrar aviso
        if confidence < 0.7:
            logger.warning(f"Baixa confiança na detecção de encoding: {confidence * 100:.2f}%")
        
        logger.info(f"Encoding detectado: {encoding} (Confiança: {confidence * 100:.2f}%)")
        
        # Lista de encodings para tentar
        encodings_to_try = [encoding, 'utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        encodings_to_try = list(dict.fromkeys(encodings_to_try))  # Remover duplicatas
        
        # Tentar identificar o formato do arquivo
        formato_detectado = None
        amostra_linhas = []
        
        for try_encoding in encodings_to_try:
            try:
                with open(filepath, 'r', encoding=try_encoding) as file:
                    # Ler algumas linhas de amostra
                    amostra_linhas = []
                    for _ in range(5):
                        linha = file.readline().strip()
                        if linha:  # Ignorar linhas vazias
                            amostra_linhas.append(linha)
                        if len(amostra_linhas) >= 5:
                            break
                
                if amostra_linhas:
                    logger.info(f"Leitura bem-sucedida com encoding: {try_encoding}")
                    encoding = try_encoding
                    break
            except UnicodeDecodeError:
                logger.warning(f"Falha ao decodificar com encoding {try_encoding}")
                continue
            except Exception as e:
                logger.error(f"Erro ao ler arquivo com encoding {try_encoding}: {str(e)}")
                continue
        
        # Verificar formato do arquivo baseado nas linhas de amostra
        if amostra_linhas:
            linha_exemplo = amostra_linhas[0]
            
            if ';' in linha_exemplo:
                formato_detectado = "SEPARADOR_PONTO_VIRGULA"
                logger.info("Formato detectado: Separado por ponto e vírgula (;)")
            elif ',' in linha_exemplo and not "Código=" in linha_exemplo:
                formato_detectado = "SEPARADOR_VIRGULA" 
                logger.info("Formato detectado: Separado por vírgula (,)")
            elif "Código=" in linha_exemplo and "Município=" in linha_exemplo and "UF=" in linha_exemplo:
                formato_detectado = "FORMATO_PROCESSANDO"
                logger.info("Formato detectado: 'Processando: Código=X, Município=Y, UF=Z'")
            else:
                formato_detectado = "DESCONHECIDO"
                logger.warning(f"Formato desconhecido. Linha exemplo: {linha_exemplo}")
        else:
            return False, "Não foi possível ler o arquivo com nenhum encoding conhecido"
            
        # Preparar para importação
        conn = self.create_connection()
        if conn is None:
            return False, "Não foi possível conectar ao banco de dados"
        
        try:
            cursor = conn.cursor()
            
            # Verificar se a tabela existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='tb_municipios'
            """)
            
            if not cursor.fetchone():
                # Criar tabela se não existir
                logger.info("Criando tabela tb_municipios")
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
            logger.info("Tabela tb_municipios limpa para nova importação")
            
            # Contadores
            total_lines = 0
            imported_count = 0
            error_count = 0
            
            # Processar o arquivo
            with open(filepath, 'r', encoding=encoding) as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:  # Pular linhas vazias
                        continue
                        
                    total_lines += 1
                    
                    try:
                        # Extrair dados conforme o formato detectado
                        cod_municipio = None
                        nome_municipio = None
                        uf = None
                        
                        if formato_detectado == "SEPARADOR_PONTO_VIRGULA":
                            parts = [part.strip() for part in line.split(';')]
                            if len(parts) >= 3:
                                cod_municipio, nome_municipio, uf = parts[0], parts[1], parts[2]
                                
                        elif formato_detectado == "SEPARADOR_VIRGULA":
                            parts = [part.strip() for part in line.split(',')]
                            if len(parts) >= 3:
                                uf, cod_municipio, nome_municipio = parts[0], parts[1], parts[2]
                                
                        elif formato_detectado == "FORMATO_PROCESSANDO":
                            # Remover prefixo se existir
                            if line.startswith("Processando: "):
                                line = line.replace("Processando: ", "")
                            
                            # Extrair partes - padrão: "Código=X, Município=Y, UF=Z"
                            if "Código=" in line and "," in line:
                                cod_municipio = line.split("Código=")[1].split(",")[0].strip()
                            
                            if "Município=" in line and "," in line:
                                nome_municipio = line.split("Município=")[1].split(",")[0].strip()
                            
                            if "UF=" in line:
                                uf = line.split("UF=")[1].strip()
                                
                        else:
                            # Tentar formato genérico como último recurso
                            parts = None
                            if ';' in line:
                                parts = [part.strip() for part in line.split(';')]
                            elif ',' in line:
                                parts = [part.strip() for part in line.split(',')]
                                
                            if parts and len(parts) >= 3:
                                # Tentar detectar qual parte é qual baseado em padrões
                                for i, part in enumerate(parts):
                                    if len(part) == 2 and part.isalpha():
                                        uf = part
                                    elif part.isdigit() or (part.startswith('0') and part[1:].isdigit()):
                                        cod_municipio = part
                                    else:
                                        nome_municipio = part
                                        
                                # Se não conseguiu identificar, usar posição padrão
                                if not all([cod_municipio, nome_municipio, uf]):
                                    if len(parts) >= 3:
                                        cod_municipio = parts[0]
                                        nome_municipio = parts[1]
                                        uf = parts[2]
                        
                        # Validar dados extraídos
                        if not all([cod_municipio, nome_municipio, uf]):
                            logger.warning(f"Dados incompletos na linha {line_num}: {line}")
                            error_count += 1
                            continue
                        
                        # Normalizar dados
                        uf = uf.upper()
                        nome_municipio = nome_municipio.strip().upper()
                        cod_municipio = cod_municipio.strip()
                        
                        # Validar UF
                        if len(uf) != 2 or not uf.isalpha():
                            logger.warning(f"UF inválida na linha {line_num}: {uf}")
                            error_count += 1
                            continue
                        
                        # Inserir no banco de dados
                        cursor.execute("""
                            INSERT OR REPLACE INTO tb_municipios 
                            (uf, cod_municipio, nome_municipio) 
                            VALUES (?, ?, ?)
                        """, (uf, cod_municipio, nome_municipio))
                        
                        imported_count += 1
                        
                        # Log a cada 100 registros para acompanhamento
                        if imported_count % 100 == 0:
                            logger.info(f"Progresso: {imported_count} municípios importados")
                        
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Erro na linha {line_num}: {str(e)}")
                        # Continuar com a próxima linha
            
            # Commit das alterações
            conn.commit()
            
            # Relatório final
            msg = (f"Importação concluída!\n"
                   f"- Total de linhas: {total_lines}\n"
                   f"- Municípios importados: {imported_count}\n"
                   f"- Erros: {error_count}")
            
            logger.info(msg)
            
            # Retornar resultado
            if imported_count > 0:
                return True, msg
            else:
                return False, "Nenhum município foi importado. Verifique o formato do arquivo."
            
        except Exception as e:
            conn.rollback()
            msg = f"Erro durante a importação: {str(e)}"
            logger.error(msg)
            return False, msg
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        msg = f"Erro ao processar arquivo: {str(e)}"
        logger.error(msg)
        return False, msg
    

def get_municipio_by_codigo(self, codigo):
    """
    Obtém dados de um município pelo código
    
    :param codigo: Código do município
    :return: Tupla (nome_municipio, uf, cod_municipio) ou None se não encontrado
    """
    # Limpar código (remover caracteres não numéricos)
    codigo_numerico = ''.join(filter(str.isdigit, str(codigo)))
    
    if not codigo_numerico:
        return None
    
    conn = self.create_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Buscar município pelo código
        cursor.execute("""
            SELECT nome_municipio, uf, cod_municipio
            FROM tb_municipios
            WHERE cod_municipio = ?
        """, (codigo_numerico,))
        
        municipio = cursor.fetchone()
        return municipio
    
    except Exception as e:
        print(f"Erro ao buscar município por código: {e}")
        return None
    
    finally:
        if conn:
            conn.close()


