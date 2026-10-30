# Editor de XML TISS — Design Spec

**Data:** 2026-10-30
**Status:** Aprovado para implementação
**Stack:** FastAPI + Jinja2 + HTMX + PyInstaller

## 1. Visão Geral

Editor local de guias TISS com interface web (browser), permitindo carregar XMLs existentes, editar campos via formulário estruturado, criar guias do zero e transmitir lotes via SOAP. Roda 100% na máquina do usuário como executável único.

### Casos de Uso Principais

1. **Correção rápida:** Usuário abre XML com erro/glosa, corrige campos específicos, reenvia
2. **Edição em lote:** Carrega pasta de XMLs, edita múltiplas guias, envia consolidado
3. **Criação manual:** Constrói guia do zero preenchendo formulário (secundário)

### Tipos de Guia Suportados (Fase 1)

- guiaSP-SADT
- guiaHonorarios
- guiaResumoInternacao

Outros tipos adicionados incrementalmente conforme necessidade.

## 2. Arquitetura

### Stack Técnica

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| Backend | FastAPI | Async, validação automática, reaproveita serviços existentes |
| Templates | Jinja2 | Renderização server-side, loops para tabelas dinâmicas |
| Interatividade | HTMX | Seções expansíveis, add/remove linhas sem JS pesado |
| Estilos | CSS puro | Sem build step, tema claro/escuro via variáveis |
| Empacotamento | PyInstaller | `.exe` único com templates + static embutidos |
| XML Parsing | ElementTree (stdlib) | Compatibilidade iso-8859-1, já usado no projeto |
| Transmissão | requests | Já usado em `SoapClient.py` |

### Estrutura de Diretórios

```
ToolTiss/
├── editor/                     # Novo módulo do editor
│   ├── __init__.py
│   ├── app.py                  # Instância FastAPI + startup/shutdown
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── xml_ops.py          # POST /carregar, POST /salvar, GET /formulario
│   │   ├── lote_ops.py         # GET /lote, POST /adicionar-guia, POST /enviar
│   │   └── dialogs.py          # GET /dialog/arquivo (tkinter headless)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── form_builder.py     # XML ↔ dict estruturado
│   │   ├── form_validator.py   # Validação de campos obrigatórios
│   │   └── state.py            # Estado em memória (guias abertas)
│   ├── templates/
│   │   ├── base.html
│   │   ├── editor/
│   │   │   ├── guia_sadt.html
│   │   │   ├── guia_honorarios.html
│   │   │   ├── guia_resumo_internacao.html
│   │   │   └── components/
│   │   │       ├── secao_cabecalho.html
│   │   │       ├── secao_beneficiario.html
│   │   │       ├── tabela_procedimentos.html
│   │   │       ├── tabela_despesas.html
│   │   │       └── campo_input.html
│   │   ├── lote/
│   │   │   ├── lista_guias.html
│   │   │   └── resultado_envio.html
│   │   └── partials/
│   │       ├── toast.html
│   │       └── modal_confirmacao.html
│   └── static/
│       ├── css/
│       │   └── editor.css
│       └── js/
│           └── editor.js       # Mínimo: inicialização HTMX, utilitários
├── services/                   # Existente (reaproveitado)
│   ├── TissXmlService.py
│   ├── TissResponseParser.py
│   └── DataExtractorService.py
├── comunication/               # Existente (reaproveitado)
│   └── SoapClient.py
├── config.py                   # Existente (estendido)
├── tooltiss.py                 # GUI atual (mantida, não modificada)
└── main_editor.py              # Entry point do editor (PyInstaller target)
```

### Ciclo de Vida da Aplicação

```
[main_editor.py]
    ↓
Inicia FastAPI em porta local aleatória (54321-54400)
    ↓
Abre browser padrão via webbrowser.open()
    ↓
Servidor roda até SIGINT/SIGTERM ou fechamento do browser
    ↓
Cleanup: fecha porta, libera recursos
```

## 3. Componentes

### 3.1 form_builder.py — Conversão XML ↔ Dict

Responsável por bidirecionalidade entre XML TISS e estrutura de dados Python.

**xml_to_dict(xml_path) → dict:**
- Parse com ElementTree, encoding iso-8859-1
- Preserva namespaces originais em metadata `_namespaces`
- Nós únicos → strings
- Nós repetidos (procedimentos, despesas, equipe) → listas de dicts
- Tag `<hash>` excluída do dict (recalculada ao salvar)
- Detecta tipo de guia via tag raiz (`guiaSP-SADT`, `guiaHonorarios`, `guiaResumoInternacao`)

**dict_to_xml(dados, output_path):**
- Reconstrói ElementTree a partir do dict
- Registra namespaces originais
- Chama `TissXmlService.atualizar_hash_tiss()` antes de serializar
- Grava com encoding iso-8859-1, xml_declaration=True

### 3.2 state.py — Gerenciamento de Sessão

Estado em memória (não persiste entre reinícios).

```python
class EditorState:
    lotes: dict[str, Lote]  # chave = lote_id

class Lote:
    id: str
    numero_lote: str
    guias: dict[str, GuiaDados]  # chave = guia_id
    caminho_origem: str | None  # se carregado de arquivo

class GuiaDados:
    id: str
    tipo: str  # "guiaSP-SADT" | "guiaHonorarios" | "guiaResumoInternacao"
    dados: dict  # estrutura do form_builder
    caminho_arquivo: str | None  # se carregado de XML existente
    modificado: bool  # flag para indicar alterações não salvas
```

### 3.3 Routes

#### xml_ops.py

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/dialog/arquivo` | Abre filedialog tkinter, retorna caminho JSON |
| POST | `/api/carregar-xml` | Recebe path, parse, armazena em state, retorna HTML do formulário |
| POST | `/api/salvar-xml` | Serializa dict → XML, recalcula hash, grava disco |
| GET | `/api/formulario/{guia_id}` | Renderiza template específico pelo tipo de guia |
| POST | `/api/atualizar-campo/{guia_id}` | Atualiza campo específico no state (HTMX parcial) |

#### lote_ops.py

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/lote/{lote_id}` | Lista guias do lote (sidebar) |
| POST | `/api/lote/{lote_id}/adicionar-guia` | Cria nova guia vazia ou carrega de XML |
| DELETE | `/api/lote/{lote_id}/guia/{guia_id}` | Remove guia do lote |
| POST | `/api/lote/{lote_id}/enviar` | Envia todas as guias do lote via SOAP |
| GET | `/api/lote/{lote_id}/resultado` | Renderiza tabela de resultados pós-envio |

#### dialogs.py

Endpoints que interagem com SO via tkinter headless:
- `/api/dialog/arquivo` — Selecionar arquivo XML
- `/api/dialog/pasta` — Selecionar pasta de XMLs
- `/api/dialog/salvar-como` — Escolher destino para salvar

Retornam JSON `{"caminho": "/path/to/file"}` ou `{"cancelado": true}`.

### 3.4 Templates

#### base.html

Layout comum: sidebar (lista de guias do lote) + área principal (formulário). Inclui HTMX via CDN local (arquivo em static/js/htmx.min.js embutido no PyInstaller).

#### guia_sadt.html

Seções expansíveis via `<details>` HTML5:
1. **Cabeçalho da Guia** — registroANS, numeroGuiaPrestador, guiaPrincipal
2. **Dados de Autorização** — numeroGuiaOperadora, dataAutorizacao, senha
3. **Dados do Beneficiário** — numeroCarteira, atendimentoRN
4. **Dados do Solicitante** — contratadoSolicitante, profissionalSolicitante
5. **Procedimentos Executados** — Tabela dinâmica com HTMX (add/remove linhas)
6. **Outras Despesas** — Tabela dinâmica similar
7. **Dados de Atendimento** — tipoAtendimento, indicacaoAcidente, regimeAtendimento

#### guia_honorarios.html

Mesma estrutura base, seções específicas:
- Dados do Profissional Executante
- Procedimentos Realizados (tabela)
- Valores Totais

#### guia_resumo_internacao.html

Seções específicas:
- Dados da Internação (caráter, tipo, datas)
- Diagnósticos (tabela CID)
- Procedimentos Realizados (tabela)
- Equipe Médica (tabela)
- Valores Totais

#### tabela_procedimentos.html (componente reutilizável)

```html
<table class="tabela-dinamica">
  <thead>
    <tr>
      <th>Seq</th><th>Data</th><th>Hora Início</th><th>Hora Fim</th>
      <th>Código</th><th>Descrição</th><th>Qtd</th><th>Valor Unit.</th>
      <th>Valor Total</th><th>Ações</th>
    </tr>
  </thead>
  <tbody id="procedimentos-body">
    {% for proc in procedimentos %}
    <tr>
      <td><input name="procedimentos[{{ loop.index0 }}][sequencialItem]" value="{{ proc.sequencialItem }}"></td>
      <!-- ... demais campos ... -->
      <td>
        <button hx-post="/api/remover-procedimento/{{ guia_id }}/{{ loop.index0 }}"
                hx-target="closest tr" hx-swap="outerHTML">🗑️</button>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
<button hx-post="/api/adicionar-procedimento/{{ guia_id }}"
        hx-target="#procedimentos-body" hx-swap="beforeend">+ Adicionar Procedimento</button>
```

## 4. Fluxo de Dados

### Carregar e Editar XML Existente

```
Usuário clica "Abrir XML"
  → GET /api/dialog/arquivo (tkinter filedialog)
  → Retorna {"caminho": "/path/to/file.xml"}
  → POST /api/carregar-xml {caminho: "..."}
  → Backend: form_builder.xml_to_dict() → state.armazenar()
  → Retorna HTML do formulário renderizado via Jinja2
  → Usuário edita campos
  → HTMX: POST /api/atualizar-campo/{guia_id} (FormData)
  → Backend: atualiza dict em state, retorna HTML parcial do campo
```

### Salvar Alterações

```
Usuário clica "Salvar"
  → POST /api/salvar-xml {guia_id: "...", caminho_saida: "..."}
  → Backend: form_builder.dict_to_xml(state.get(guia_id))
  → TissXmlService.atualizar_hash_tiss(root)
  → tree.write(caminho_saida, encoding="iso-8859-1")
  → Retorna JSON {"sucesso": true, "hash": "..."}
  → Frontend: exibe toast de sucesso
```

### Enviar Lote

```
Usuário clica "Enviar Lote"
  → POST /api/lote/{lote_id}/enviar
  → Backend: para cada guia no lote:
      1. dict_to_xml() → XML temporário
      2. SoapClient.enviar_lote(xml_temp, url, action)
      3. TissResponseParser.parse(resposta)
      4. Acumula resultados
  → Gera relatório CSV via TissResponseParser.gerar_relatorio_csv()
  → Retorna HTML da tabela de resultados (template resultado_envio.html)
  → Frontend: substitui área principal com tabela de status/glosas
```

## 5. Integração com Código Existente

### Reaproveitamento Direto

| Módulo Existente | Uso no Editor |
|-----------------|---------------|
| `TissXmlService.atualizar_hash_tiss()` | Recálculo de hash ao salvar |
| `TissXmlService.preparar_conteudo_xml()` | Limpeza estrutural antes do envio |
| `TissSoapClient.enviar_lote()` | Transmissão SOAP |
| `TissResponseParser.parse()` | Extração de resultados |
| `TissResponseParser.gerar_relatorio_csv()` | Relatório consolidado |
| `config.py` | URLs, timeouts, flags globais |

### Extensões Necessárias em config.py

```python
# Novas configurações para o editor
EDITOR_PORTA_INICIAL = 54321
EDITOR_PORTA_FINAL = 54400
EDITOR_AUTO_ABRIR_BROWSER = True
EDITOR_TEMA_PADRAO = "light"  # "light" | "dark"
```

## 6. Empacotamento

### PyInstaller Spec

```bash
python -m PyInstaller \
  --clean --noconsole --onefile \
  --collect-all customtkinter \
  --add-data "editor/templates;editor/templates" \
  --add-data "editor/static;editor/static" \
  --add-data "manual.pdf;." \
  -n "ToolTissEditor" \
  -i "bateria.ico" \
  main_editor.py
```

### main_editor.py (Entry Point)

```python
import sys, os, webbrowser, socket, threading
from editor.app import create_app

def encontrar_porta_livre(inicio=54321, fim=54400):
    for porta in range(inicio, fim + 1):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", porta))
                return porta
            except OSError:
                continue
    raise RuntimeError("Nenhuma porta livre encontrada")

if __name__ == "__main__":
    porta = encontrar_porta_livre()
    app = create_app()

    # Abre browser após servidor iniciar
    def abrir_browser():
        webbrowser.open(f"http://127.0.0.1:{porta}")

    threading.Timer(1.5, abrir_browser).start()

    # uvicorn.run bloqueia até encerramento
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")
```

## 7. Restrições e Decisões

1. **Encoding:** Todo I/O XML usa iso-8859-1. Hash MD5 calculado sobre bytes iso-8859-1. Não alterar.
2. **Namespace preservation:** form_builder deve preservar prefixos originais. ElementTree renomeia para ns0/ns1 sem registro explícito.
3. **Estado em memória:** Sem banco de dados. Guias abertas perdidas ao fechar app. Aceitável para uso local.
4. **Sem autenticação:** App roda apenas em localhost. Sem risco de acesso externo.
5. **HTMX via arquivo local:** htmx.min.js incluído em static/, não via CDN. Funciona offline.
6. **CustomTkinter mantido:** GUI original (`tooltiss.py`) não é modificada. Editor é entry point separado.
7. **Autocomplete futuro:** Estrutura de dados já prevê campos de busca (codigoProcedimento, CID), mas UI de autocomplete implementada apenas quando necessário.

## 8. Fora do Escopo (Fase 1)

- Autocomplete/busca por CID, CBOS, código procedimento
- Validação em tempo real contra schema XSD
- Histórico de alterações / undo-redo
- Persistência de estado entre sessões
- Multi-usuário / rede
- Assinatura digital XML-DSig
- Importação/exportação de planilhas Excel no editor
- Modo escuro (implementar apenas se solicitado)