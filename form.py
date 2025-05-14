import json
from flask_wtf import FlaskForm
from wtforms import FileField, StringField, SelectField, DateField, DecimalField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

def validate_select_field(form, field):
    """Validate that a selection has been made"""
    if not field.data or field.data == '':
        raise ValidationError('Por favor, selecione uma opção')

class ImportarMunicipiosForm(FlaskForm):
    arquivo = FileField('Arquivo TXT', validators=[DataRequired()])
    submit = SubmitField('Importar Municípios')

class NotaFiscalForm(FlaskForm):
    referencia = StringField('Referência', validators=[DataRequired()])
    cnpj = StringField('CNPJ/CPF', validators=[DataRequired(), Length(min=11, max=14)])
    fornecedor = StringField('Fornecedor', validators=[DataRequired()])
    uf = SelectField('UF',
        choices=[('', 'Selecione uma UF'), ('AC', 'AC')],
        validators=[validate_select_field]
    )
    municipio = SelectField('Município',
        choices=[('', 'Selecione um município')],
        validators=[validate_select_field]
    )
    cod_municipio = StringField('Código do Município', validators=[DataRequired()])
    inscricao_municipal = StringField('Inscrição Municipal', validators=[Optional()])
    cadastrado_goiania = SelectField('Cadastrado em Goiânia',
        choices=[('', 'Selecione'), ('Sim', 'Sim'), ('Não', 'Não')],
        validators=[validate_select_field]
    )
    fora_pais = SelectField('Fora do País',
        choices=[('', 'Selecione'), ('Sim', 'Sim'), ('Não', 'Não')],
        validators=[validate_select_field]
    )
    num_nf = StringField('Nº NF', validators=[DataRequired()])
    dt_emissao = DateField('Data de Emissão', format='%d/%m/%Y', validators=[DataRequired()])
    dt_pagamento = DateField('Data de Pagamento', format='%d/%m/%Y', validators=[DataRequired()])
    tipo_servico = SelectField('Tipo de Serviço',
        choices=[('', 'Selecione um Tipo de Serviço'), ('00', '00 - normal')],
        validators=[validate_select_field]
    )
    base_calculo = SelectField('Base de Cálculo',
        choices=[('', 'Selecione uma Base de Cálculo'), ('00', '00 - base de cálculo')],
        validators=[validate_select_field]
    )
    recolhimento = SelectField('Recolhimento',
        choices=[('', 'Selecione um Recolhimento'), ('Recolhimento', 'Recolhimento')],
        validators=[validate_select_field]
    )
    aliquota = DecimalField('Aliquota', places=2, validators=[DataRequired()])
    valor_nf = DecimalField('Valor NF', places=2, validators=[DataRequired()])
    recibo = StringField('Recibo', validators=[Optional()])
    submit = SubmitField('Salvar')

class TomadorForm(FlaskForm):
    razao_social = StringField('Razão Social', validators=[DataRequired()])
    cnpj = StringField('CNPJ', validators=[DataRequired(), Length(min=14, max=14)])
    inscricao = StringField('CAE/Inscrição', validators=[DataRequired()])
    usuario = StringField('Usuário Prefeitura', validators=[DataRequired()])
    submit = SubmitField('Salvar')

def validate_municipio(form, field):
    """Validação personalizada para município"""
    if not field.data or field.data == '':
        raise ValidationError('Por favor, selecione um município')

    try:
        # Tentar parsear o valor do município
        municipio_data = json.loads(field.data)

        # Validar estrutura do JSON
        if not isinstance(municipio_data, dict):
            raise ValidationError('Formato de município inválido')

        # Verificar campos obrigatórios
        if not municipio_data.get('nome') or not municipio_data.get('codigo'):
            raise ValidationError('Dados do município incompletos')

    except (ValueError, json.JSONDecodeError):
        raise ValidationError('Formato de município inválido')

class MunicipioSelectionForm(FlaskForm):
    municipio = SelectField('Município',
        choices=[
            ('', 'Selecione um Município'),
            ('GO', 'Goiânia'),
            ('SP', 'São Paulo'),
            ('RJ', 'Rio de Janeiro'),
            ('MG', 'Belo Horizonte')
        ],
        validators=[validate_select_field]
    )
    submit = SubmitField('Selecionar')

def validate_cnpj(form, field):
    """
    Validação personalizada de CNPJ para o formulário
    
    :param form: Formulário
    :param field: Campo de CNPJ
    """
    from database import DatabaseManager
    
    # Criar instância do gerenciador de banco de dados
    db_manager = DatabaseManager()
    
    # Remover caracteres não numéricos
    cnpj = ''.join(filter(str.isdigit, field.data))
    
    # Validar CNPJ
    if not db_manager.validate_cnpj(cnpj):
        raise ValidationError('CNPJ inválido. Verifique o número digitado.')

class TomadorForm(FlaskForm):
    razao_social = StringField('Razão Social', validators=[
        DataRequired(message='Razão Social é obrigatória')
    ])
    cnpj = StringField('CNPJ', validators=[
        DataRequired(message='CNPJ é obrigatório'),
        Length(min=14, max=18, message='CNPJ deve ter entre 14 e 18 caracteres'),
        validate_cnpj
    ])
    inscricao = StringField('CAE/Inscrição', validators=[
        DataRequired(message='Inscrição é obrigatória')
    ])
    usuario = StringField('Usuário Prefeitura', validators=[
        DataRequired(message='Usuário da Prefeitura é obrigatório')
    ])
    submit = SubmitField('Salvar')

    
