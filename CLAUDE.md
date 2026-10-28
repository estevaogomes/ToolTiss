# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ToolTiss is a TISS (Agência Nacional de Saúde Suplementar) XML batch orchestrator and transmitter for Brazilian health insurance operators. It masks beneficiary PII, recalculates ANS-mandated MD5 hashes, and transmits batches via SOAP. Has both a CLI entry point (`app.py`) and a CustomTkinter GUI (`tooltiss.py`).

## Commands

```bash
# Install dependencies
pip install customtkinter requests

# Optional: Excel support for wallet number spreadsheets
pip install pandas openpyxl

# Run GUI
python tooltiss.py

# Run headless CLI pipeline (uses config.py flags)
python app.py

# Build Windows executable (single-file, embeds manual.pdf + customtkinter assets)
python -m PyInstaller --clean --noconsole --onefile \
  --collect-all customtkinter \
  --add-data "manual.pdf;." \
  -n "ToolTiss" -i "bateria.ico" tooltiss.py
```

No test suite, linter, or formatter configured.

## Architecture

### Dual Entry Points

- **`tooltiss.py`** — Primary production entry. CustomTkinter GUI with tabs for config editing, file/folder selection, processing, and transmission. Reads/writes `config.py` at runtime through the UI. Embeds `manual.pdf` for end-user help.
- **`app.py`** — Headless CLI pipeline for testing/automation. Auto-generates stub `contas.xml` and `dados.csv` if missing. Respects same `config.py` feature flags as GUI.

### Config-Driven Feature Flags (`config.py`)

All processing steps are toggled via module-level booleans. Both entry points read these directly — there is no config abstraction layer:

- `ALTERAR_LOTES` — enable wallet number masking
- `ALTERAR_GUIAS` — enable guide/provider number randomization
- `ALTERAR_TRANSACAO_LOTE` — enable batch/transaction ID mutation
- `UTILIZAR_RANDOM_TRANSACAO` — random vs increment for transaction IDs
- `ENVIAR_WS` — transmit to operator SOAP endpoint after processing
- `SOBRESCREVER_ENTRADA` — overwrite input file vs write to separate output

URLs, timeouts, and file paths also live here. The GUI edits this file in place.

### Processing Pipeline (unidirectional)

1. **DataExtractorService.carregar_carteiras()** — loads replacement wallet numbers from CSV or Excel. Column selection via `COLUNA_ALVO`. Falls back to first column if named column missing.
2. **TissXmlService.processar_alteracao_tiss()** — parses XML with `iso-8859-1` encoding, registers namespaces to prevent `ns0:` prefix rewriting, iterates all elements replacing `numeroCarteira`, `numeroLote`, `sequencialTransacao`, `numeroGuiaPrestador` and related tags. Guide numbers are randomized once per `numeroGuiaPrestador` and reused across linked tags (`numeroGuiaOperadora`, `senha`, `guiaPrincipal`, `guiaSolicInternacao`).
3. **TissXmlService.atualizar_hash_tiss()** — ANS C14N hash recalculation. Recursively extracts text content ignoring whitespace/tails, skips `<epilogo>` and `<hash>` nodes entirely, encodes result as `iso-8859-1`, produces 32-char hex MD5. Writes back into `<hash>` tag.
4. **TissSoapClient.enviar_lote()** — calls `preparar_conteudo_xml()` to strip wrapper tags (`<prestadorParaOperadora>`, `<epilogo>`) keeping only `<cabecalho>` + `<loteGuias>` + recalculated `<hash>`. Wraps in SOAP envelope with `ans:loteGuiasWS` body. Saves debug copy to `ultimo_envio_soap.txt`. Posts as `iso-8859-1` bytes.

### Critical Encoding Constraint

Entire pipeline uses **ISO-8859-1** (Latin-1) for XML parsing, hash computation, SOAP serialization, and file I/O. Changing to UTF-8 anywhere breaks ANS hash validation and operator acceptance. This is non-negotiable per TISS spec.

### Namespace Handling

XML files use ANS-defined namespaces. Code must register all discovered prefixes before writing to prevent ElementTree from renaming tags to `ns0:tag`, which invalidates the SOAP payload. Both `processar_alteracao_tiss()` and `preparar_conteudo_xml()` handle this independently.

## File Conventions

- `.gitignore` excludes all `.xml`, `.csv`, `.txt`, `build/`, `dist/`, `*.spec` — never commit data files or build artifacts
- Debug outputs (`resposta.txt`, `ultimo_envio_soap.txt`) are generated at runtime in working directory
- `Arquivos sem Ocorrencias/` — folder for processed files that had no issues (Portuguese naming intentional)