/**
 * scripts.js - Funções gerais para a aplicação
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar componentes da UI
    inicializarTooltips();
    inicializarValidacoes();
    configurarModals();
    configurarAjaxForms();
    
    // Verificar se temos o formulário de notas fiscais e configurá-lo
    const formNotaFiscal = document.getElementById('form-nota-fiscal');
    if (formNotaFiscal) {
        configurarFormularioNotaFiscal(formNotaFiscal);
    }
    
    // Verificar se temos a tabela de notas fiscais e configurá-la
    const tabelaNotas = document.getElementById('tabela-notas');
    if (tabelaNotas) {
        configurarTabelaNotas(tabelaNotas);
    }
    
    // Configurar funcionalidade de exportação
    const btnExportar = document.getElementById('btn-exportar');
    if (btnExportar) {
        btnExportar.addEventListener('click', confirmarExportacao);
    }
    
    // Configurar formulário de importação
    const formImportacao = document.getElementById('form-importacao');
    if (formImportacao) {
        configurarFormularioImportacao(formImportacao);
    }
});

/**
 * Inicializa tooltips para elementos com o atributo 'data-tooltip'
 */
function inicializarTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        // Implementação específica de tooltips pode ser adicionada aqui
        // Este é apenas um exemplo simples
        element.title = element.getAttribute('data-tooltip');
    });
}

/**
 * Inicializa validações de formulário
 */
function inicializarValidacoes() {
    const forms = document.querySelectorAll('form.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
    });
}

/**
 * Configura modais para confirmação de ações
 */
function configurarModals() {
    // Configurar modais de confirmação para exclusão
    const btnsExcluir = document.querySelectorAll('.btn-excluir');
    
    btnsExcluir.forEach(btn => {
        btn.addEventListener('click', function(event) {
            event.preventDefault();
            
            const url = this.getAttribute('href');
            const item = this.getAttribute('data-item') || 'item';
            
            if (confirm(`Tem certeza que deseja excluir este ${item}?`)) {
                // Criar um formulário para fazer o POST de exclusão
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = url;
                document.body.appendChild(form);
                form.submit();
            }
        });
    });
}

/**
 * Configura formulários para envio via AJAX
 */
function configurarAjaxForms() {
    const ajaxForms = document.querySelectorAll('form.ajax-form');
    
    ajaxForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const formData = new FormData(form);
            const url = form.action;
            const method = form.method.toUpperCase();
            
            fetch(url, {
                method: method,
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert(data.message || 'Operação realizada com sucesso!');
                    
                    // Se tiver um redirecionamento, fazer
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    }
                    
                    // Se precisar atualizar a página
                    if (data.refresh) {
                        window.location.reload();
                    }
                } else {
                    alert(data.message || 'Ocorreu um erro na operação.');
                }
            })
            .catch(error => {
                console.error('Erro na requisição:', error);
                alert('Ocorreu um erro na comunicação com o servidor.');
            });
        });
    });
}

/**
 * Configura o formulário de notas fiscais
 */
function configurarFormularioNotaFiscal(form) {
    // Campo de CNPJ - validar e buscar dados do fornecedor
    const cnpjInput = form.querySelector('#cnpj');
    if (cnpjInput) {
        cnpjInput.addEventListener('blur', function() {
            const cnpj = this.value.replace(/\D/g, '');
            if (cnpj.length >= 11) {
                buscarFornecedorPorCNPJ(cnpj);
            }
        });
    }
    
    // Máscara para CNPJ
    const mascaraInputs = form.querySelectorAll('.mascara-cnpj');
    mascaraInputs.forEach(input => {
        input.addEventListener('input', function() {
            const valor = this.value.replace(/\D/g, '');
            if (valor.length <= 11) {
                // Formato CPF: 000.000.000-00
                this.value = valor.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
            } else {
                // Formato CNPJ: 00.000.000/0000-00
                this.value = valor.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
            }
        });
    });
    
    // Validações de campos em tempo real
    const camposValidaveis = form.querySelectorAll('[data-validacao]');
    camposValidaveis.forEach(campo => {
        campo.addEventListener('blur', function() {
            validarCampo(this);
        });
    });
}

/**
 * Busca dados de fornecedor pelo CNPJ
 */
function buscarFornecedorPorCNPJ(cnpj) {
    fetch(`/api/fornecedor/${cnpj}`)
        .then(response => response.json())
        .then(data => {
            if (data && data.descricao) {
                // Preencher os campos com os dados do fornecedor
                document.getElementById('fornecedor').value = data.descricao;
                
                const ufSelect = document.getElementById('uf');
                if (ufSelect && data.uf) {
                    ufSelect.value = data.uf;
                    // Disparar o evento change para carregar os municípios
                    const event = new Event('change');
                    ufSelect.dispatchEvent(event);
                    
                    // Após um breve delay, selecionar o município
                    setTimeout(() => {
                        const municipioSelect = document.getElementById('municipio');
                        if (municipioSelect && data.cod_municipio) {
                            municipioSelect.value = data.cod_municipio;
                            
                            // Atualizar o campo de código do município
                            const codMunicipioInput = document.getElementById('cod_municipio');
                            if (codMunicipioInput) {
                                codMunicipioInput.value = data.cod_municipio;
                            }
                        }
                    }, 500);
                }
                
                // Marcar os checkboxes conforme dados do fornecedor
                if (data.cadastrado_goiania !== null) {
                    document.getElementById('cadastrado_goiania').checked = data.cadastrado_goiania;
                }
                
                if (data.fora_pais !== null) {
                    document.getElementById('fora_pais').checked = data.fora_pais;
                }
            }
        })
        .catch(error => {
            console.error('Erro ao buscar fornecedor:', error);
        });
}

/**
 * Valida um campo específico em tempo real
 */
function validarCampo(campo) {
    const valor = campo.value;
    const tipoValidacao = campo.getAttribute('data-validacao');
    
    // URL para a validação do campo
    const url = '/nota-fiscal/validar-campos';
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            campo: tipoValidacao,
            valor: valor
        })
    })
    .then(response => response.json())
    .then(data => {
        // Remover mensagens de erro anteriores
        const mensagemErro = campo.parentNode.querySelector('.mensagem-erro');
        if (mensagemErro) {
            mensagemErro.remove();
        }
        
        // Atualizar classe do campo
        campo.classList.remove('is-invalid', 'is-valid');
        
        if (data.valid) {
            campo.classList.add('is-valid');
            
            // Se tiver dados adicionais, processar
            if (data.data) {
                processarDadosValidacao(tipoValidacao, data.data);
            }
        } else {
            campo.classList.add('is-invalid');
            
            // Adicionar mensagem de erro
            const div = document.createElement('div');
            div.className = 'mensagem-erro text-danger';
            div.textContent = data.message || 'Campo inválido';
            campo.parentNode.appendChild(div);
        }
    })
    .catch(error => {
        console.error('Erro na validação do campo:', error);
    });
}

/**
 * Processa dados retornados da validação
 */
function processarDadosValidacao(tipo, dados) {
    // Processar conforme o tipo de validação
    switch (tipo) {
        case 'cnpj':
            if (dados.fornecedor) {
                document.getElementById('fornecedor').value = dados.fornecedor;
            }
            break;
            
        case 'municipio':
            if (dados.nome) {
                // Atualizar o nome do município se necessário
            }
            break;
            
        // Outros casos específicos
    }
}

/**
 * Configura tabela de notas fiscais com funcionalidades de busca e ordenação
 */
function configurarTabelaNotas(tabela) {
    // Configurar busca na tabela
    const inputBusca = document.getElementById('input-busca');
    if (inputBusca) {
        inputBusca.addEventListener('input', function() {
            const termo = this.value.toLowerCase();
            
            // Cada linha da tabela (exceto o cabeçalho)
            const linhas = tabela.querySelectorAll('tbody tr');
            
            linhas.forEach(linha => {
                const texto = linha.textContent.toLowerCase();
                
                if (texto.includes(termo)) {
                    linha.style.display = '';
                } else {
                    linha.style.display = 'none';
                }
            });
        });
    }
    
    // Configurar ordenação da tabela
    const cabecalhos = tabela.querySelectorAll('thead th[data-ordenar]');
    cabecalhos.forEach(cabecalho => {
        cabecalho.addEventListener('click', function() {
            const coluna = this.getAttribute('data-ordenar');
            ordenarTabela(tabela, coluna);
        });
    });
}

/**
 * Ordena uma tabela HTML pela coluna especificada
 */
function ordenarTabela(tabela, coluna) {
    const direcao = tabela.getAttribute('data-direcao') === 'asc' ? 'desc' : 'asc';
    tabela.setAttribute('data-direcao', direcao);
    
    const tbody = tabela.querySelector('tbody');
    const linhas = Array.from(tbody.querySelectorAll('tr'));
    
    // Ordenar linhas
    linhas.sort((a, b) => {
        const celulaA = a.querySelector(`td:nth-child(${parseInt(coluna) + 1})`);
        const celulaB = b.querySelector(`td:nth-child(${parseInt(coluna) + 1})`);
        
        const valorA = celulaA.textContent.trim();
        const valorB = celulaB.textContent.trim();
        
        // Verificar se é número ou data
        if (!isNaN(valorA) && !isNaN(valorB)) {
            return direcao === 'asc' ? 
                parseFloat(valorA) - parseFloat(valorB) : 
                parseFloat(valorB) - parseFloat(valorA);
        } else {
            return direcao === 'asc' ? 
                valorA.localeCompare(valorB) : 
                valorB.localeCompare(valorA);
        }
    });
    
    // Recriar tabela com linhas ordenadas
    linhas.forEach(linha => tbody.appendChild(linha));
}

/**
 * Confirma exportação de dados para Excel
 */
function confirmarExportacao() {
    const limpar = confirm('Deseja limpar os dados após a exportação?');
    
    const inputLimpar = document.getElementById('limpar_apos_exportar');
    if (inputLimpar) {
        inputLimpar.value = limpar ? 'sim' : 'nao';
    }
    
    // Submeter formulário de exportação
    const formExportacao = document.getElementById('form-exportacao');
    if (formExportacao) {
        formExportacao.submit();
    }
}

/**
 * Configura o formulário de importação de municípios
 */
function configurarFormularioImportacao(form) {
    // Exibir nome do arquivo selecionado
    const inputArquivo = form.querySelector('input[type="file"]');
    const labelArquivo = form.querySelector('.custom-file-label');
    
    if (inputArquivo && labelArquivo) {
        inputArquivo.addEventListener('change', function() {
            if (this.files.length > 0) {
                labelArquivo.textContent = this.files[0].name;
            } else {
                labelArquivo.textContent = 'Selecione um arquivo';
            }
        });
    }
    
    // Enviar formulário via AJAX
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const formData = new FormData(form);
        
        // Desabilitar botão de envio durante o processo
        const btnEnviar = form.querySelector('[type="submit"]');
        if (btnEnviar) {
            btnEnviar.disabled = true;
            btnEnviar.textContent = 'Importando...';
        }
        
        // Área de status
        const statusArea = document.getElementById('status-importacao');
        if (statusArea) {
            statusArea.innerHTML = '<p>Iniciando importação...</p>';
        }
        
        fetch('/api/importar-municipios', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (btnEnviar) {
                btnEnviar.disabled = false;
                btnEnviar.textContent = 'Importar';
            }
            
            if (statusArea) {
                if (data.status === 'success') {
                    statusArea.innerHTML += `<p class="text-success">${data.message}</p>`;
                } else {
                    statusArea.innerHTML += `<p class="text-danger">${data.message}</p>`;
                }
            }
            
            // Resetar formulário em caso de sucesso
            if (data.status === 'success') {
                form.reset();
                if (labelArquivo) {
                    labelArquivo.textContent = 'Selecione um arquivo';
                }
            }
        })
        .catch(error => {
            console.error('Erro na importação:', error);
            
            if (btnEnviar) {
                btnEnviar.disabled = false;
                btnEnviar.textContent = 'Importar';
            }
            
            if (statusArea) {
                statusArea.innerHTML += `<p class="text-danger">Erro na comunicação com o servidor: ${error.message}</p>`;
            }
        });
    });
}

/**
 * Valida um CNPJ
 * @param {string} cnpj - CNPJ a ser validado (com ou sem formatação)
 * @return {boolean} - true se válido, false caso contrário
 */
function validarCNPJ(cnpj) {
    // Remove caracteres não numéricos
    cnpj = cnpj.replace(/[^\d]/g, '');
    
    // Verifica se tem 14 dígitos
    if (cnpj.length !== 14) {
        return false;
    }
    
    // Verifica se todos os dígitos são iguais (caso inválido)
    if (/^(\d)\1+$/.test(cnpj)) {
        return false;
    }
    
    // Validação do primeiro dígito verificador
    let soma = 0;
    let peso = 5;
    
    // Soma os produtos dos dígitos com os pesos
    for (let i = 0; i < 12; i++) {
        soma += parseInt(cnpj.charAt(i)) * peso;
        peso = (peso === 2) ? 9 : peso - 1;
    }
    
    // Cálculo do primeiro dígito verificador
    let resto = soma % 11;
    let dv1 = (resto < 2) ? 0 : 11 - resto;
    
    // Verifica o primeiro dígito verificador
    if (parseInt(cnpj.charAt(12)) !== dv1) {
        return false;
    }
    
    // Validação do segundo dígito verificador
    soma = 0;
    peso = 6;
    
    // Soma os produtos dos dígitos com os pesos
    for (let i = 0; i < 13; i++) {
        soma += parseInt(cnpj.charAt(i)) * peso;
        peso = (peso === 2) ? 9 : peso - 1;
    }
    
    // Cálculo do segundo dígito verificador
    resto = soma % 11;
    let dv2 = (resto < 2) ? 0 : 11 - resto;
    
    // Verifica o segundo dígito verificador
    return parseInt(cnpj.charAt(13)) === dv2;
}

/**
 * Função auxiliar para validar CPF
 * @param {string} cpf - CPF a ser validado
 * @return {boolean} true se válido, false caso contrário
 */
function validarCPF(cpf) {
    // Remove caracteres não numéricos
    cpf = cpf.replace(/[^\d]/g, '');
    
    // Verifica se tem 11 dígitos
    if (cpf.length !== 11) {
        return false;
    }
    
    // Verifica se todos os dígitos são iguais (caso inválido)
    if (/^(\d)\1+$/.test(cpf)) {
        return false;
    }
    
    // Validação do primeiro dígito verificador
    let soma = 0;
    for (let i = 0; i < 9; i++) {
        soma += parseInt(cpf.charAt(i)) * (10 - i);
    }
    
    let resto = soma % 11;
    let dv1 = (resto < 2) ? 0 : 11 - resto;
    
    // Verifica o primeiro dígito verificador
    if (parseInt(cpf.charAt(9)) !== dv1) {
        return false;
    }
    
    // Validação do segundo dígito verificador
    soma = 0;
    for (let i = 0; i < 10; i++) {
        soma += parseInt(cpf.charAt(i)) * (11 - i);
    }
    
    resto = soma % 11;
    let dv2 = (resto < 2) ? 0 : 11 - resto;
    
    // Verifica o segundo dígito verificador
    return parseInt(cpf.charAt(10)) === dv2;
}

/**
 * Valida um documento (CNPJ ou CPF)
 * @param {string} documento - CNPJ ou CPF a ser validado
 * @return {boolean} true se válido, false caso contrário
 */
function validarDocumento(documento) {
    // Remove caracteres não numéricos
    const apenasNumeros = documento.replace(/[^\d]/g, '');
    
    // Verifica se é CPF ou CNPJ com base no tamanho
    if (apenasNumeros.length === 11) {
        return validarCPF(apenasNumeros);
    } else if (apenasNumeros.length === 14) {
        return validarCNPJ(apenasNumeros);
    }
    
    return false;
}

// Adiciona validação ao formulário quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    const formTomador = document.getElementById('form-tomador');
    if (formTomador) {
        // Validação do CNPJ/CPF no formulário de tomador
        formTomador.addEventListener('submit', function(event) {
            const cnpjInput = document.getElementById('cnpj');
            if (cnpjInput) {
                const cnpj = cnpjInput.value;
                if (!validarDocumento(cnpj)) {
                    event.preventDefault(); // Impede o envio do formulário
                    alert('CNPJ/CPF inválido. Por favor, verifique o documento informado.');
                    cnpjInput.focus();
                }
            }
        });
        
        // Adiciona validação em tempo real quando o campo perder o foco
        const cnpjInput = document.getElementById('cnpj');
        if (cnpjInput) {
            cnpjInput.addEventListener('blur', function() {
                const cnpj = this.value;
                if (cnpj && !validarDocumento(cnpj)) {
                    this.classList.add('is-invalid');
                    
                    // Adiciona mensagem de erro se não existir
                    let feedbackElement = this.nextElementSibling;
                    if (!feedbackElement || !feedbackElement.classList.contains('invalid-feedback')) {
                        feedbackElement = document.createElement('div');
                        feedbackElement.className = 'invalid-feedback';
                        this.parentNode.insertBefore(feedbackElement, this.nextSibling);
                    }
                    feedbackElement.textContent = 'CNPJ/CPF inválido';
                } else if (cnpj) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                    
                    // Remove mensagem de erro se existir
                    const feedbackElement = this.nextElementSibling;
                    if (feedbackElement && feedbackElement.classList.contains('invalid-feedback')) {
                        feedbackElement.remove();
                    }
                }
            });
            
            // Formata o CNPJ/CPF enquanto o usuário digita
            cnpjInput.addEventListener('input', function() {
                const valor = this.value.replace(/\D/g, '');
                
                if (valor.length <= 11) {
                    // Formato de CPF: 000.000.000-00
                    this.value = valor.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, function(match, p1, p2, p3, p4) {
                        if (p4) return `${p1}.${p2}.${p3}-${p4}`;
                        if (p3) return `${p1}.${p2}.${p3}`;
                        if (p2) return `${p1}.${p2}`;
                        return p1;
                    });
                } else {
                    // Formato de CNPJ: 00.000.000/0000-00
                    this.value = valor.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, function(match, p1, p2, p3, p4, p5) {
                        if (p5) return `${p1}.${p2}.${p3}/${p4}-${p5}`;
                        if (p4) return `${p1}.${p2}.${p3}/${p4}`;
                        if (p3) return `${p1}.${p2}.${p3}`;
                        if (p2) return `${p1}.${p2}`;
                        return p1;
                    });
                }
            });
        }
    }
});