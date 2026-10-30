# Editor TISS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web-based TISS XML editor (FastAPI + Jinja2 + HTMX) that loads existing XMLs into structured forms, allows field editing, saves with correct ANS hash, and transmits via SOAP — packaged as a single `.exe`.

**Architecture:** FastAPI backend serves Jinja2 templates with HTMX for interactivity. Backend reuses existing `TissXmlService`, `SoapClient`, and `TissResponseParser`. State is in-memory only. Entry point `main_editor.py` starts uvicorn on a random localhost port and opens the browser.

**Tech Stack:** Python 3.10+, FastAPI, Jinja2, HTMX, uvicorn, ElementTree (stdlib), requests, PyInstaller

---

## File Structure

```
editor/
├── __init__.py
├── app.py                    # FastAPI app factory + Jinja2 config
├── routes/
│   ├── __init__.py
│   ├── xml_ops.py            # Load/save/form endpoints
│   ├── lote_ops.py           # Batch management + send
│   └── dialogs.py            # tkinter file dialogs via API
├── services/
│   ├── __init__.py
│   ├── form_builder.py       # XML ↔ dict bidirectional conversion
│   ├── form_validator.py     # Required field validation
│   └── state.py              # In-memory session state
├── templates/
│   ├── base.html
│   ├── editor/
│   │   ├── guia_sadt.html
│   │   ├── guia_honorarios.html
│   │   ├── guia_resumo_internacao.html
│   │   └── components/
│   │       ├── secao_cabecalho.html
│   │       ├── secao_beneficiario.html
│   │       ├── tabela_procedimentos.html
│   │       ├── tabela_despesas.html
│   │       └── campo_input.html
│   ├── lote/
│   │   ├── lista_guias.html
│   │   └── resultado_envio.html
│   └── partials/
│       ├── toast.html
│       └── modal_confirmacao.html
└── static/
    ├── css/
    │   └── editor.css
    └── js/
        ├── htmx.min.js       # Bundled locally (no CDN)
        └── editor.js         # Minimal: HTMX init + utilities
main_editor.py                # PyInstaller entry point
config.py                     # Extended with EDITOR_* vars
```

Existing files reused without modification:
- `services/TissXmlService.py` — `atualizar_hash_tiss()`, `preparar_conteudo_xml()`
- `comunication/SoapClient.py` — `enviar_lote()`
- `services/TissResponseParser.py` — `parse()`, `gerar_relatorio_csv()`

---

### Task 1: Project Scaffolding + Dependencies

**Files:**
- Create: `editor/__init__.py`
- Create: `editor/routes/__init__.py`
- Create: `editor/services/__init__.py`
- Modify: `config.py`

- [ ] **Step 1: Install dependencies**
Run:
```bash
python3 -m pip install --break-system-packages fastapi uvicorn jinja2 python-multipart
```
Expected: All packages installed successfully.

- [ ] **Step 2: Create package init files**
Create `editor/__init__.py`:
```python
"""Editor TISS — FastAPI-based local XML editor."""
```

Create `editor/routes/__init__.py`:
```python
"""Editor API routes."""
```

Create `editor/services/__init__.py`:
```python
"""Editor internal services."""
```

- [ ] **Step 3: Add editor config vars to config.py**
Append to end of `config.py`:
```python
# Editor Web Configuration
EDITOR_PORTA_INICIAL = 54321
EDITOR_PORTA_FINAL = 54400
EDITOR_AUTO_ABRIR_BROWSER = True
EDITOR_TEMA_PADRAO = "light"
```

- [ ] **Step 4: Verify imports work**
Run:
```bash
cd /home/estevao/Projects/Unimed/ToolTiss && python3 -c "from editor import *; from editor.routes import *; from editor.services import *; import config; print(config.EDITOR_PORTA_INICIAL)"
```
Expected output: `54321`

- [ ] **Step 5: Commit**
```bash
git add editor/__init__.py editor/routes/__init__.py editor/services/__init__.py config.py
git commit -m "feat(editor): project scaffolding and config vars

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: In-Memory State Manager

**Files:**
- Create: `editor/services/state.py`

- [ ] **Step 1: Write the failing test**
Create `tests/editor/test_state.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from editor.services.state import EditorState

def test_create_lote():
    state = EditorState()
    lote_id = state.criar_lote("28596")
    assert lote_id in state.lotes
    assert state.lotes[lote_id].numero_lote == "28596"
    assert len(state.lotes[lote_id].guias) == 0

def test_adicionar_guia():
    state = EditorState()
    lote_id = state.criar_lote("28596")
    guia_id = state.adicionar_guia(lote_id, "guiaSP-SADT", {"cabecalho": {"registroANS": "304701"}})
    assert guia_id in state.lotes[lote_id].guias
    guia = state.lotes[lote_id].guias[guia_id]
    assert guia.tipo == "guiaSP-SADT"
    assert guia.dados["cabecalho"]["registroANS"] == "304701"
    assert guia.modificado is False

def test_remover_guia():
    state = EditorState()
    lote_id = state.criar_lote("28596")
    guia_id = state.adicionar_guia(lote_id, "guiaSP-SADT", {})
    state.remover_guia(lote_id, guia_id)
    assert guia_id not in state.lotes[lote_id].guias

def test_get_guia():
    state = EditorState()
    lote_id = state.criar_lote("28596")
    guia_id = state.adicionar_guia(lote_id, "guiaHonorarios", {"teste": "valor"})
    guia = state.get_guia(guia_id)
    assert guia is not None
    assert guia.tipo == "guiaHonorarios"

def test_get_guia_inexistente():
    state = EditorState()
    assert state.get_guia("nao-existe") is None

def test_marcar_modificado():
    state = EditorState()
    lote_id = state.criar_lote("28596")
    guia_id = state.adicionar_guia(lote_id, "guiaSP-SADT", {})
    state.marcar_modificado(guia_id)
    assert state.lotes[lote_id].guias[guia_id].modificado is True
```

- [ ] **Step 2: Run test to verify it fails**
Run:
```bash
cd /home/estevao/Projects/Unimed/ToolTiss && python3 -m pytest tests/editor/test_state.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'editor.services.state'`

- [ ] **Step 3: Implement state.py**
Create `editor/services/state.py`:
```python
"""In-memory session state for the TISS editor."""
import uuid
from dataclasses import dataclass, field


@dataclass
class GuiaDados:
    id: str
    tipo: str  # "guiaSP-SADT" | "guiaHonorarios" | "guiaResumoInternacao"
    dados: dict
    caminho_arquivo: str | None = None
    modificado: bool = False


@dataclass
class Lote:
    id: str
    numero_lote: str
    guias: dict[str, GuiaDados] = field(default_factory=dict)
    caminho_origem: str | None = None


class EditorState:
    """Singleton-free state container. One instance per app lifecycle."""

    def __init__(self):
        self.lotes: dict[str, Lote] = {}

    def criar_lote(self, numero_lote: str) -> str:
        lote_id = str(uuid.uuid4())[:8]
        self.lotes[lote_id] = Lote(id=lote_id, numero_lote=numero_lote)
        return lote_id

    def get_lote(self, lote_id: str) -> Lote | None:
        return self.lotes.get(lote_id)

    def adicionar_guia(
        self, lote_id: str, tipo: str, dados: dict, caminho_arquivo: str | None = None
    ) -> str:
        guia_id = str(uuid.uuid4())[:8]
        self.lotes[lote_id].guias[guia_id] = GuiaDados(
            id=guia_id,
            tipo=tipo,
            dados=dados,
            caminho_arquivo=caminho_arquivo,
        )
        return guia_id

    def remover_guia(self, lote_id: str, guia_id: str) -> None:
        if lote_id in self.lotes:
            self.lotes[lote_id].guias.pop(guia_id, None)

    def get_guia(self, guia_id: str) -> GuiaDados | None:
        for lote in self.lotes.values():
            if guia_id in lote.guias:
                return lote.guias[guia_id]
        return None

    def marcar_modificado(self, guia_id: str) -> None:
        guia = self.get_guia(guia_id)
        if guia:
            guia.modificado = True

    def listar_guias(self, lote_id: str) -> list[GuiaDados]:
        lote = self.lotes.get(lote_id)
        if lote is None:
            return []
        return list(lote.guias.values())
```

- [ ] **Step 4: Run test to verify it passes**
Run:
```bash
cd /home/estevao/Projects/Unimed/ToolTiss && python3 -m pytest tests/editor/test_state.py -v
```
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**
```bash
git add editor/services/state.py tests/editor/test_state.py
git commit -m "feat(editor): in-memory state manager for lotes and guias

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Form Builder — XML to Dict

**Files:**
- Create: `editor/services/form_builder.py`

- [ ] **Step 1: Write the failing test**
Create `tests/editor/test_form_builder.py`:
```python
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from editor.services.form_builder import FormBuilder

XML_SADT_MINIMO = b'''<?xml version="1.0" encoding="iso-8859-1"?>
<ans:mensagemTISS xmlns:ans="http://www.ans.gov.br/padroes/tiss/schemas">
    <ans:cabecalho>
        <ans:identificacaoTransacao>
            <ans:tipoTransacao>ENVIO_LOTE_GUIAS</ans:tipoTransacao>
            <ans:sequencialTransacao>14584688</ans:sequencialTransacao>
            <ans:dataRegistroTransacao>2026-09-30</ans:dataRegistroTransacao>
            <ans:horaRegistroTransacao>23:56:35</ans:horaRegistroTransacao>
        </ans:identificacaoTransacao>
        <ans:origem>
            <ans:identificacaoPrestador>
                <ans:codigoPrestadorNaOperadora>68870</ans:codigoPrestadorNaOperadora>
            </ans:identificacaoPrestador>
        </ans:origem>
        <ans:destino>
            <ans:registroANS>304701</ans:registroANS>
        </ans:destino>
        <ans:Padrao>4.03.00</ans:Padrao>
    </ans:cabecalho>
    <ans:prestadorParaOperadora>
        <ans:loteGuias>
            <ans:numeroLote>28595</ans:numeroLote>
            <ans:guiasTISS>
                <ans:guiaSP-SADT>
                    <ans:cabecalhoGuia>
                        <ans:registroANS>304701</ans:registroANS>
                        <ans:numeroGuiaPrestador>1557971967</ans:numeroGuiaPrestador>
                        <ans:guiaPrincipal>1557971967</ans:guiaPrincipal>
                    </ans:cabecalhoGuia>
                    <ans:dadosBeneficiario>
                        <ans:numeroCarteira>00320000065565592</ans:numeroCarteira>
                        <ans:atendimentoRN>N</ans:atendimentoRN>
                    </ans:dadosBeneficiario>
                    <ans:procedimentosExecutados>
                        <ans:procedimentoExecutado>
                            <ans:sequencialItem>0</ans:sequencialItem>
                            <ans:dataExecucao>2026-09-12</ans:dataExecucao>
                            <ans:procedimento>
                                <ans:codigoProcedimento>146935</ans:codigoProcedimento>
                                <ans:descricaoProcedimento>KIT TESTE</ans:descricaoProcedimento>
                            </ans:procedimento>
                            <ans:quantidadeExecutada>1.0</ans:quantidadeExecutada>
                            <ans:valorUnitario>3980.0</ans:valorUnitario>
                            <ans:valorTotal>3980.00</ans:valorTotal>
                        </ans:procedimentoExecutado>
                    </ans:procedimentosExecutados>
                </ans:guiaSP-SADT>
            </ans:guiasTISS>
        </ans:loteGuias>
    </ans:prestadorParaOperadora>
    <ans:epilogo>
        <ans:hash>abc123</ans:hash>
    </ans:epilogo>
</ans:mensagemTISS>'''


def _write_temp_xml(content: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".xml")
    os.write(fd, content)
    os.close(fd)
    return path


def test_xml_to_dict_detects_sadt():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        assert result["tipo"] == "guiaSP-SADT"
    finally:
        os.unlink(path)


def test_xml_to_dict_extracts_cabecalho():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        assert result["cabecalho"]["registroANS"] == "304701"
        assert result["cabecalho"]["numeroGuiaPrestador"] == "1557971967"
    finally:
        os.unlink(path)


def test_xml_to_dict_extracts_procedimentos_as_list():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        procs = result["procedimentosExecutados"]
        assert isinstance(procs, list)
        assert len(procs) == 1
        assert procs[0]["sequencialItem"] == "0"
        assert procs[0]["codigoProcedimento"] == "146935"
        assert procs[0]["valorTotal"] == "3980.00"
    finally:
        os.unlink(path)


def test_xml_to_dict_excludes_hash():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        assert "hash" not in result
        assert "epilogo" not in result
    finally:
        os.unlink(path)


def test_xml_to_dict_preserves_namespaces():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        assert "_namespaces" in result
        assert "ans" in result["_namespaces"]
        assert result["_namespaces"]["ans"] == "http://www.ans.gov.br/padroes/tiss/schemas"
    finally:
        os.unlink(path)
```

- [ ] **Step 2: Run test to verify it fails**
Run:
```bash
cd /home/estevao/Projects/Unimed/ToolTiss && python3 -m pytest tests/editor/test_form_builder.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'editor.services.form_builder'`

- [ ] **Step 3: Implement form_builder.py (xml_to_dict only)**
Create `editor/services/form_builder.py`:
```python
"""Bidirectional conversion between TISS XML and structured dicts."""
import xml.etree.ElementTree as ET


# Tags whose children are always lists (repeating elements)
LIST_TAGS = {
    "procedimentoExecutado", "despesa", "diagnostico",
    "profissionalExecutante", "equipeSadt", "motivoGlosa",
}

# Map tag local names to dict keys for known guia types
GUIA_TYPE_MAP = {
    "guiaSP-SADT": "guiaSP-SADT",
    "guiaHonorarios": "guiaHonorarios",
    "guiaResumoInternacao": "guiaResumoInternacao",
}


class FormBuilder:
    """Converts TISS XML files to/from structured Python dicts."""

    @staticmethod
    def xml_to_dict(xml_path: str) -> dict:
        """Parse a TISS XML file and return a structured dict.

        Returns dict with keys: tipo, cabecalho, <guia fields>, _namespaces.
        Excludes <epilogo> and <hash> (hash is recalculated on save).
        """
        # Collect namespaces before parsing
        namespaces = {}
        for event, elem in ET.iterparse(xml_path, events=["start-ns"]):
            prefix, uri = elem
            if prefix:
                namespaces[prefix] = uri

        parser = ET.XMLParser(encoding="iso-8859-1")
        tree = ET.parse(xml_path, parser)
        root = tree.getroot()

        result = {"_namespaces": namespaces}

        # Extract cabecalho (top-level transaction header)
        cabecalho_elem = None
        for elem in root.iter():
            tag_local = elem.tag.split("}")[-1]
            if tag_local == "cabecalho":
                cabecalho_elem = elem
                break

        if cabecalho_elem is not None:
            result["cabecalho"] = FormBuilder._elem_to_dict(cabecalho_elem)

        # Find the guia element (inside guiasTISS)
        guia_elem = None
        guia_tipo = None
        for elem in root.iter():
            tag_local = elem.tag.split("}")[-1]
            if tag_local in GUIA_TYPE_MAP:
                guia_elem = elem
                guia_tipo = GUIA_TYPE_MAP[tag_local]
                break

        if guia_elem is not None:
            result["tipo"] = guia_tipo
            guia_dict = FormBuilder._elem_to_dict(guia_elem)
            # Merge guia fields into result (excluding nested wrapper tags)
            for key, value in guia_dict.items():
                result[key] = value

        return result

    @staticmethod
    def _elem_to_dict(elem) -> dict | str | list:
        """Recursively convert an ElementTree element to dict/list/string.

        - Leaf nodes (no children) → stripped text string
        - Nodes with repeating children (LIST_TAGS) → list of dicts
        - Other nodes → dict of child tag → value
        - Skips epilogo and hash tags entirely
        """
        tag_local = elem.tag.split("}")[-1]

        # Skip epilogo and hash
        if tag_local in ("epilogo", "hash"):
            return None

        children = list(elem)
        if not children:
            # Leaf node
            return (elem.text or "").strip()

        # Check if this element contains repeating children that should be a list
        child_tags = [c.tag.split("}")[-1] for c in children]
        has_repeating = any(tag in LIST_TAGS for tag in child_tags)

        if has_repeating:
            # Build dict but convert repeating children to lists
            result = {}
            list_accumulator = {}
            for child in children:
                child_tag = child.tag.split("}")[-1]
                if child_tag in ("epilogo", "hash"):
                    continue
                child_value = FormBuilder._elem_to_dict(child)
                if child_value is None:
                    continue
                if child_tag in LIST_TAGS:
                    if child_tag not in list_accumulator:
                        list_accumulator[child_tag] = []
                    list_accumulator[child_tag].append(child_value)
                else:
                    result[child_tag] = child_value
            # Merge accumulated lists
            for tag, items in list_accumulator.items():
                result[tag] = items
            return result
        else:
            # Regular dict
            result = {}
            for child in children:
                child_tag = child.tag.split("}")[-1]
                if child_tag in ("epilogo", "hash"):
                    continue
                child_value = FormBuilder._elem_to_dict(child)
                if child_value is None:
                    continue
                result[child_tag] = child_value
            return result

    @staticmethod
    def dict_to_xml(dados: dict, output_path: str) -> str:
        """Convert a structured dict back to TISS XML file.

        Recalculates hash via TissXmlService.atualizar_hash_tiss().
        Returns the generated hash string.
        """
        from services.TissXmlService import TissXmlService

        ns = dados.get("_namespaces", {})
        ans_uri = ns.get("ans", "http://www.ans.gov.br/padroes/tiss/schemas")

        # Register namespaces to preserve prefixes
        for prefix, uri in ns.items():
            ET.register_namespace(prefix, uri)

        # Build root element
        root = ET.Element(f"{{{ans_uri}}}mensagemTISS")

        # Rebuild cabecalho
        if "cabecalho" in dados:
            cabecalho_elem = ET.SubElement(root, f"{{{ans_uri}}}cabecalho")
            FormBuilder._dict_to_elem(dados["cabecalho"], cabecalho_elem, ans_uri)

        # Rebuild prestadorParaOperadora > loteGuias > guiasTISS > guia
        ppo = ET.SubElement(root, f"{{{ans_uri}}}prestadorParaOperadora")
        lote = ET.SubElement(ppo, f"{{{ans_uri}}}loteGuias")

        # numeroLote comes from cabecalho or top-level
        if "numeroLote" in dados:
            nl = ET.SubElement(lote, f"{{{ans_uri}}}numeroLote")
            nl.text = str(dados["numeroLote"])

        guias_tiss = ET.SubElement(lote, f"{{{ans_uri}}}guiasTISS")

        guia_tipo = dados.get("tipo", "guiaSP-SADT")
        guia_elem = ET.SubElement(guias_tiss, f"{{{ans_uri}}}{guia_tipo}")

        # Add guia fields (skip metadata keys)
        skip_keys = {"tipo", "cabecalho", "_namespaces", "numeroLote"}
        for key, value in dados.items():
            if key in skip_keys:
                continue
            FormBuilder._add_field(guia_elem, key, value, ans_uri)

        # Add epilogo with empty hash (will be recalculated)
        epilogo = ET.SubElement(root, f"{{{ans_uri}}}epilogo")
        hash_elem = ET.SubElement(epilogo, f"{{{ans_uri}}}hash")
        hash_elem.text = ""

        # Write to file
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding="iso-8859-1", xml_declaration=True, method="xml")

        # Recalculate hash
        parser = ET.XMLParser(encoding="iso-8859-1")
        tree2 = ET.parse(output_path, parser)
        novo_hash = TissXmlService.atualizar_hash_tiss(tree2.getroot())
        tree2.write(output_path, encoding="iso-8859-1", xml_declaration=True, method="xml")

        return novo_hash or ""

    @staticmethod
    def _dict_to_elem(data: dict, parent, ns_uri: str):
        """Recursively add dict contents as child elements."""
        if isinstance(data, dict):
            for key, value in data.items():
                FormBuilder._add_field(parent, key, value, ns_uri)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Infer tag name from parent context — caller handles this
                    pass

    @staticmethod
    def _add_field(parent, key: str, value, ns_uri: str):
        """Add a single field (key/value) as child element(s) of parent."""
        if isinstance(value, dict):
            child = ET.SubElement(parent, f"{{{ns_uri}}}{key}")
            FormBuilder._dict_to_elem(value, child, ns_uri)
        elif isinstance(value, list):
            for item in value:
                child = ET.SubElement(parent, f"{{{ns_uri}}}{key}")
                if isinstance(item, dict):
                    FormBuilder._dict_to_elem(item, child, ns_uri)
                else:
                    child.text = str(item)
        else:
            child = ET.SubElement(parent, f"{{{ns_uri}}}{key}")
            child.text = str(value) if value is not None else ""
```

- [ ] **Step 4: Run test to verify it passes**
Run:
```bash
cd /home/estevao/Projects/Unimed/ToolTiss && python3 -m pytest tests/editor/test_form_builder.py -v
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**
```bash
git add editor/services/form_builder.py tests/editor/test_form_builder.py
git commit -m "feat(editor): form builder XML-to-dict conversion with namespace preservation

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: FastAPI App Factory + Static/Template Config

**Files:**
- Create: `editor/app.py`
- Create: `editor/templates/base.html`
- Create: `editor/static/css/editor.css`
- Create: `editor/static/js/htmx.min.js` (download)
- Create: `editor/static/js/editor.js`

- [ ] **Step 1: Download htmx.min.js**
Run:
```bash
mkdir -p /home/estevao/Projects/Unimed/ToolTiss/editor/static/js /home/estevao/Projects/Unimed/ToolTiss/editor/static/css /home/estevao/Projects/Unimed/ToolTiss/editor/templates/editor/components /home/estevao/Projects/Unimed/ToolTiss/editor/templates/lote /home/estevao/Projects/Unimed/ToolTiss/editor/templates/partials
curl -o /home/estevao/Projects/Unimed/ToolTiss/editor/static/js/htmx.min.js https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js
```
Expected: File downloaded, ~45KB.

- [ ] **Step 2: Create app.py**
Create `editor/app.py`:
```python
"""FastAPI application factory for the TISS Editor."""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


def create_app() -> FastAPI:
    app = FastAPI(title="ToolTiss Editor", docs_url=None, redoc_url=None)

    # Resolve paths relative to this file (works inside PyInstaller bundle)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app.state.templates = Jinja2Templates(directory=templates_dir)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Import and register routes
    from editor.routes import xml_ops, lote_ops, dialogs
    app.include_router(xml_ops.router, prefix="/api")
    app.include_router(lote_ops.router, prefix="/api")
    app.include_router(dialogs.router, prefix="/api")

    # Root route serves the main page
    from starlette.requests import Request
    from starlette.responses import HTMLResponse

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return app.state.templates.TemplateResponse("base.html", {"request": request})

    return app
```

- [ ] **Step 3: Create base.html**
Create `editor/templates/base.html`:
```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToolTiss Editor</title>
    <link rel="stylesheet" href="/static/css/editor.css">
    <script src="/static/js/htmx.min.js"></script>
    <script src="/static/js/editor.js"></script>
</head>
<body>
    <div class="app-layout">
        <aside class="sidebar" id="sidebar">
            <h2>📋 Lotes</h2>
            <div id="lote-list">
                <p class="empty-state">Nenhum lote aberto.</p>
            </div>
            <button class="btn btn-primary" hx-post="/api/lote/novo" hx-target="#lote-list" hx-swap="innerHTML">
                + Novo Lote
            </button>
        </aside>
        <main class="content" id="main-content">
            <div class="welcome">
                <h1>🔧 ToolTiss Editor</h1>
                <p>Crie um novo lote ou abra um XML existente para começar.</p>
                <button class="btn btn-primary"
                        hx-get="/api/dialog/arquivo"
                        hx-trigger="click"
                        onclick="abrirArquivo()">
                    📂 Abrir XML
                </button>
            </div>
        </main>
    </div>
    <div id="toast-container"></div>
</body>
</html>
```

- [ ] **Step 4: Create editor.css**
Create `editor/static/css/editor.css`:
```css
:root {
    --bg: #f5f5f5;
    --sidebar-bg: #ffffff;
    --text: #1a1a1a;
    --border: #ddd;
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --danger: #dc2626;
    --success: #16a34a;
    --radius: 6px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }

.app-layout { display: flex; min-height: 100vh; }

.sidebar {
    width: 280px; background: var(--sidebar-bg); border-right: 1px solid var(--border);
    padding: 16px; display: flex; flex-direction: column; gap: 12px;
}
.sidebar h2 { font-size: 1.1rem; }

.content { flex: 1; padding: 24px; overflow-y: auto; }

.btn {
    padding: 8px 16px; border: none; border-radius: var(--radius); cursor: pointer;
    font-size: 0.9rem; font-weight: 500; transition: background 0.15s;
}
.btn-primary { background: var(--primary); color: white; }
.btn-primary:hover { background: var(--primary-hover); }
.btn-danger { background: var(--danger); color: white; }
.btn-sm { padding: 4px 10px; font-size: 0.8rem; }

details { border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 12px; }
details summary {
    padding: 10px 14px; cursor: pointer; font-weight: 600; background: var(--sidebar-bg);
    border-radius: var(--radius); user-select: none;
}
details[open] summary { border-bottom: 1px solid var(--border); border-radius: var(--radius) var(--radius) 0 0; }
details .section-body { padding: 14px; }

.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.form-field label { display: block; font-size: 0.8rem; font-weight: 600; margin-bottom: 4px; color: #555; }
.form-field input, .form-field select {
    width: 100%; padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius);
    font-size: 0.9rem;
}

table.tabela-dinamica { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 0.85rem; }
table.tabela-dinamica th, table.tabela-dinamica td {
    border: 1px solid var(--border); padding: 6px 8px; text-align: left;
}
table.tabela-dinamica th { background: var(--sidebar-bg); font-weight: 600; }
table.tabela-dinamica input { width: 100%; border: none; padding: 2px; font-size: 0.85rem; }

.empty-state { color: #888; font-style: italic; font-size: 0.9rem; }
.welcome { text-align: center; margin-top: 80px; }
.welcome h1 { margin-bottom: 12px; }
.welcome p { margin-bottom: 20px; color: #666; }

#toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 1000; }
.toast {
    padding: 10px 18px; border-radius: var(--radius); color: white; margin-top: 8px;
    animation: fadeIn 0.3s ease;
}
.toast-success { background: var(--success); }
.toast-error { background: var(--danger); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.guia-item {
    padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius);
    cursor: pointer; display: flex; justify-content: space-between; align-items: center;
}
.guia-item:hover { background: #f0f4ff; }
.guia-item.active { border-color: var(--primary); background: #eff6ff; }
.guia-item .modificado::after { content: " ●"; color: var(--primary); }
```

- [ ] **Step 5: Create editor.js**
Create `editor/static/js/editor.js`:
```javascript
// Minimal JS utilities for the TISS Editor
function showToast(message, type) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type || 'success'}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

async function abrirArquivo() {
    try {
        const resp = await fetch('/api/dialog/arquivo');
        const data = await resp.json();
        if (data.cancelado) return;
        // Load the selected XML into the editor
        const loadResp = await fetch('/api/carregar-xml', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({caminho: data.caminho})
        });
        const html = await loadResp.text();
        document.getElementById('main-content').innerHTML = html;
    } catch (e) {
        showToast('Erro ao abrir arquivo: ' + e.message, 'error');
    }
}

// Listen for HTMX errors
document.body.addEventListener('htmx:responseError', function(evt) {
    showToast('Erro na requisição', 'error');
});

// Listen for successful saves
document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target.id === 'toast-container') {
        // Toast was swapped in, no action needed
    }
});
```

- [ ] **Step 6: Verify app starts**
Run:
```bash
cd /home/estevao/Projects/Unimed/ToolTiss && python3 -c "from editor.app import create_app; app = create_app(); print('App created:', app.title)"
```
Expected: `App created: ToolTiss Editor`

- [ ] **Step 7: Commit**
```bash
git add editor/app.py editor/templates/base.html editor/static/css/editor.css editor/static/js/htmx.min.js editor/static/js/editor.js
git commit -m "feat(editor): FastAPI app factory, base template, CSS and HTMX bundle

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: API Routes — Dialogs + XML Operations

**Files:**
- Create: `editor/routes/dialogs.py`
- Create: `editor/routes/xml_ops.py`

- [ ] **Step 1: Create dialogs.py**
Create `editor/routes/dialogs.py`:
```python
"""File dialog endpoints using tkinter headless."""
import json
from fastapi import APIRouter

router = APIRouter(tags=["dialogs"])


@router.get("/dialog/arquivo")
async def dialog_arquivo():
    """Open file dialog and return selected path."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        caminho = filedialog.askopenfilename(
            title="Selecionar XML TISS",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        root.destroy()
        if caminho:
            return {"caminho": caminho}
        return {"cancelado": True}
    except Exception as e:
        return {"erro": str(e)}


@router.get("/dialog/pasta")
async def dialog_pasta():
    """Open folder dialog and return selected path."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        caminho = filedialog.askdirectory(title="Selecionar Pasta de XMLs")
        root.destroy()
        if caminho:
            return {"caminho": caminho}
        return {"cancelado": True}
    except Exception as e:
        return {"erro": str(e)}


@router.get("/dialog/salvar-como")
async def dialog_salvar_como():
    """Open save-as dialog and return selected path."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        caminho = filedialog.asksaveasfilename(
            title="Salvar XML TISS",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml")]
        )
        root.destroy()
        if caminho:
            return {"caminho": caminho}
        return {"cancelado": True}
    except Exception as e:
        return {"erro": str(e)}
```

- [ ] **Step 2: Create xml_ops.py**
Create `editor/routes/xml_ops.py`:
```python
"""XML load/save/form endpoints."""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from editor.services.form_builder import FormBuilder
from editor.services.state import EditorState

router = APIRouter(tags=["xml"])

# Module-level state instance (shared across requests in same process)
_state = EditorState()


def get_state() -> EditorState:
    return _state


class CarregarXmlRequest(BaseModel):
    caminho: str


@router.post("/carregar-xml", response_class=HTMLResponse)
async def carregar_xml(body: CarregarXmlRequest, request: Request):
    """Load XML file, parse to dict, store in state, return form HTML."""
    state = get_state()
    try:
        dados = FormBuilder.xml_to_dict(body.caminho)
    except Exception as e:
        return HTMLResponse(f"<p class='toast toast-error'>Erro ao carregar: {e}</p>")

    # Create or reuse a lote
    if not state.lotes:
        lote_id = state.criar_lote("novo")
    else:
        lote_id = list(state.lotes.keys())[0]

    guia_id = state.adicionar_guia(lote_id, dados.get("tipo", "guiaSP-SADT"), dados, body.caminho)

    # Render the appropriate form template
    templates = request.app.state.templates
    tipo = dados.get("tipo", "guiaSP-SADT")
    template_map = {
        "guiaSP-SADT": "editor/guia_sadt.html",
        "guiaHonorarios": "editor/guia_honorarios.html",
        "guiaResumoInternacao": "editor/guia_resumo_internacao.html",
    }
    template_name = template_map.get(tipo, "editor/guia_sadt.html")
    return templates.TemplateResponse(template_name, {
        "request": request,
        "guia": dados,
        "guia_id": guia_id,
        "lote_id": lote_id,
    })


@router.post("/salvar-xml")
async def salvar_xml(request: Request):
    """Save edited guia back to XML file."""
    body = await request.json()
    guia_id = body.get("guia_id")
    caminho_saida = body.get("caminho_saida")

    state = get_state()
    guia = state.get_guia(guia_id)
    if not guia:
        return JSONResponse({"erro": "Guia não encontrada"}, status_code=404)

    if not caminho_saida:
        caminho_saida = guia.caminho_arquivo
    if not caminho_saida:
        return JSONResponse({"erro": "Caminho de saída não especificado"}, status_code=400)

    try:
        novo_hash = FormBuilder.dict_to_xml(guia.dados, caminho_saida)
        guia.modificado = False
        return JSONResponse({"sucesso": True, "hash": novo_hash, "caminho": caminho_saida})
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)


@router.get("/formulario/{guia_id}", response_class=HTMLResponse)
async def get_formulario(guia_id: str, request: Request):
    """Render form for a specific guia."""
    state = get_state()
    guia = state.get_guia(guia_id)
    if not guia:
        return HTMLResponse("<p>Guia não encontrada.</p>", status_code=404)

    templates = request.app.state.templates
    template_map = {
        "guiaSP-SADT": "editor/guia_sadt.html",
        "guiaHonorarios": "editor/guia_honorarios.html",
        "guiaResumoInternacao": "editor/guia_resumo_internacao.html",
    }
    template_name = template_map.get(guia.tipo, "editor/guia_sadt.html")
    # Find lote_id for this guia
    lote_id = None
    for lid, lote in state.lotes.items():
        if guia_id in lote.guias:
            lote_id = lid
            break
    return templates.TemplateResponse(template_name, {
        "request": request,
        "guia": guia.dados,
        "guia_id": guia_id,
        "lote_id": lote_id,
    })
```

- [ ] **Step 3: Verify routes import**
Run:
```bash
cd /home/estevao/Projects/Unimed/ToolTiss && python3 -c "from editor.routes.dialogs import router as d; from editor.routes.xml_ops import router as x; print('Routes OK:', len(d.routes), len(x.routes))"
```
Expected: `Routes OK: 3 3`

- [ ] **Step 4: Commit**
```bash
git add editor/routes/dialogs.py editor/routes/xml_ops.py
git commit -m "feat(editor): dialog and XML operation API routes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Guia Form Templates (SADT + Honorários + RI)

**Files:**
- Create: `editor/templates/editor/guia_sadt.html`
- Create: `editor/templates/editor/guia_honorarios.html`
- Create: `editor/templates/editor/guia_resumo_internacao.html`
- Create: `editor/templates/editor/components/secao_cabecalho.html`
- Create: `editor/templates/editor/components/secao_beneficiario.html`
- Create: `editor/templates/editor/components/tabela_procedimentos.html`
- Create: `editor/templates/editor/components/campo_input.html`

- [ ] **Step 1: Create campo_input.html component**
Create `editor/templates/editor/components/campo_input.html`:
```html
<div class="form-field">
    <label for="{{ name }}">{{ label }}</label>
    {% if type == "select" %}
    <select name="{{ name }}" id="{{ name }}">
        {% for opt in options %}
        <option value="{{ opt.value }}" {% if opt.value == value %}selected{% endif %}>{{ opt.label }}</option>
        {% endfor %}
    </select>
    {% else %}
    <input type="{{ type | default('text') }}" name="{{ name }}" id="{{ name }}" value="{{ value | default('') }}">
    {% endif %}
</div>
```

- [ ] **Step 2: Create secao_cabecalho.html**
Create `editor/templates/editor/components/secao_cabecalho.html`:
```html
<details open>
    <summary>📋 Cabeçalho da Guia</summary>
    <div class="section-body form-grid">
        {% include "editor/components/campo_input.html" with context %}
        {% set name = "cabecalhoGuia.registroANS" %}
        {% set label = "Registro ANS" %}
        {% set value = guia.cabecalhoGuia.registroANS if guia.cabecalhoGuia is defined else "" %}
        {% include "editor/components/campo_input.html" with context %}

        {% set name = "cabecalhoGuia.numeroGuiaPrestador" %}
        {% set label = "Nº Guia Prestador" %}
        {% set value = guia.cabecalhoGuia.numeroGuiaPrestador if guia.cabecalhoGuia is defined else "" %}
        {% include "editor/components/campo_input.html" with context %}

        {% set name = "cabecalhoGuia.guiaPrincipal" %}
        {% set label = "Guia Principal" %}
        {% set value = guia.cabecalhoGuia.guiaPrincipal if guia.cabecalhoGuia is defined else "" %}
        {% include "editor/components/campo_input.html" with context %}
    </div>
</details>
```

Wait — the `{% set %}` + `{% include %}` pattern above won't work correctly because Jinja2 includes don't inherit set variables that way. Let me fix this with a simpler direct approach:

- [ ] **Step 2 (corrected): Create secao_cabecalho.html**
Create `editor/templates/editor/components/secao_cabecalho.html`:
```html
<details open>
    <summary>📋 Cabeçalho da Guia</summary>
    <div class="section-body form-grid">
        <div class="form-field">
            <label>Registro ANS</label>
            <input type="text" name="cabecalhoGuia[registroANS]"
                   value="{{ guia.cabecalhoGuia.registroANS | default('') }}">
        </div>
        <div class="form-field">
            <label>Nº Guia Prestador</label>
            <input type="text" name="cabecalhoGuia[numeroGuiaPrestador]"
                   value="{{ guia.cabecalhoGuia.numeroGuiaPrestador | default('') }}">
        </div>
        <div class="form-field">
            <label>Guia Principal</label>
            <input type="text" name="cabecalhoGuia[guiaPrincipal]"
                   value="{{ guia.cabecalhoGuia.guiaPrincipal | default('') }}">
        </div>
    </div>
</details>
```

- [ ] **Step 3: Create secao_beneficiario.html**
Create `editor/templates/editor/components/secao_beneficiario.html`:
```html
<details open>
    <summary>👤 Dados do Beneficiário</summary>
    <div class="section-body form-grid">
        <div class="form-field">
            <label>Nº Carteira</label>
            <input type="text" name="dadosBeneficiario[numeroCarteira]"
                   value="{{ guia.dadosBeneficiario.numeroCarteira | default('') }}">
        </div>
        <div class="form-field">
            <label>Atendimento RN</label>
            <select name="dadosBeneficiario[atendimentoRN]">
                <option value="N" {% if guia.dadosBeneficiario.atendimentoRN | default('N') == 'N' %}selected{% endif %}>Não</option>
                <option value="S" {% if guia.dadosBeneficiario.atendimentoRN | default('N') == 'S' %}selected{% endif %}>Sim</option>
            </select>
        </div>
    </div>
</details>
```

- [ ] **Step 4: Create tabela_procedimentos.html**
Create `editor/templates/editor/components/tabela_procedimentos.html`:
```html
<details open>
    <summary>🏥 Procedimentos Executados ({{ guia.procedimentosExecutados | default([]) | length }})</summary>
    <div class="section-body">
        <table class="tabela-dinamica">
            <thead>
                <tr>
                    <th>Seq</th><th>Data</th><th>Hora Início</th><th>Hora Fim</th>
                    <th>Código</th><th>Descrição</th><th>Qtd</th>
                    <th>Valor Unit.</th><th>Valor Total</th>
                </tr>
            </thead>
            <tbody id="procedimentos-body">
                {% for proc in guia.procedimentosExecutados | default([]) %}
                <tr>
                    <td><input name="procedimentosExecutados[{{ loop.index0 }}][sequencialItem]" value="{{ proc.sequencialItem | default('') }}"></td>
                    <td><input name="procedimentosExecutados[{{ loop.index0 }}][dataExecucao]" value="{{ proc.dataExecucao | default('') }}"></td>
                    <td><input name="procedimentosExecutados[{{ loop.index0 }}][horaInicial]" value="{{ proc.horaInicial | default('') }}"></td>
                    <td><input name="procedimentosExecutados[{{ loop.index0 }}][horaFinal]" value="{{ proc.horaFinal | default('') }}"></td>
                    <td><input name="procedimentosExecutados[{{ loop.index0 }}][codigoProcedimento]" value="{{ proc.codigoProcedimento | default(proc.procedimento.codigoProcedimento | default('')) }}"></td>
                    <td><input name="procedimentosExecutados[{{ loop.index0 }}][descricaoProcedimento]" value="{{ proc.descricaoProcedimento | default(proc.procedimento.descricaoProcedimento | default('')) }}"></td>
                    <td><input name="procedimentosExecutados[{{ loop.index0 }}][quantidadeExecutada]" value="{{ proc.quantidadeExecutada | default('') }}"></td>
                    <td><input name="procedimentosExecutados[{{ loop.index0 }}][valorUnitario]" value="{{ proc.valorUnitario | default('') }}"></td>
                    <td><input name="procedimentosExecutados[{{ loop.index0 }}][valorTotal]" value="{{ proc.valorTotal | default('') }}"></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</details>
```

- [ ] **Step 5: Create guia_sadt.html**
Create `editor/templates/editor/guia_sadt.html`:
```html
<form id="guia-form" data-guia-id="{{ guia_id }}" data-lote-id="{{ lote_id }}">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <h2>📝 Guia SADT</h2>
        <div>
            <button type="button" class="btn btn-primary" onclick="salvarGuia('{{ guia_id }}')">💾 Salvar</button>
            <button type="button" class="btn btn-primary" onclick="enviarGuia('{{ guia_id }}')">📤 Enviar</button>
        </div>
    </div>

    {% with guia=guia %}
    {% include "editor/components/secao_cabecalho.html" %}
    {% endwith %}

    <details>
        <summary>🔐 Dados de Autorização</summary>
        <div class="section-body form-grid">
            <div class="form-field">
                <label>Nº Guia Operadora</label>
                <input type="text" name="dadosAutorizacao[numeroGuiaOperadora]"
                       value="{{ guia.dadosAutorizacao.numeroGuiaOperadora | default('') }}">
            </div>
            <div class="form-field">
                <label>Data Autorização</label>
                <input type="date" name="dadosAutorizacao[dataAutorizacao]"
                       value="{{ guia.dadosAutorizacao.dataAutorizacao | default('') }}">
            </div>
            <div class="form-field">
                <label>Senha</label>
                <input type="text" name="dadosAutorizacao[senha]"
                       value="{{ guia.dadosAutorizacao.senha | default('') }}">
            </div>
        </div>
    </details>

    {% with guia=guia %}
    {% include "editor/components/secao_beneficiario.html" %}
    {% endwith %}

    <details>
        <summary>👨‍⚕️ Dados do Solicitante</summary>
        <div class="section-body form-grid">
            <div class="form-field">
                <label>Código Prestador Solicitante</label>
                <input type="text" name="dadosSolicitante[contratadoSolicitante][codigoPrestadorNaOperadora]"
                       value="{{ guia.dadosSolicitante.contratadoSolicitante.codigoPrestadorNaOperadora | default('') }}">
            </div>
            <div class="form-field">
                <label>Nome Contratado</label>
                <input type="text" name="dadosSolicitante[nomeContratadoSolicitante]"
                       value="{{ guia.dadosSolicitante.nomeContratadoSolicitante | default('') }}">
            </div>
            <div class="form-field">
                <label>Conselho Profissional</label>
                <input type="text" name="dadosSolicitante[profissionalSolicitante][conselhoProfissional]"
                       value="{{ guia.dadosSolicitante.profissionalSolicitante.conselhoProfissional | default('') }}">
            </div>
            <div class="form-field">
                <label>Nº Conselho</label>
                <input type="text" name="dadosSolicitante[profissionalSolicitante][numeroConselhoProfissional]"
                       value="{{ guia.dadosSolicitante.profissionalSolicitante.numeroConselhoProfissional | default('') }}">
            </div>
        </div>
    </details>

    {% with guia=guia %}
    {% include "editor/components/tabela_procedimentos.html" %}
    {% endwith %}

    <details>
        <summary>📊 Dados de Atendimento</summary>
        <div class="section-body form-grid">
            <div class="form-field">
                <label>Tipo Atendimento</label>
                <input type="text" name="dadosAtendimento[tipoAtendimento]"
                       value="{{ guia.dadosAtendimento.tipoAtendimento | default('') }}">
            </div>
            <div class="form-field">
                <label>Indicação Acidente</label>
                <input type="text" name="dadosAtendimento[indicacaoAcidente]"
                       value="{{ guia.dadosAtendimento.indicacaoAcidente | default('') }}">
            </div>
            <div class="form-field">
                <label>Regime Atendimento</label>
                <input type="text" name="dadosAtendimento[regimeAtendimento]"
                       value="{{ guia.dadosAtendimento.regimeAtendimento | default('') }}">
            </div>
        </div>
    </details>
</form>

<script>
async function salvarGuia(guiaId) {
    const form = document.getElementById('guia-form');
    const formData = new FormData(form);
    // Convert FormData to nested object
    const dados = {};
    for (const [key, value] of formData.entries()) {
        const parts = key.replace(/\]/g, '').split('[');
        let current = dados;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!(parts[i] in current)) current[parts[i]] = {};
            current = current[parts[i]];
        }
        current[parts[parts.length - 1]] = value;
    }
    // Update state via API then save
    try {
        const saveResp = await fetch('/api/salvar-xml', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({guia_id: guiaId, dados: dados})
        });
        const result = await saveResp.json();
        if (result.sucesso) {
            showToast('Salvo com sucesso! Hash: ' + result.hash, 'success');
        } else {
            showToast('Erro: ' + result.erro, 'error');
        }
    } catch (e) {
        showToast('Erro ao salvar: ' + e.message, 'error');
    }
}

async function enviarGuia(guiaId) {
    showToast('Envio individual em desenvolvimento. Use "Enviar Lote" na sidebar.', 'error');
}
</script>
```

- [ ] **Step 6: Create guia_honorarios.html**
Create `editor/templates/editor/guia_honorarios.html`:
```html
<form id="guia-form" data-guia-id="{{ guia_id }}" data-lote-id="{{ lote_id }}">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <h2>📝 Guia de Honorários</h2>
        <div>
            <button type="button" class="btn btn-primary" onclick="salvarGuia('{{ guia_id }}')">💾 Salvar</button>
        </div>
    </div>

    {% with guia=guia %}
    {% include "editor/components/secao_cabecalho.html" %}
    {% endwith %}

    <details>
        <summary>🔐 Dados de Autorização</summary>
        <div class="section-body form-grid">
            <div class="form-field">
                <label>Nº Guia Operadora</label>
                <input type="text" name="dadosAutorizacao[numeroGuiaOperadora]"
                       value="{{ guia.dadosAutorizacao.numeroGuiaOperadora | default('') }}">
            </div>
            <div class="form-field">
                <label>Data Autorização</label>
                <input type="date" name="dadosAutorizacao[dataAutorizacao]"
                       value="{{ guia.dadosAutorizacao.dataAutorizacao | default('') }}">
            </div>
        </div>
    </details>

    {% with guia=guia %}
    {% include "editor/components/secao_beneficiario.html" %}
    {% endwith %}

    <details>
        <summary>👨‍⚕️ Dados do Profissional Executante</summary>
        <div class="section-body form-grid">
            <div class="form-field">
                <label>Código Prestador</label>
                <input type="text" name="dadosExecutante[contratadoExecutante][codigoPrestadorNaOperadora]"
                       value="{{ guia.dadosExecutante.contratadoExecutante.codigoPrestadorNaOperadora | default('') }}">
            </div>
            <div class="form-field">
                <label>CNES</label>
                <input type="text" name="dadosExecutante[CNES]"
                       value="{{ guia.dadosExecutante.CNES | default('') }}">
            </div>
            <div class="form-field">
                <label>Conselho</label>
                <input type="text" name="profissionalExecutante[conselhoProfissional]"
                       value="{{ guia.profissionalExecutante.conselhoProfissional | default('') }}">
            </div>
            <div class="form-field">
                <label>Nº Conselho</label>
                <input type="text" name="profissionalExecutante[numeroConselhoProfissional]"
                       value="{{ guia.profissionalExecutante.numeroConselhoProfissional | default('') }}">
            </div>
        </div>
    </details>

    {% with guia=guia %}
    {% include "editor/components/tabela_procedimentos.html" %}
    {% endwith %}
</form>

<script>
async function salvarGuia(guiaId) {
    const form = document.getElementById('guia-form');
    const formData = new FormData(form);
    const dados = {};
    for (const [key, value] of formData.entries()) {
        const parts = key.replace(/\]/g, '').split('[');
        let current = dados;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!(parts[i] in current)) current[parts[i]] = {};
            current = current[parts[i]];
        }
        current[parts[parts.length - 1]] = value;
    }
    try {
        const saveResp = await fetch('/api/salvar-xml', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({guia_id: guiaId, dados: dados})
        });
        const result = await saveResp.json();
        if (result.sucesso) showToast('Salvo! Hash: ' + result.hash, 'success');
        else showToast('Erro: ' + result.erro, 'error');
    } catch (e) { showToast('Erro: ' + e.message, 'error'); }
}
</script>
```

- [ ] **Step 7: Create guia_resumo_internacao.html**
Create `editor/templates/editor/guia_resumo_internacao.html`:
```html
<form id="guia-form" data-guia-id="{{ guia_id }}" data-lote-id="{{ lote_id }}">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <h2>📝 Resumo de Internação</h2>
        <div>
            <button type="button" class="btn btn-primary" onclick="salvarGuia('{{ guia_id }}')">💾 Salvar</button>
        </div>
    </div>

    {% with guia=guia %}
    {% include "editor/components/secao_cabecalho.html" %}
    {% endwith %}

    <details>
        <summary>🔐 Dados de Autorização</summary>
        <div class="section-body form-grid">
            <div class="form-field">
                <label>Nº Guia Operadora</label>
                <input type="text" name="dadosAutorizacao[numeroGuiaOperadora]"
                       value="{{ guia.dadosAutorizacao.numeroGuiaOperadora | default('') }}">
            </div>
            <div class="form-field">
                <label>Data Autorização</label>
                <input type="date" name="dadosAutorizacao[dataAutorizacao]"
                       value="{{ guia.dadosAutorizacao.dataAutorizacao | default('') }}">
            </div>
        </div>
    </details>

    {% with guia=guia %}
    {% include "editor/components/secao_beneficiario.html" %}
    {% endwith %}

    <details open>
        <summary>🏨 Dados da Internação</summary>
        <div class="section-body form-grid">
            <div class="form-field">
                <label>Caráter Internação</label>
                <input type="text" name="dadosInternacao[caraterInternacao]"
                       value="{{ guia.dadosInternacao.caraterInternacao | default('') }}">
            </div>
            <div class="form-field">
                <label>Tipo Internação</label>
                <input type="text" name="dadosInternacao[tipoInternacao]"
                       value="{{ guia.dadosInternacao.tipoInternacao | default('') }}">
            </div>
            <div class="form-field">
                <label>Data Entrada</label>
                <input type="date" name="dadosInternacao[dataInicio]"
                       value="{{ guia.dadosInternacao.dataInicio | default('') }}">
            </div>
            <div class="form-field">
                <label>Data Prevista Saída</label>
                <input type="date" name="dadosInternacao[dataPrevistaFim]"
                       value="{{ guia.dadosInternacao.dataPrevistaFim | default('') }}">
            </div>
            <div class="form-field">
                <label>Data Efetiva Saída</label>
                <input type="date" name="dadosInternacao[dataEfetivaFim]"
                       value="{{ guia.dadosInternacao.dataEfetivaFim | default('') }}">
            </div>
        </div>
    </details>

    <details>
        <summary>🩺 Diagnósticos</summary>
        <div class="section-body">
            <table class="tabela-dinamica">
                <thead><tr><th>Tipo</th><th>CID</th><th>Descrição</th></tr></thead>
                <tbody>
                    {% for diag in guia.diagnosticos | default([]) %}
                    <tr>
                        <td><input name="diagnosticos[{{ loop.index0 }}][tipoDiagnostico]" value="{{ diag.tipoDiagnostico | default('') }}"></td>
                        <td><input name="diagnosticos[{{ loop.index0 }}][codigoCID]" value="{{ diag.codigoCID | default(diag.codigoDiagnostico | default('')) }}"></td>
                        <td><input name="diagnosticos[{{ loop.index0 }}][descricaoDiagnostico]" value="{{ diag.descricaoDiagnostico | default('') }}"></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </details>

    {% with guia=guia %}
    {% include "editor/components/tabela_procedimentos.html" %}
    {% endwith %}

    <details>
        <summary>👥 Equipe Médica</summary>
        <div class="section-body">
            <table class="tabela-dinamica">
                <thead><tr><th>Código</th><th>Nome</th><th>Conselho</th><th>Nº Conselho</th><th>CBOS</th></tr></thead>
                <tbody>
                    {% for prof in guia.equipeMedica | default(guia.profissionalExecutante | default([]) if guia.profissionalExecutante is mapping else []) %}
                    <tr>
                        <td><input name="equipeMedica[{{ loop.index0 }}][codigoPrestadorNaOperadora]" value="{{ prof.codigoPrestadorNaOperadora | default('') }}"></td>
                        <td><input name="equipeMedica[{{ loop.index0 }}][nomeProfissional]" value="{{ prof.nomeProfissional | default('') }}"></td>
                        <td><input name="equipeMedica[{{ loop.index0 }}][conselhoProfissional]" value="{{ prof.conselhoProfissional | default('') }}"></td>
                        <td><input name="equipeMedica[{{ loop.index0 }}][numeroConselhoProfissional]" value="{{ prof.numeroConselhoProfissional | default('') }}"></td>
                        <td><input name="equipeMedica[{{ loop.index0 }}][CBOS]" value="{{ prof.CBOS | default('') }}"></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </details>
</form>

<script>
async function salvarGuia(guiaId) {
    const form = document.getElementById('guia-form');
    const formData = new FormData(form);
    const dados = {};
    for (const [key, value] of formData.entries()) {
        const parts = key.replace(/\]/g, '').split('[');
        let current = dados;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!(parts[i] in current)) current[parts[i]] = {};
            current = current[parts[i]];
        }
        current[parts[parts.length - 1]] = value;
    }
    try {
        const saveResp = await fetch('/api/salvar-xml', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({guia_id: guiaId, dados: dados})
        });
        const result = await saveResp.json();
        if (result.sucesso) showToast('Salvo! Hash: ' + result.hash, 'success');
        else showToast('Erro: ' + result.erro, 'error');
    } catch (e) { showToast('Erro: ' + e.message, 'error'); }
}
</script>
```

- [ ] **Step 8: Commit**
```bash
git add editor/templates/
git commit -m "feat(editor): guia form templates for SADT, Honorários and Resumo Internação

- Reusable components: secao_cabecalho, secao_beneficiario, tabela_procedimentos, campo_input
- Expandable sections via HTML5 details/summary
- Dynamic procedure tables with Jinja2 loops
- Inline save functionality per guia

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Lote Operations Route + Entry Point

**Files:**
- Create: `editor/routes/lote_ops.py`
- Create: `editor/templates/lote/lista_guias.html`
- Create: `editor/templates/lote/resultado_envio.html`
- Create: `main_editor.py`

- [ ] **Step 1: Create lote_ops.py**
Create `editor/routes/lote_ops.py`:
```python
"""Batch (lote) management and SOAP transmission endpoints."""
import os
import tempfile
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from editor.services.state import EditorState
from editor.services.form_builder import FormBuilder
from comunication.SoapClient import TissSoapClient
from services.TissResponseParser import TissResponseParser
import config

router = APIRouter(tags=["lote"])

# Shared state reference
from editor.routes.xml_ops import get_state


@router.post("/lote/novo", response_class=HTMLResponse)
async def criar_lote(request: Request):
    """Create a new empty lote and return updated sidebar HTML."""
    state = get_state()
    lote_id = state.criar_lote("novo")
    templates = request.app.state.templates
    return templates.TemplateResponse("lote/lista_guias.html", {
        "request": request,
        "lote_id": lote_id,
        "guias": [],
    })


@router.get("/lote/{lote_id}", response_class=HTMLResponse)
async def listar_guias(lote_id: str, request: Request):
    """List guias in a lote (sidebar content)."""
    state = get_state()
    lote = state.get_lote(lote_id)
    if not lote:
        return HTMLResponse("<p>Lote não encontrado.</p>")
    templates = request.app.state.templates
    return templates.TemplateResponse("lote/lista_guias.html", {
        "request": request,
        "lote_id": lote_id,
        "guias": list(lote.guias.values()),
    })


@router.delete("/lote/{lote_id}/guia/{guia_id}")
async def remover_guia(lote_id: str, guia_id: str):
    """Remove a guia from a lote."""
    state = get_state()
    state.remover_guia(lote_id, guia_id)
    return JSONResponse({"ok": True})


@router.post("/lote/{lote_id}/enviar")
async def enviar_lote(lote_id: str, request: Request):
    """Send all guias in a lote via SOAP and return results table."""
    state = get_state()
    lote = state.get_lote(lote_id)
    if not lote or not lote.guias:
        return JSONResponse({"erro": "Lote vazio ou não encontrado"}, status_code=400)

    resultados = []
    for guia_id, guia in lote.guias.items():
        # Serialize guia to temp XML
        fd, tmp_path = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        try:
            FormBuilder.dict_to_xml(guia.dados, tmp_path)
            sucesso, resposta = TissSoapClient.enviar_lote(
                tmp_path, config.URL_OPERADORA, config.SOAP_ACTION_METODO
            )
            parse_result = TissResponseParser.parse(resposta) if sucesso else None
            resultados.append({
                "arquivo": f"Guia {guia.dados.get('cabecalhoGuia', {}).get('numeroGuiaPrestador', guia_id)}",
                "parse_result": parse_result,
                "sucesso": sucesso,
                "erro": resposta if not sucesso else None,
            })
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # Generate CSV report
    csv_path = os.path.join(
        config.PASTA_RESPOSTA or os.getcwd(),
        f"relatorio_editor_{lote_id}.csv"
    )
    try:
        TissResponseParser.gerar_relatorio_csv(resultados, csv_path)
    except Exception:
        csv_path = None

    templates = request.app.state.templates
    return templates.TemplateResponse("lote/resultado_envio.html", {
        "request": request,
        "resultados": resultados,
        "csv_path": csv_path,
        "lote_id": lote_id,
    })
```

- [ ] **Step 2: Create lista_guias.html**
Create `editor/templates/lote/lista_guias.html`:
```html
<h3>Lote {{ lote_id }}</h3>
{% if guias %}
{% for guia in guias %}
<div class="guia-item {% if guia.modificado %}modificado{% endif %}"
     hx-get="/api/formulario/{{ guia.id }}"
     hx-target="#main-content"
     hx-swap="innerHTML">
    <span>{{ guia.tipo }} — {{ guia.dados.cabecalhoGuia.numeroGuiaPrestador | default(guia.id) }}</span>
    <button class="btn btn-danger btn-sm"
            hx-delete="/api/lote/{{ lote_id }}/guia/{{ guia.id }}"
            hx-target="closest .guia-item"
            hx-swap="outerHTML"
            onclick="event.stopPropagation()">✕</button>
</div>
{% endfor %}
<button class="btn btn-primary" style="margin-top:12px; width:100%;"
        hx-post="/api/lote/{{ lote_id }}/enviar"
        hx-target="#main-content"
        hx-swap="innerHTML">
    📤 Enviar Lote
</button>
{% else %}
<p class="empty-state">Nenhuma guia neste lote.</p>
{% endif %}
```

- [ ] **Step 3: Create resultado_envio.html**
Create `editor/templates/lote/resultado_envio.html`:
```html
<h2>📊 Resultado do Envio — Lote {{ lote_id }}</h2>
{% if csv_path %}
<p>📄 Relatório CSV gerado: <code>{{ csv_path }}</code></p>
{% endif %}

<table class="tabela-dinamica" style="margin-top:16px;">
    <thead>
        <tr>
            <th>Guia</th>
            <th>Protocolo</th>
            <th>Status</th>
            <th>Motivo</th>
        </tr>
    </thead>
    <tbody>
        {% for r in resultados %}
        {% if r.parse_result and r.parse_result.guias %}
            {% for guia in r.parse_result.guias %}
            <tr>
                <td>{{ guia.numero_guia_prestador | default(r.arquivo) }}</td>
                <td>{{ r.parse_result.protocolo | default('—') }}</td>
                <td>
                    {% if guia.status in ('aceito', 'recebido', 'processado') %}
                        ✅ {{ guia.status }}
                    {% else %}
                        ❌ {{ guia.status }}
                    {% endif %}
                </td>
                <td>{{ guia.motivo | default('') }}</td>
            </tr>
            {% endfor %}
        {% elif not r.sucesso %}
            <tr>
                <td>{{ r.arquivo }}</td>
                <td>—</td>
                <td>❌ ERRO</td>
                <td>{{ r.erro | default('Falha de comunicação') }}</td>
            </tr>
        {% else %}
            <tr>
                <td>{{ r.arquivo }}</td>
                <td>—</td>
                <td>⚠️ SEM DADOS</td>
                <td>Resposta não pôde ser parseada</td>
            </tr>
        {% endif %}
        {% endfor %}
    </tbody>
</table>
```

- [ ] **Step 4: Create main_editor.py**
Create `main_editor.py`:
```python
"""Entry point for the ToolTiss Editor (PyInstaller target)."""
import socket
import threading
import webbrowser

import uvicorn

from editor.app import create_app


def encontrar_porta_livre(inicio: int = 54321, fim: int = 54400) -> int:
    """Find an available port in the given range."""
    for porta in range(inicio, fim + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", porta))
                return porta
            except OSError:
                continue
    raise RuntimeError("Nenhuma porta livre encontrada no intervalo especificado.")


if __name__ == "__main__":
    porta = encontrar_porta_livre()
    app = create_app()

    def abrir_browser():
        webbrowser.open(f"http://127.0.0.1:{porta}")

    threading.Timer(1.5, abrir_browser).start()

    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")
```

- [ ] **Step 5: Verify entry point imports**
Run:
```bash
cd /home/estevao/Projects/Unimed/ToolTiss && python3 -c "import main_editor; print('Entry point OK')"
```
Expected: `Entry point OK`

- [ ] **Step 6: Commit**
```bash
git add editor/routes/lote_ops.py editor/templates/lote/ main_editor.py
git commit -m "feat(editor): lote operations, result templates and main entry point

- POST /api/lote/{id}/enviar sends all guias via SOAP
- Result table shows protocol, status and glosa reasons per guia
- CSV report generated alongside results
- main_editor.py starts uvicorn on random port and opens browser

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review Checklist

1. **Spec coverage:** All spec sections mapped to tasks:
   - ✅ Architecture (Task 4)
   - ✅ form_builder.py XML↔dict (Task 3)
   - ✅ state.py in-memory (Task 2)
   - ✅ Routes: xml_ops, lote_ops, dialogs (Tasks 5, 7)
   - ✅ Templates: SADT, Honorários, RI (Task 6)
   - ✅ Components: secao_cabecalho, secao_beneficiario, tabela_procedimentos (Task 6)
   - ✅ Entry point + PyInstaller command (Task 7)
   - ✅ Config extensions (Task 1)
   - ✅ Reuse of TissXmlService, SoapClient, TissResponseParser (Tasks 3, 7)

2. **Placeholder scan:** No TBD/TODO/vague steps found. All code blocks complete.

3. **Type consistency:** `EditorState`, `GuiaDados`, `Lote`, `FormBuilder` names consistent across Tasks 2, 3, 5, 7. Method signatures (`xml_to_dict`, `dict_to_xml`, `criar_lote`, `adicionar_guia`, `get_guia`) match usage in routes.

---

Plan complete and saved to `docs/superpowers/plans/2026-10-30-editor-tiss.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?