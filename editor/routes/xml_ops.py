"""XML load/save/form endpoints."""
import html

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from editor.services.form_builder import FormBuilder
from editor.services.state import EditorState

router = APIRouter(tags=["xml"])

# Module-level state instance (shared across requests in same process)
_state = EditorState()

_TEMPLATE_MAP = {
    "guiaSP-SADT": "editor/guia_sadt.html",
    "guiaHonorarios": "editor/guia_honorarios.html",
    "guiaResumoInternacao": "editor/guia_resumo_internacao.html",
}


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
        return HTMLResponse(f"<p class='toast toast-error'>Erro ao carregar: {html.escape(str(e))}</p>")

    # Create or reuse a lote
    if not state.lotes:
        lote_id = state.criar_lote("novo")
    else:
        lote_id = list(state.lotes.keys())[0]

    guia_id = state.adicionar_guia(
        lote_id, dados.get("tipo", "guiaSP-SADT"), dados, body.caminho
    )

    # Render the appropriate form template
    templates = request.app.state.templates
    tipo = dados.get("tipo", "guiaSP-SADT")
    template_name = _TEMPLATE_MAP.get(tipo, "editor/guia_sadt.html")
    return templates.TemplateResponse(
        name=template_name,
        context={
            "request": request,
            "guia": dados,
            "guia_id": guia_id,
            "lote_id": lote_id,
        },
    )


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
        return JSONResponse(
            {"erro": "Caminho de saída não especificado"}, status_code=400
        )

    try:
        novo_hash = FormBuilder.dict_to_xml(guia.dados, caminho_saida)
        guia.modificado = False
        return JSONResponse(
            {"sucesso": True, "hash": novo_hash, "caminho": caminho_saida}
        )
    except NotImplementedError:
        return JSONResponse(
            {"erro": "dict_to_xml ainda não implementado"}, status_code=501
        )
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
    template_name = _TEMPLATE_MAP.get(guia.tipo, "editor/guia_sadt.html")

    # Find lote_id for this guia
    lote_id = None
    for lid, lote in state.lotes.items():
        if guia_id in lote.guias:
            lote_id = lid
            break

    return templates.TemplateResponse(
        name=template_name,
        context={
            "request": request,
            "guia": guia.dados,
            "guia_id": guia_id,
            "lote_id": lote_id,
        },
    )