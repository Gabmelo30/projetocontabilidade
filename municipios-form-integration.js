// Função para popular o dropdown de UFs
function popularUFs() {
    const ufSelect = document.getElementById('uf');
    if (!ufSelect) return;
    
    ufSelect.innerHTML = '<option value="">Selecione uma UF</option>';
    
    // Tentar buscar UFs via API
    fetch('/api/ufs')
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao carregar UFs');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // Popular dropdown com UFs do banco de dados
                data.data.forEach(uf => {
                    const option = document.createElement('option');
                    option.value = uf;
                    option.textContent = uf;
                    ufSelect.appendChild(option);
                });
                console.log('UFs carregadas da API');
            } else {
                // Fallback para lista estática
                ufsBrasileiras.forEach(uf => {
                    const option = document.createElement('option');
                    option.value = uf;
                    option.textContent = uf;
                    ufSelect.appendChild(option);
                });
                console.log('Usando UFs estáticas devido a erro na API');
            }
        })
        .catch(error => {
            console.error('Erro ao buscar UFs:', error);
            // Fallback para lista estática
            ufsBrasileiras.forEach(uf => {
                const option = document.createElement('option');
                option.value = uf;
                option.textContent = uf;
                ufSelect.appendChild(option);
            });
            console.log('Usando UFs estáticas devido a erro na API');
        });
}

// Função para popular o dropdown de municípios com base na UF selecionada
function popularMunicipios() {
    const ufSelect = document.getElementById('uf');
    const municipioSelect = document.getElementById('municipio');
    const codMunicipioInput = document.getElementById('cod_municipio');
    
    if (!ufSelect || !municipioSelect) return;
    
    ufSelect.addEventListener('change', function() {
        const uf = this.value;
        municipioSelect.innerHTML = '<option value="">Selecione um município</option>';
        
        if (!uf) return;
        
        // Tentar buscar municípios via API
        fetch(`/api/municipios/${uf}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro ao carregar municípios');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success' && data.data && data.data.length > 0) {
                    // Ordenar municípios alfabeticamente
                    data.data.sort((a, b) => a.nome.localeCompare(b.nome));
                    
                    // Popular dropdown com municípios do banco de dados
                    data.data.forEach(municipio => {
                        const option = document.createElement('option');
                        option.value = municipio.codigo;
                        option.textContent = municipio.nome;
                        municipioSelect.appendChild(option);
                    });
                    console.log(`Municípios de ${uf} carregados da API`);
                } else {
                    // Fallback para lista estática se disponível
                    if (municipiosPorUF[uf]) {
                        municipiosPorUF[uf].forEach(municipio => {
                            const option = document.createElement('option');
                            option.value = municipio[1]; // Código do município
                            option.textContent = municipio[0]; // Nome do município
                            municipioSelect.appendChild(option);
                        });
                        console.log(`Usando municípios estáticos para ${uf}`);
                    } else {
                        console.warn(`Nenhum município encontrado para ${uf}`);
                    }
                }
            })
            .catch(error => {
                console.error(`Erro ao buscar municípios de ${uf}:`, error);
                // Fallback para lista estática se disponível
                if (municipiosPorUF[uf]) {
                    municipiosPorUF[uf].forEach(municipio => {
                        const option = document.createElement('option');
                        option.value = municipio[1]; // Código do município
                        option.textContent = municipio[0]; // Nome do município
                        municipioSelect.appendChild(option);
                    });
                    console.log(`Usando municípios estáticos para ${uf}`);
                }
            });
    });
    
    // Quando selecionar um município, preencher o campo de código
    if (municipioSelect && codMunicipioInput) {
        municipioSelect.addEventListener('change', function() {
            codMunicipioInput.value = this.value;
        });
    }
}