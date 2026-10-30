# ToolTiss Editor

Editor web local para guias TISS (padrão ANS de faturamento em saúde). Carrega XMLs existentes em formulários estruturados, permite edição de campos, salva com hash ANS correto e transmite via SOAP — tudo rodando no navegador.

## Requisitos

- Python 3.9+
- tkinter (para diálogos nativos de arquivo; geralmente já incluso na instalação padrão do Python)

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

```bash
python main_editor.py
```

O editor encontra automaticamente uma porta livre no intervalo configurado (padrão 54321–54400), inicia o servidor e abre o navegador. Para desativar a abertura automática ou alterar o intervalo de portas, edite `config.py`:

```python
EDITOR_PORTA_INICIAL = 54321
EDITOR_PORTA_FINAL = 54400
EDITOR_AUTO_ABRIR_BROWSER = True
```

## Estrutura do Projeto

```
editor/
├── app.py                  # FastAPI app factory
├── routes/
│   ├── xml_ops.py          # Carregar/salvar XML, renderizar formulários
│   ├── lote_ops.py         # Gerenciamento de lotes e envio SOAP
│   └── dialogs.py          # Diálogos de arquivo via tkinter headless
├── services/
│   ├── state.py            # Estado em memória (lotes e guias)
│   └── form_builder.py     # Conversão XML ↔ dict com preservação de namespaces
├── templates/
│   ├── base.html           # Template base com CSS e HTMX
│   ├── editor/
│   │   ├── guia_sadt.html
│   │   ├── guia_honorarios.html
│   │   ├── guia_resumo_internacao.html
│   │   └── components/     # Componentes reutilizáveis (cabeçalho, beneficiário, procedimentos)
│   └── lote/
│       ├── lista_guias.html
│       └── resultado_envio.html
└── static/
    ├── css/editor.css
    └── js/
        ├── htmx.min.js
        └── editor.js

main_editor.py              # Ponto de entrada (PyInstaller target)
config.py                   # Configurações globais
comunication/SoapClient.py  # Cliente SOAP TISS (legado)
services/TissResponseParser.py  # Parser de respostas TISS (legado)
```

## Testes

```bash
python -m pytest tests/editor/ -v
```

## Empacotamento (.exe)

```bash
pyinstaller --onefile --name ToolTissEditor \
  --add-data "editor/templates:editor/templates" \
  --add-data "editor/static:editor/static" \
  main_editor.py
```

O executável gerado estará em `dist/ToolTissEditor.exe`.

## Notas

- A transmissão SOAP (`enviar_lote`) requer Windows devido à dependência do módulo `nt` na cadeia de imports do `SoapClient`. Em Linux/macOS, o editor funciona normalmente para carga, edição e salvamento de XMLs; o endpoint de envio retorna erro 501 informando a indisponibilidade.
- O conversor `dict_to_xml` ainda está como stub (`NotImplementedError`). O salvamento de guias editadas de volta para XML será implementado em uma iteração futura.
- Todos os arquivos XML são processados com encoding ISO-8859-1 conforme exigido pelo padrão TISS.