"""Batch (lote) management and SOAP transmission endpoints."""
import os
import tempfile
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter(tags=["lote"])

# Shared state reference
from editor.routes.xml_ops import get_state


@router.post("/lote/novo", response_class=HTMLResponse)
async def criar_lote(request: Request):
    """Create a new empty lote and return updated sidebar HTML."""
    state = get_state()
    lote_id = state.criar_lote("novo")
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        name="lote/lista_guias.html",
        context={
            "lote_id": lote_id,
            "guias": [],
        },
    )


@router.get("/lote/{lote_id}", response_class=HTMLResponse)
async def listar_guias(lote_id: str, request: Request):
    """List guias in a lote (sidebar content)."""
    state = get_state()
    lote = state.get_lote(lote_id)
    if not lote:
        return HTMLResponse("<p>Lote não encontrado.</p>")
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        name="lote/lista_guias.html",
        context={
            "lote_id": lote_id,
            "guias": list(lote.guias.values()),
        },
    )


@router.delete("/lote/{lote_id}/guia/{guia_id}")
async def remover_guia(lote_id: str, guia_id: str):
    """Remove a guia from a lote."""
    state = get_state()
    state.remover_guia(lote_id, guia_id)
    return JSONResponse({"ok": True})


@router.post("/lote/{lote_id}/enviar")
async def enviar_lote(lote_id: str, request: Request):
    """Send all guias in a lote via SOAP and return results table."""
    # Lazy imports to avoid import-time failures on non-Windows platforms
    from editor.services.form_builder import FormBuilder
    try:
        from comunication.SoapClient import TissSoapClient
        from services.TissResponseParser import TissResponseParser
        import config
    except ImportError as e:
        return JSONResponse(
            {"erro": f"Transmissão SOAP indisponível nesta plataforma: {e}"},
            status_code=501,
        )

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
        except NotImplementedError:
            resultados.append({
                "arquivo": f"Guia {guia.dados.get('cabecalhoGuia', {}).get('numeroGuiaPrestador', guia_id)}",
                "parse_result": None,
                "sucesso": False,
                "erro": "dict_to_xml ainda não implementado",
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
    return templates.TemplateResponse(
        request,
        name="lote/resultado_envio.html",
        context={
            "resultados": resultados,
            "csv_path": csv_path,
            "lote_id": lote_id,
        },
    )