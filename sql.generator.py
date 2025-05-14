#!/usr/bin/env python3
"""
sql_generator.py - Integração para Geração SQL de Municípios

Este módulo adiciona funcionalidade de geração SQL ao seu sistema Flask existente.
"""

import os
import tempfile
import sqlite3
import logging
from datetime import datetime
from flask import render_template, request, redirect, jsonify, send_file, url_for

logger = logging.getLogger(__name__)

def setup_sql_generator(app, db_manager):
    """
    Adiciona as rotas do SQL Generator à aplicação Flask existente
    
    :param app: Aplicação Flask
    :param db_manager: Instância do DatabaseManager
    """
    # Rota principal do gerador SQL
    @app.route('/sql-generator')
    def sql_generator_home():
        """Página inicial do Gerador SQL"""
        # Obter todas as UFs disponíveis
        ufs = db_manager.get_all_ufs()
        return render_template('sql_generator.html', ufs=ufs)
    
    # API para gerar SQL
    @app.route('/api/generate-sql', methods=['POST'])
    def generate_sql_api():
        """API para gerar SQL com base nos parâmetros fornecidos"""
        try:
            # Obter parâmetros
            data = request.json or {}
            ufs = data.get('ufs', [])  # Lista de UFs selecionadas
            selected_columns = data.get('columns', ['uf', 'cod_municipio', 'nome_municipio'])
            include_create_table = data.get('include_create_table', True)
            limit = data.get('limit', 0)  # 0 = sem limite
            search = data.get('search', '')  # Filtro por texto
            
            # Validar parâmetros
            if not isinstance(ufs, list):
                ufs = [ufs] if ufs else []
            
            # Conectar ao banco e gerar SQL
            sql_commands = generate_sql_commands(
                db_path=db_manager.db_file,
                ufs=ufs,
                selected_columns=selected_columns,
                include_create_table=include_create_table,
                limit=limit,
                search=search
            )
            
            # Retornar SQL gerado
            return jsonify({
                'status': 'success',
                'sql': sql_commands,
                'params': {
                    'ufs': ufs,
                    'columns': selected_columns,
                    'include_create_table': include_create_table,
                    'limit': limit,
                    'search': search
                }
            })
        
        except Exception as e:
            logger.error(f"Erro ao gerar SQL: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # Download do SQL gerado
    @app.route('/download-sql', methods=['POST'])
    def download_sql():
        """Download do script SQL gerado"""
        try:
            # Obter parâmetros
            ufs = request.form.getlist('ufs')
            columns = request.form.getlist('columns')
            include_create_table = request.form.get('include_create_table', 'on') == 'on'
            limit = int(request.form.get('limit', '0'))
            search = request.form.get('search', '')
            
            # Gerar SQL
            sql_commands = generate_sql_commands(
                db_path=db_manager.db_file,
                ufs=ufs,
                selected_columns=columns,
                include_create_table=include_create_table,
                limit=limit,
                search=search
            )
            
            # Criar arquivo temporário
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.sql')
            temp_file.write(sql_commands.encode('utf-8'))
            temp_file.close()
            
            # Preparar nome do arquivo de saída
            if len(ufs) == 1:
                filename = f"municipios_{ufs[0]}.sql"
            else:
                filename = f"municipios_{len(ufs)}_ufs_{datetime.now().strftime('%Y%m%d')}.sql"
            
            # Enviar arquivo para download
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=filename,
                mimetype='text/plain'
            )
        
        except Exception as e:
            logger.error(f"Erro no download do SQL: {e}")
            return redirect(url_for('sql_generator_home'))
    
    # API para contar municípios por UF
    @app.route('/api/municipios-count')
    def get_municipios_count():
        """Obtém a contagem de municípios por UF"""
        try:
            conn = sqlite3.connect(db_manager.db_file)
            cursor = conn.cursor()
            
            # Contar municípios por UF
            cursor.execute("""
                SELECT uf, COUNT(*) as total 
                FROM tb_municipios 
                GROUP BY uf 
                ORDER BY uf
            """)
            
            # Formatar os resultados
            counts = {row[0]: row[1] for row in cursor.fetchall()}
            total = sum(counts.values())
            
            return jsonify({
                'status': 'success',
                'counts': counts,
                'total': total
            })
        
        except Exception as e:
            logger.error(f"Erro ao contar municípios: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
        
        finally:
            if 'conn' in locals() and conn:
                conn.close()

def generate_sql_commands(db_path, ufs=None, selected_columns=None, include_create_table=True, limit=0, search=''):
    """
    Gera comandos SQL INSERT OR REPLACE para municípios
    
    :param db_path: Caminho do banco de dados SQLite
    :param ufs: Lista de UFs para filtrar (None = todas)
    :param selected_columns: Lista de colunas a incluir (None = todas)
    :param include_create_table: Se deve incluir o comando CREATE TABLE
    :param limit: Número máximo de registros (0 = sem limite)
    :param search: Filtro de texto para nome do município
    :return: String com comandos SQL
    """
    # Definir colunas padrão se não especificadas
    all_columns = ['uf', 'cod_municipio', 'nome_municipio']
    if not selected_columns:
        selected_columns = all_columns
    
    # Validar que colunas solicitadas existem
    selected_columns = [col for col in selected_columns if col in all_columns]
    
    if not selected_columns:
        return "-- Erro: Nenhuma coluna válida selecionada para gerar SQL"
    
    # Conectar ao banco
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Para acessar colunas pelo nome
    
    try:
        cursor = conn.cursor()
        
        # Construir a consulta SQL para buscar os municípios
        query = f"SELECT {', '.join(selected_columns)} FROM tb_municipios"
        params = []
        
        # Aplicar filtros
        conditions = []
        
        if ufs and isinstance(ufs, list) and len(ufs) > 0:
            placeholders = ', '.join(['?' for _ in ufs])
            conditions.append(f"uf IN ({placeholders})")
            params.extend(ufs)
        
        if search:
            conditions.append("nome_municipio LIKE ?")
            params.append(f"%{search.upper()}%")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Ordenação
        query += " ORDER BY uf, nome_municipio"
        
        # Limite de registros
        if limit > 0:
            query += " LIMIT ?"
            params.append(limit)
        
        # Executar consulta
        cursor.execute(query, params)
        municipios = cursor.fetchall()
        
        # Contar municípios por UF para o cabeçalho
        uf_counts = {}
        for municipio in municipios:
            if 'uf' in municipio.keys():
                uf = municipio['uf']
                uf_counts[uf] = uf_counts.get(uf, 0) + 1
        
        # Iniciar a construção do script SQL
        sql = "-- Script SQL para importação de municípios brasileiros\n"
        sql += f"-- Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        sql += f"-- Total de municípios: {len(municipios)}\n"
        
        # Adicionar contagem por UF
        if uf_counts:
            sql += "-- UFs incluídas:\n"
            for uf, count in sorted(uf_counts.items()):
                sql += f"--   {uf}: {count} municípios\n"
        
        sql += "\n"
        
        # Adicionar comando CREATE TABLE se solicitado
        if include_create_table:
            sql += "-- Criar tabela se não existir\n"
            sql += "CREATE TABLE IF NOT EXISTS tb_municipios (\n"
            sql += "    uf TEXT,\n"
            sql += "    cod_municipio TEXT,\n"
            sql += "    nome_municipio TEXT,\n"
            sql += "    PRIMARY KEY (uf, cod_municipio)\n"
            sql += ");\n\n"
        
        # Adicionar transação para melhor performance
        sql += "BEGIN TRANSACTION;\n\n"
        
        # Gerar comandos INSERT OR REPLACE
        for municipio in municipios:
            # Montar valores das colunas
            values = []
            for col in selected_columns:
                val = municipio[col]
                # Escapar aspas simples nos valores de texto
                if isinstance(val, str):
                    val = val.replace("'", "''")
                values.append(f"'{val}'")
            
            # Construir comando
            sql += f"INSERT OR REPLACE INTO tb_municipios ({', '.join(selected_columns)}) "
            sql += f"VALUES ({', '.join(values)});\n"
        
        # Finalizar transação
        sql += "\nCOMMIT;\n"
        
        return sql
    
    except Exception as e:
        logger.error(f"Erro ao gerar SQL: {e}")
        return f"-- Erro ao gerar comandos SQL: {e}"
    
    finally:
        if conn:
            conn.close()