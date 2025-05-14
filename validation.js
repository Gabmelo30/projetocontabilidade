// Função para validar CNPJ no frontend
function validarCNPJ(cnpj) {
    // Remove caracteres não numéricos
    cnpj = cnpj.replace(/\D/g, '');

    // Verifica se tem 14 dígitos
    if (cnpj.length !== 14) {
        return false;
    }

    // Verifica se todos os dígitos são iguais
    if (/^(\d)\1{13}$/.test(cnpj)) {
        return false;
    }

    // Calcula o primeiro dígito verificador
    let soma = 0;
    let peso = 5;
    for (let i = 0; i < 12; i++) {
        soma += parseInt(cnpj.charAt(i)) * peso;
        peso = peso === 2 ? 9 : peso - 1;
    }

    let resto = soma % 11;
    let digito1 = resto < 2 ? 0 : 11 - resto;

    // Calcula o segundo dígito verificador
    soma = 0;
    peso = 6;
    for (let i = 0; i < 13; i++) {
        soma += parseInt(cnpj.charAt(i)) * peso;
        peso = peso === 2 ? 9 : peso - 1;
    }

    resto = soma % 11;
    let digito2 = resto < 2 ? 0 : 11 - resto;

    // Verifica se os dígitos verificadores estão corretos
    return cnpj.charAt(12) == digito1.toString() && cnpj.charAt(13) == digito2.toString();
}

// Função para formatar CNPJ
function formatarCNPJ(cnpj) {
    // Remove caracteres não numéricos
    cnpj = cnpj.replace(/\D/g, '');

    // Formata como CNPJ: 00.000.000/0000-00
    return cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
}

// Função para validar o formulário antes do envio
function validarFormulario() {
    $('#tomadorForm').on('submit', function(e) {
        const cnpj = $('#cnpjCpf').val();

        if (!validarCNPJ(cnpj)) {
            e.preventDefault();
            alert('CNPJ inválido. Por favor, verifique o número informado.');
            $('#cnpjCpf').addClass('error');
            return;
        }

        // Remove a classe de erro se existir
        $('#cnpjCpf').removeClass('error');
    });
}

// Função para formatar o CNPJ automaticamente
function configurarFormatacaoCNPJ() {
    $('#cnpjCpf').on('input', function() {
        let valor = $(this).val();
        valor = formatarCNPJ(valor);
        $(this).val(valor);
    });
}

// Inicializa as funções quando a página carregar
$(document).ready(function() {
    configurarFormatacaoCNPJ();
    validarFormulario();
});
