from datetime import datetime
import os
import sqlite3
import tempfile
from flask import Flask, render_template, request, redirect, send_file, url_for, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import FileField, SelectField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from database import DatabaseManager
import logging

from form import NotaFiscalForm, TomadorForm
import form
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)
static_folder='static',  # Specify the static folder
static_url_path='/static'
app.secret_key = 'kbl-accounting-rest-goiania'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inicializar o gerenciador de banco de dados
db = DatabaseManager()
# Isso precisa estar ligado dinamicamente

count = db.import_municipios_from_txt('municipios.txt')
print(f"{count} municípios importados")

# Consultar municípios de uma UF
municipios_go = db.get_municipios_by_uf('GO')
for nome, codigo in municipios_go:
    print(f"{nome}: {codigo}")


@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/')
def index():
    """Rota da página inicial"""
    logger.info("Acessando a página inicial")
    return render_template('index.html')

class ImportarMunicipiosForm(FlaskForm):
    arquivo = FileField('Arquivo TXT', validators=[DataRequired()])
    submit = SubmitField('Importar Municípios')

@app.route('/importar-municipios', methods=['GET', 'POST'])
def importar_municipios():
    form = ImportarMunicipiosForm()
    resultado = None
    
    if form.validate_on_submit():
        # Save the uploaded file
        f = form.arquivo.data
        filename = secure_filename(f.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(filepath)
        
        # Log file details
        logger.info(f"Arquivo recebido: {filename}")
        
        try:
            # Import municipalities from the file
            count = db.import_municipios_from_txt(filepath)
            
            if count > 0:
                flash(f'{count} municípios importados com sucesso!', 'success')
                resultado = {
                    'status': 'success',
                    'message': f'{count} municípios importados com sucesso!',
                    'count': count
                }
            else:
                flash('Nenhum município foi importado. Verifique o formato do arquivo.', 'warning')
                resultado = {
                    'status': 'warning',
                    'message': 'Nenhum município foi importado. Verifique o formato do arquivo.'
                }
                
        except Exception as e:
            error_msg = f"Erro durante a importação: {str(e)}"
            flash(error_msg, 'danger')
            logger.error(error_msg)
            resultado = {
                'status': 'error',
                'message': error_msg
            }
    logger.info("Renderizando a página de importação de municípios")
    logger.info(f"Resultado da importação: {resultado}")        
    return render_template('importar_municipios.html', form=form, resultado=resultado)

# API endpoint for AJAX import
@app.route('/api/importar-municipios', methods=['POST'])
def api_importar_municipios():
    if 'arquivo' not in request.files:
        return jsonify({'status': 'error', 'message': 'Nenhum arquivo enviado'})
    
    file = request.files['arquivo']
    logger.info(f"Arquivo recebido: {file.filename}")
    if file.filename == '':
        logger.error
        return jsonify({'status': 'error', 'message': 'Nenhum arquivo selecionado'})
        
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logger.info(f"Arquivo salvo em: {filepath}")
        # Import municipalities
        count = db.import_municipios_from_txt(filepath)
        
        if count > 0:
            logger.info(f"{count} municípios importados com sucesso!")
            return jsonify({
                'status': 'success',
                'message': f'{count} municípios importados com sucesso!',
                'count': count
            })
        else:
            logger.warning('Nenhum município foi importado. Verifique o formato do arquivo.')
            return jsonify({
                'status': 'warning',
                'message': 'Nenhum município foi importado. Verifique o formato do arquivo.'
            })
            
    except Exception as e:
        error_msg = f"Erro durante a importação: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            'status': 'error',
            'message': error_msg
        })
@app.route('/api/ufs', methods=['GET'])
def api_ufs():
    """API para listar todas as UFs disponíveis"""
    try:
        # Conexão direta ao banco
        conn = sqlite3.connect(db.db_file)
        cursor = conn.cursor()
        
        # Buscar UFs
        cursor.execute("SELECT DISTINCT uf FROM tb_municipios ORDER BY uf")
        ufs = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        logger.info(f"API UFs: retornando {len(ufs)} UFs")
        
        return jsonify({
            'status': 'success',
            'data': ufs
        })
    except Exception as e:
        logger.error(f"Erro ao listar UFs: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/municipios/<uf>', methods=['GET'])
def api_municipios(uf):
    """API para listar municípios de uma UF específica"""
    try:
        # Validar UF
        if not uf or len(uf) != 2:
            logger.warning(f"UF inválida: {uf}")
            return jsonify({
                'status': 'error',
                'message': 'UF inválida'
            }), 400
            
        # Conexão direta ao banco
        conn = sqlite3.connect(db.db_file)
        cursor = conn.cursor()
        
        # Buscar municípios
        cursor.execute("""
            SELECT nome_municipio, cod_municipio 
            FROM tb_municipios 
            WHERE uf = ? 
            ORDER BY nome_municipio
        """, (uf.upper(),))
        
        municipios_data = cursor.fetchall()
        
        # Formatar como JSON
        municipios = []
        for nome, codigo in municipios_data:
            municipios.append({
                'nome': nome,
                'codigo': codigo
            })
        
        conn.close()
        logger.info(f"API Municípios: retornando {len(municipios)} municípios para UF {uf}")
        
        return jsonify({
            'status': 'success',
            'data': municipios
        })
    except Exception as e:
        logger.error(f"Erro ao listar municípios de {uf}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
def verificar_municipios_db():
    """Verifica o estado dos municípios no banco de dados"""
    try:
        conn = sqlite3.connect(db.db_file)
        cursor = conn.cursor()
        
        # Verificar tabela
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='tb_municipios'")
        tabela_existe = cursor.fetchone()[0] > 0
        
        if not tabela_existe:
            print("Tabela tb_municipios não existe!")
            return False
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM tb_municipios")
        total = cursor.fetchone()[0]
        print(f"Total de municípios: {total}")
        
        # Verificar distribuição por UF
        if total > 0:
            cursor.execute("SELECT uf, COUNT(*) FROM tb_municipios GROUP BY uf ORDER BY uf")
            for uf, count in cursor.fetchall():
                print(f"UF {uf}: {count} municípios")
        
        conn.close()
        return total > 0
    except Exception as e:
        print(f"Erro ao verificar municípios: {e}")
        return False
    
@app.route('/api/municipio/<codigo>', methods=['GET'])
def api_municipio_por_codigo(codigo):
    """API para obter dados de um município pelo código"""
    try:
        # Limpar código
        codigo_numerico = ''.join(filter(str.isdigit, codigo))
        
        if not codigo_numerico:
            logger.warning(f"Código inválido: {codigo}")
            return jsonify({
                'status': 'error',
                'message': 'Código inválido'
            }), 400
            
        # Conexão direta ao banco
        conn = sqlite3.connect(db.db_file)
        cursor = conn.cursor()
        
        # Buscar município
        cursor.execute("""
            SELECT nome_municipio, uf, cod_municipio 
            FROM tb_municipios 
            WHERE cod_municipio = ?
        """, (codigo_numerico,))
        
        municipio = cursor.fetchone()
        conn.close()
        
        if not municipio:
            logger.warning(f"Município com código {codigo} não encontrado")
            return jsonify({
                'status': 'error',
                'message': 'Município não encontrado'
            }), 404
        
        logger.info(f"API Município: retornando {municipio[0]} ({municipio[1]})")
        
        return jsonify({
            'status': 'success',
            'data': {
                'nome': municipio[0],  # nome_municipio
                'uf': municipio[1],    # uf
                'codigo': municipio[2] # cod_municipio
            }
        })
    except Exception as e:
        logger.error(f"Erro ao buscar município com código {codigo}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500    

def criar_tabela_municipios(self):
    """Cria a tabela de municípios se não existir"""
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Criar tabela
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tb_municipios (
                uf TEXT,
                cod_municipio TEXT,
                nome_municipio TEXT,
                PRIMARY KEY (uf, cod_municipio)
            )
            ''')
            
            conn.commit()
            logging.info("Tabela tb_municipios criada com sucesso")
            return True
        except Exception as e:
            logging.error(f"Erro ao criar tabela tb_municipios: {e}")
            return False
        finally:
            if conn:
                conn.close()
    return False

def limpar_tabela_municipios(self):
    """Limpa todos os dados da tabela de municípios"""
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tb_municipios")
            conn.commit()
            logging.info("Tabela tb_municipios limpa com sucesso")
            return True
        except Exception as e:
            logging.error(f"Erro ao limpar tabela tb_municipios: {e}")
            return False
        finally:
            if conn:
                conn.close()
    return False

def inserir_municipio(self, uf, cod_municipio, nome_municipio):
    """Insere um município no banco de dados"""
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tb_municipios (uf, cod_municipio, nome_municipio)
                VALUES (?, ?, ?)
            """, (uf.upper(), cod_municipio, nome_municipio.upper()))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Erro ao inserir município: {e}")
            return False
        finally:
            if conn:
                conn.close()
    return False

def contar_municipios(self, uf=None):
    """Conta municípios no banco, opcionalmente filtrados por UF"""
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            if uf:
                cursor.execute("SELECT COUNT(*) FROM tb_municipios WHERE uf = ?", (uf.upper(),))
            else:
                cursor.execute("SELECT COUNT(*) FROM tb_municipios")
                
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logging.error(f"Erro ao contar municípios: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    return 0

def exportar_municipios_sql(self, uf=None, limit=0):
    """Exporta municípios como script SQL"""
    conn = self.create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Construir query
            query = """
                SELECT uf, cod_municipio, nome_municipio 
                FROM tb_municipios
            """
            
            params = []
            if uf:
                query += " WHERE uf = ?"
                params.append(uf.upper())
            
            query += " ORDER BY uf, nome_municipio"
            
            if limit > 0:
                query += " LIMIT ?"
                params.append(limit)
            
            # Executar query
            cursor.execute(query, params)
            municipios = cursor.fetchall()
            
            # Gerar SQL
            sql = "-- Script SQL para importação de municípios\n"
            sql += f"-- Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            sql += f"-- Total de municípios: {len(municipios)}\n\n"
            
            # CREATE TABLE
            sql += "CREATE TABLE IF NOT EXISTS tb_municipios (\n"
            sql += "    uf TEXT,\n"
            sql += "    cod_municipio TEXT,\n"
            sql += "    nome_municipio TEXT,\n"
            sql += "    PRIMARY KEY (uf, cod_municipio)\n"
            sql += ");\n\n"
            
            # BEGIN TRANSACTION
            sql += "BEGIN TRANSACTION;\n\n"
            
            # INSERT OR REPLACE
            for uf, cod, nome in municipios:
                # Escapar aspas simples
                nome_escaped = nome.replace("'", "''") if nome else ""
                sql += f"INSERT OR REPLACE INTO tb_municipios (uf, cod_municipio, nome_municipio) VALUES ('{uf}', '{cod}', '{nome_escaped}');\n"
            
            # COMMIT
            sql += "\nCOMMIT;\n"
            
            return sql
        except Exception as e:
            logging.error(f"Erro ao exportar SQL: {e}")
            return f"-- Erro ao exportar: {e}"
        finally:
            if conn:
                conn.close()
    return "-- Erro: Não foi possível conectar ao banco"

@app.route('/notas')
def listar_notas():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    result = db.get_notas_fiscais_paginadas(page=page, search=search)
    return render_template('notas/index.html', notas=result['rows'], )


@app.route('/notas/novo', methods=['GET', 'POST'])
def nova_nota():
    """Rota para criar uma nova nota fiscal"""
    form = NotaFiscalForm()
    form.uf.choices = db.get_all_ufs()
    form.tipo_servico.choices = db.get_all_tipos_servico()
    form.base_calculo.choices = db.get_all_bases_calculo()
    form.recolhimento.choices = db.get_all_recolhimentos()

    if form.validate_on_submit():
        try:
            # Processar formulário
            cnpj = form.cnpj.data
            fornecedor = form.fornecedor.data
            uf = form.uf.data
            municipio = form.municipio.data
            cod_municipio = form.cod_municipio.data
            fora_pais = form.fora_pais.data
            cadastrado_goiania = form.cadastrado_goiania.data

            # Inserir fornecedor
            fornecedor_id = db.insert_fornecedor(
                cnpj, fornecedor, uf, municipio, cod_municipio, fora_pais, cadastrado_goiania
            )

            if fornecedor_id is None:
                flash("Erro ao salvar fornecedor", "danger")
                return redirect(url_for('nova_nota'))

            # Preparar dados da nota fiscal
            nota_fiscal_data = {
                "referencia": form.referencia.data,
                "CNPJ": cnpj,
                "Fornecedor_ID": fornecedor_id,
                "Inscricao Municipal": form.inscricao_municipal.data,
                "Tipo de Servico": form.tipo_servico.data,
                "Base de Calculo": form.base_calculo.data,
                "Nº NF": form.num_nf.data,
                "Dt. Emissao": form.dt_emissao.data,
                "Dt. Pagamento": form.dt_pagamento.data,
                "Aliquota": float(form.aliquota.data),
                "Valor NF": float(form.valor_nf.data),
                "Recolhimento": form.recolhimento.data,
                "RECIBO": form.recibo.data,
                "UF": uf,
                "Municipio": municipio,
                "Codigo Municipio": cod_municipio,
                "cadastrado_goiania": cadastrado_goiania,
                "fora_pais": fora_pais,
            }

            # Inserir nota fiscal
            db.insert_nota_fiscal(nota_fiscal_data)
            flash("Nota fiscal cadastrada com sucesso!", "success")
            logger.info(f"Nota fiscal cadastrada: {nota_fiscal_data}")
            return redirect(url_for('listar_notas'))

        except Exception as e:
            logger.error(f"Erro ao salvar nota fiscal: {str(e)}")
            flash(f"Erro ao salvar dados: {str(e)}", "danger")

    return render_template('notas/form.html', form=form, title="Nova Nota Fiscal")


@app.route('/notas/editar/<int:id>', methods=['GET', 'POST'])
def editar_nota(id):
    """Rota para editar uma nota fiscal"""
    # Buscar a nota fiscal
    nota = db.get_nota_fiscal_by_id(id)

    if nota is None:
        logger.error(f"Nota fiscal com ID {id} não encontrada")
        flash("Nota fiscal não encontrada", "danger")
        return redirect(url_for('listar_notas'))
    logger.info(f"Nota fiscal encontrada: {nota}")
    form = NotaFiscalForm(obj=nota)
    form.uf.choices = db.get_all_ufs()
    form.tipo_servico.choices = db.get_all_tipos_servico()
    form.base_calculo.choices = db.get_all_bases_calculo()
    form.recolhimento.choices = db.get_all_recolhimentos()

    if form.validate_on_submit():
        try:
            # Processar formulário (similar ao método nova_nota)
            cnpj = form.cnpj.data
            fornecedor = form.fornecedor.data
            uf = form.uf.data
            municipio = form.municipio.data
            cod_municipio = form.cod_municipio.data
            fora_pais = form.fora_pais.data
            cadastrado_goiania = form.cadastrado_goiania.data

            # Inserir/Atualizar fornecedor
            fornecedor_id = db.insert_fornecedor(
                cnpj, fornecedor, uf, municipio, cod_municipio, fora_pais, cadastrado_goiania
            )

            # Preparar dados da nota fiscal
            nota_fiscal_data = {
                "referencia": form.referencia.data,
                "CNPJ": cnpj,
                "Fornecedor_ID": fornecedor_id,
                "Inscricao Municipal": form.inscricao_municipal.data,
                "Tipo de Servico": form.tipo_servico.data,
                "Base de Calculo": form.base_calculo.data,
                "Nº NF": form.num_nf.data,
                "Dt. Emissao": form.dt_emissao.data,
                "Dt. Pagamento": form.dt_pagamento.data,
                "Aliquota": float(form.aliquota.data),
                "Valor NF": float(form.valor_nf.data),
                "Recolhimento": form.recolhimento.data,
                "RECIBO": form.recibo.data,
                "UF": uf,
                "Municipio": municipio,
                "Codigo Municipio": cod_municipio,
                "cadastrado_goiania": cadastrado_goiania,
                "fora_pais": fora_pais,
            }

            # Atualizar nota fiscal
            db.update_nota_fiscal(id, nota_fiscal_data)
            logger.info(f"Nota fiscal atualizada: {nota_fiscal_data}")
            flash("Nota fiscal atualizada com sucesso!", "success")
            return redirect(url_for('listar_notas'))

        except Exception as e:
            logger.error(f"Erro ao atualizar nota fiscal: {str(e)}")
            flash(f"Erro ao atualizar dados: {str(e)}", "danger")
    
    logger.info(f"Renderizando a página de edição da nota fiscal com ID {id}")
    return render_template('notas/form.html', form=form, title="Editar Nota Fiscal")

@app.route('/notas/excluir/<int:id>', methods=['POST'])
def excluir_nota(id):
    """Rota para excluir uma nota fiscal"""
    try:
        if db.delete_nota_fiscal(id):
            logger.info(f"Nota fiscal com ID {id} excluída com sucesso")
            flash("Nota fiscal excluída com sucesso!", "success")
        else:
            logger.error(f"Erro ao excluir nota fiscal com ID {id}")    
            flash("Não foi possível excluir a nota fiscal", "danger")
    except Exception as e:
        logger.error(f"Erro ao excluir nota fiscal com ID {id}: {str(e)}")
        flash(f"Erro ao excluir nota fiscal: {str(e)}", "danger")
    
    logger.info(f"Redirecionando para a lista de notas fiscais após exclusão")
    return redirect(url_for('listar_notas'))

@app.route('/notas/exportar-excel', methods=['GET', 'POST'])
def exportar_excel():
    """Rota para exportar todas as notas fiscais para Excel"""
    if request.method == 'POST':
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp:
            temp_path = temp.name
            logger.info(f"Arquivo temporário criado: {temp_path}")

        try:
            # Exportar todas as notas fiscais para Excel
            if db.export_to_excel(temp_path):
                # Se solicitado, limpar a tabela após exportação
                if request.form.get('limpar_apos_exportar') == 'sim':
                    if db.limpar_notas_fiscais():
                        logger.info("Tabela de notas fiscais foi limpa após exportação.")   
                        flash("Tabela de notas fiscais foi limpa após exportação.", "info")

                # Enviar o arquivo para download
                logger.info(f"Enviando arquivo para download: {temp_path}")
                return send_file(
                    temp_path,
                    as_attachment=True,
                    download_name=f'notas_fiscais_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                )
            else:
                logger.error("Erro ao exportar dados para Excel")   
                flash("Não foi possível exportar os dados", "danger")
        except Exception as e:
            logger.error(f"Erro ao exportar dados: {str(e)}")
            flash(f"Erro ao exportar dados: {str(e)}", "danger")
        finally:
            # Limpar arquivo temporário
            try:
                logger.info(f"Removendo arquivo temporário: {temp_path}")
                os.unlink(temp_path)
            except:
                logger.error(f"Erro ao remover arquivo temporário: {temp_path}")
                pass

                # Para GET, mostrar tela de exportação
                logger.info("Renderizando a página de exportação de notas fiscais") 
                return render_template('notas/exportar.html')
        try:
            # Exportar para Excel
            if db.export_to_excel(temp_path):
                # Se solicitado, limpar a tabela após exportação
                if request.form.get('limpar_apos_exportar') == 'sim':
                    logger.info("Limpando tabela de notas fiscais após exportação")
                    if db.limpar_notas_fiscais():
                        logger.info("Tabela de notas fiscais foi limpa após exportação.")   
                        flash("Tabela de notas fiscais foi limpa após exportação.", "info")

                # Enviar o arquivo para download
                logger.info(f"Enviando arquivo para download: {temp_path}")
                return send_file(
                    temp_path,
                    as_attachment=True,
                    download_name=f'notas_fiscais_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                )
            else:
                logger.error("Erro ao exportar dados para Excel")
                flash("Não foi possível exportar os dados", "danger")
        except Exception as e:
            logger.error(f"Erro ao exportar dados: {str(e)}")
            flash(f"Erro ao exportar dados: {str(e)}", "danger")

    # Para GET, mostrar tela de seleção do tomador
    tomadores = db.get_all_tomadores()
    logger.info(f"Tomadores disponíveis para exportação: {tomadores}")
    return render_template('notas/exportar.html', tomadores=tomadores)

@app.route('/tomadores')
def listar_tomadores():
    """Rota para listar todos os tomadores"""
    tomadores = db.get_all_tomadores()
    logger.info(f"Tomadores encontrados: {tomadores}")
    return render_template('tomadores/index.html', tomadores=tomadores)

@app.route('/tomadores/novo', methods=['GET', 'POST'])
def novo_tomador():
    """Rota para criar um novo tomador"""
    form = TomadorForm()
    if form.validate_on_submit():
        try:
            # Validate CNPJ first
            if not db.validate_cnpj(form.cnpj.data):
                logger
                flash("CNPJ inválido", "danger")
                return render_template('tomadores/form.html', form=form, title="Novo Tomador")

            dados = {
                'razao_social': form.razao_social.data,
                'cnpj': form.cnpj.data,
                'inscricao': form.inscricao.data,
                'usuario': form.usuario.data,
            }

            tomador_id = db.insert_tomador(dados)
            
            if tomador_id:
                logger.info(f"Tomador cadastrado: {dados}")
                flash("Tomador cadastrado com sucesso!", "success")
                return redirect(url_for('listar_tomadores'))
            else:
                logger.error("Erro ao salvar tomador")
                flash("Erro ao salvar tomador", "danger")
        
        except Exception as e:
            logger.error(f"Erro ao salvar tomador: {str(e)}")
            flash(f"Erro ao salvar tomador: {str(e)}", "danger")

    return render_template('tomadores/form.html', form=form, title="Novo Tomador")

@app.route('/tomadores/editar/<int:id>', methods=['GET', 'POST'])
def editar_tomador(id):
    """Rota para editar um tomador"""
    # Buscar todos os tomadores
    tomadores = db.get_all_tomadores()

    # Encontrar o tomador pelo ID
    tomador = next((t for t in tomadores if t[0] == id), None)
    logger.info(f"Tomador encontrado para edição: {tomador}")
    if tomador is None:
        logger.error(f"Tomador com ID {id} não encontrado")
        flash("Tomador não encontrado", "danger")
        return redirect(url_for('listar_tomadores'))

    form = TomadorForm(obj=tomador)

    if form.validate_on_submit():
        try:
            dados = {
                'id': id,
                'razao_social': form.razao_social.data,
                'cnpj': form.cnpj.data,
                'inscricao': form.inscricao.data,
                'usuario': form.usuario.data,
            }

            if db.update_tomador(dados):
                logger.info(f"Tomador atualizado: {dados}")
                flash("Tomador atualizado com sucesso!", "success")
                return redirect(url_for('listar_tomadores'))
            else:
                logger.error("Erro ao atualizar tomador")
                flash("Erro ao atualizar tomador", "danger")
        except Exception as e:
            logger.error(f"Erro ao atualizar tomador: {str(e)}")
            flash(f"Erro ao atualizar tomador: {str(e)}", "danger")

    logger.info("Renderizando a página de edição de tomador")
    return render_template('tomadores/form.html', form=form, title="Editar Tomador")

@app.route('/tomadores/excluir/<int:id>', methods=['POST'])
def excluir_tomador(id):
    """Rota para excluir um tomador"""
    try:
        if db.delete_tomador(id):
            logger.info(f"Tomador com ID {id} excluído com sucesso")    
            flash("Tomador excluído com sucesso!", "success")
        else:
            logger.error(f"Erro ao excluir tomador com ID {id}")    
            flash("Não foi possível excluir o tomador", "danger")
    except Exception as e:
        logger.error(f"Erro ao excluir tomador com ID {id}: {str(e)}")
        flash(f"Erro ao excluir tomador: {str(e)}", "danger")

    logger.info(f"Redirecionando para a lista de tomadores após exclusão")
    return redirect(url_for('listar_tomadores'))

@app.route('/processar_formulario', methods=['POST'])
def processar_formulario():
    # Obter dados do formulário
    municipio = request.form.get('municipio', '')
    
    # Verificar se o município foi selecionado
    if not municipio:
        # Redirecionar de volta com mensagem de erro
        logger.error
        flash('Faltou informar o município. Selecione um da lista antes de continuar.', 'error')
        return redirect(url_for('pagina_formulario'))
    
    # Continuar com o processamento se o município for válido
    # ...resto do código...
    #### verificar qual o resto do código que deve ser executado aqui   
    logger.warning(f"verificar qual o resto do código que deve ser executado aqui") 
    return redirect(url_for('pagina_sucesso'))

@app.route('/api/fornecedor/<cnpj>')
def get_fornecedor(cnpj):
    """API para obter dados do fornecedor por CNPJ"""
    fornecedor = db.get_fornecedor_by_cnpj(cnpj)
    if fornecedor:
        logger.info(f"Fornecedor encontrado: {fornecedor}")
        return jsonify({
            'descricao': fornecedor[0],
            'uf': fornecedor[1],
            'municipio': fornecedor[2],
            'cod_municipio': fornecedor[3]
        })
        
    else:
        logger.warning(f"Fornecedor com CNPJ {cnpj} não encontrado")
        jsonify({
            'status': 'error',
            'message': 'Fornecedor não encontrado'
        })
    return jsonify({})

def print_template_paths(app):
    """Print all possible template search paths"""
    print("Template Search Paths:")
    print("Current Working Directory:", os.getcwd())
    logger.info("Current Working Directory: %s", os.getcwd())
    # Check for common template locations
    potential_paths = [
        os.path.join(os.getcwd(), 'templates'),
        os.path.join(os.path.dirname(__file__), 'templates'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    ]
    
    for path in potential_paths:
        print(f"- {path}")
        print(f"  Exists: {os.path.exists(path)}")
        if os.path.exists(path):
            print("  Contents:")
            try:
                logger.info(f"Contents of {path}:")
                print(os.listdir(path))
            except Exception as e:
                logger.error(f"Error listing contents of {path}: {e}")
                print(f"  Error listing contents: {e}")

@app.route('/api/exportar-notas', methods=['POST'])
def exportar_notas_json():
    """API para exportar dados de notas fiscais como JSON"""
    try:
        # Receber dados do formulário
        data = request.json
        
        # Validar dados (exemplo básico)
        if not data.get('referencia') or not data.get('cnpj'):
            logger.error("Dados incompletos")
            return jsonify({'error': 'Dados incompletos'}), 400
        
        # Processar os dados conforme necessário
        # Exemplo: inserir no banco de dados
        # db.insert_nota_fiscal(data)
        
        # Retornar sucesso
        logger.info("Dados processados com sucesso")
        return jsonify({
            'success': True,
            'message': 'Dados processados com sucesso',
            'data': data
        })
    
    except Exception as e:
        logger
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/nota-fiscal/validar-campos', methods=['POST'])
def validar_campos_nota_fiscal():
    """API para validar campos de nota fiscal em tempo real"""
    try:
        # Obter dados enviados
        campo = request.json.get('campo')
        valor = request.json.get('valor')
        logger.info(f"Validando campo: {campo}, valor: {valor}")
        # Validações específicas
        if campo == 'cnpj':
            # Remover caracteres não numéricos
            cnpj_numerico = ''.join(filter(str.isdigit, valor))
            
            # Verificar tamanho
            if len(cnpj_numerico) != 14:
                logger.warning("CNPJ inválido")
                return jsonify({
                    'valid': False,
                    'message': 'CNPJ deve ter 14 dígitos'
                })
                
            # Aqui poderia ter mais validações, como verificar dígitos verificadores
            
            # Verificar se o CNPJ já existe no banco
            fornecedor = db.get_fornecedor_by_cnpj(cnpj_numerico)
            if fornecedor:
                logger.info(f"Fornecedor encontrado: {fornecedor}")
                return jsonify({
                    'valid': True,
                    'exists': True,
                    'data': {
                        'fornecedor': fornecedor[0],
                        'uf': fornecedor[1],
                        'municipio': fornecedor[2],
                        'cod_municipio': fornecedor[3]
                    }
                })

            logger.info("Fornecedor não encontrado")    
            return jsonify({
                'valid': True,
                'exists': False
            })
            
        elif campo == 'municipio':
            # Verificar se o município existe
            municipio_info = db.get_municipio_by_codigo(valor)
            if not municipio_info:
                logger.warning("Código de município inválido")  
                return jsonify({
                    'valid': False,
                    'message': 'Código de município inválido'
                })

            logger.info(f"Município encontrado: {municipio_info}")    
            return jsonify({
                'valid': True,
                'data': {
                    'nome': municipio_info[0],
                    'codigo': municipio_info[1],
                    'uf': municipio_info[2]
                }
            })
        
        # Para outros campos, apenas validar se não está vazio
        elif not valor and campo in ['referencia', 'fornecedor', 'num_nf']:
            logger.warning(f"Campo {campo} é obrigatório")
            return jsonify({
                'valid': False,
                'message': 'Este campo é obrigatório'
            })
            
        # Se não houver validações específicas, considerar válido
        logger.info(f"Campo {campo} validado com sucesso")
        return jsonify({
            'valid': True
        })
        
    except Exception as e:
        logger.error(f"Erro durante validação: {str(e)}")
        return jsonify({
            'valid': False,
            'message': f'Erro durante validação: {str(e)}'
        }), 500

@app.route('/api/municipio/<codigo>')
def api_municipio(codigo):
    """
    API para obter dados de município por código
    """
    try:
        # Limpar código (remover caracteres não numéricos)
        codigo_numerico = ''.join(filter(str.isdigit, codigo))
        
        if not codigo_numerico or len(codigo_numerico) < 4:  # Permitir apenas códigos válidos
            logger.warning(f"Código de município inválido: {codigo}")
            return jsonify({'status': 'error', 'message': 'Código de município inválido'}), 400
        
        # Buscar município no banco de dados
        municipio = db.get_municipio_by_codigo(codigo_numerico)
        
        if not municipio:
            logger.warning(f"Município com código {codigo} não encontrado")
            return jsonify({})
        
        # Retornar dados formatados
        logger.info(f"Município encontrado: {municipio}")
        return jsonify({
            'nome': municipio[0],  # nome_municipio
            'uf': municipio[1],  # uf
            'codigo': municipio[2]  # cod_municipio
        })
    except Exception as e:
        app.logger.error(f"Erro ao buscar município com código {codigo}: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Erro ao buscar município: {str(e)}"
        }), 500


@app.route('/api/fornecedor/<cnpj>')
def api_fornecedor_por_cnpj(cnpj):
    """
    API para obter dados de fornecedor por CNPJ
    """
    try:
        # Limpar CNPJ (remover caracteres não numéricos)
        cnpj_numerico = ''.join(filter(str.isdigit, cnpj))
        
        if not cnpj_numerico or len(cnpj_numerico) < 11:  # Permitir CPF ou CNPJ
            logger.warning(f"CNPJ/CPF inválido: {cnpj}")
            return jsonify({'status': 'error', 'message': 'CNPJ/CPF inválido'}), 400
        
        # Buscar fornecedor no banco de dados
        fornecedor = db.get_fornecedor_by_cnpj(cnpj_numerico)
        
        if not fornecedor:
            logger.warning(f"Fornecedor com CNPJ {cnpj} não encontrado")
            return jsonify({})
        
        # Retornar dados formatados
        logger.info(f"Fornecedor encontrado: {fornecedor}")
        return jsonify({
            'descricao': fornecedor[0],  # descricao_fornecedor
            'uf': fornecedor[1],  # uf
            'municipio': fornecedor[2],  # municipio
            'cod_municipio': fornecedor[3],  # cod_municipio
            'cadastrado_goiania': fornecedor[4] if len(fornecedor) > 4 else None,  # cadastrado_goiania
            'fora_pais': fornecedor[5] if len(fornecedor) > 5 else None  # fora_pais
        })
    except Exception as e:
        app.logger.error(f"Erro ao buscar fornecedor com CNPJ {cnpj}: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Erro ao buscar fornecedor: {str(e)}"
        }), 500

@app.route('/api/ufs', methods=['GET'])
def api_get_ufs():
    """API para obter todas as UFs disponíveis"""
    try:
        # Obter todas as UFs do banco de dados
        ufs = db.get_all_ufs()
        
        # Ordenar alfabeticamente
        ufs.sort()
        
        return jsonify({
            'status': 'success',
            'data': ufs
        })
    except Exception as e:
        logger.error(f"Erro ao listar UFs: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/municipios/<uf>', methods=['GET'])
def api_get_municipios(uf):
    """API para obter municípios de uma UF específica"""
    try:
        # Validar UF
        if not uf or len(uf) != 2:
            return jsonify({
                'status': 'error',
                'message': 'UF inválida'
            }), 400
        
        # Buscar municípios da UF
        municipios_list = db.get_municipios_by_uf(uf.upper())
        
        # Formatar para JSON
        municipios = []
        for nome, codigo in municipios_list:
            municipios.append({
                'nome': nome,
                'codigo': codigo
            })
        
        return jsonify({
            'status': 'success',
            'data': municipios
        })
    except Exception as e:
        logger.error(f"Erro ao listar municípios de {uf}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    
if __name__ == '__main__':
        app.run(debug=True, host='127.0.0.1', port=5000)
  