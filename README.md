app/
│
├── core/
│   ├── __init__.py
│   ├── database.py           # Configuração base de conexão
│   └── config.py             # Configurações da aplicação
│
├── models/
│   ├── __init__.py
│   ├── municipio.py          # Modelo de Município
│   ├── nota_fiscal.py        # Modelo de Nota Fiscal
│   └── tomador.py            # Modelo de Tomador
│
├── repositories/
│   ├── __init__.py
│   ├── base_repository.py    # Repositório base abstrato
│   ├── municipio_repository.py   # Repositório de Municípios
│   ├── nota_fiscal_repository.py # Repositório de Notas Fiscais
│   └── tomador_repository.py     # Repositório de Tomadores
│
├── services/
│   ├── __init__.py
│   ├── municipio_service.py      # Lógica de negócio para Municípios
│   ├── nota_fiscal_service.py    # Lógica de negócio para Notas Fiscais
│   └── tomador_service.py        # Lógica de negócio para Tomadores
│
├── utils/
│   ├── __init__.py
│   ├── file_handler.py       # Utilitários para manipulação de arquivos
│   └── encoding_detector.py  # Detecção robusta de encoding
│
├── web/
│   ├── __init__.py
│   ├── forms.py              # Formulários
│   └── routes.py             # Rotas da aplicação
│
├── templates/
└── static/