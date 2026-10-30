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