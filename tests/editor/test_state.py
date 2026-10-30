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
