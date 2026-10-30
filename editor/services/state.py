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
        self._guia_index: dict[str, str] = {}  # guia_id -> lote_id

    def criar_lote(self, numero_lote: str) -> str:
        lote_id = str(uuid.uuid4())[:8]
        self.lotes[lote_id] = Lote(id=lote_id, numero_lote=numero_lote)
        return lote_id

    def get_lote(self, lote_id: str) -> Lote | None:
        return self.lotes.get(lote_id)

    def adicionar_guia(
        self, lote_id: str, tipo: str, dados: dict, caminho_arquivo: str | None = None
    ) -> str:
        if lote_id not in self.lotes:
            raise ValueError(f"Lote {lote_id} não encontrado")
        guia_id = str(uuid.uuid4())[:8]
        self.lotes[lote_id].guias[guia_id] = GuiaDados(
            id=guia_id,
            tipo=tipo,
            dados=dados,
            caminho_arquivo=caminho_arquivo,
        )
        self._guia_index[guia_id] = lote_id
        return guia_id

    def remover_guia(self, lote_id: str, guia_id: str) -> None:
        if lote_id in self.lotes:
            self.lotes[lote_id].guias.pop(guia_id, None)
            self._guia_index.pop(guia_id, None)

    def get_guia(self, guia_id: str) -> GuiaDados | None:
        lote_id = self._guia_index.get(guia_id)
        if lote_id is not None:
            lote = self.lotes.get(lote_id)
            if lote is not None:
                return lote.guias.get(guia_id)
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
