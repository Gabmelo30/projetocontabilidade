# Em render_template_string.py
from sqlite3 import dbapi2
from web_app import app  # Importar app do arquivo principal
from flask import render_template_string
import os

print("Templates folder path:", os.path.join(os.getcwd(), 'templates'))

@app.route('/tomadores-alternativo')
def listar_tomadores_alternativo():
    # Resto do código...

    """Rota alternativa para listar tomadores com HTML dinâmico"""
    tomadores = dbapi2.get_all_tomadores()
    
    # Criar template HTML com estilo embutido
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Lista de Tomadores - Alternativo</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            th, td {
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }
            th {
                background-color: #f4f4f4;
                font-weight: bold;
                color: #333;
            }
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            tr:hover {
                background-color: #f1f1f1;
                transition: background-color 0.3s ease;
            }
            h1 {
                color: #333;
                text-align: center;
                border-bottom: 2px solid #ddd;
                padding-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <h1>Tomadores Cadastrados</h1>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Razão Social</th>
                    <th>CNPJ</th>
                    <th>Inscrição</th>
                    <th>Usuário</th>
                </tr>
            </thead>
            <tbody>
                {% for tomador in tomadores %}
                <tr>
                    <td>{{ tomador[0] }}</td>
                    <td>{{ tomador[1] }}</td>
                    <td>{{ tomador[2] }}</td>
                    <td>{{ tomador[3] }}</td>
                    <td>{{ tomador[4] }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """
    
    # Renderizar o template com os dados dos tomadores
    return render_template_string(html_template, tomadores=tomadores)