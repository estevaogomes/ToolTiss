"""File dialog endpoints using tkinter headless."""
from fastapi import APIRouter

router = APIRouter(tags=["dialogs"])


@router.get("/dialog/arquivo")
def dialog_arquivo():
    """Open file dialog and return selected path."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        try:
            root.withdraw()
            root.attributes("-topmost", True)
            caminho = filedialog.askopenfilename(
                title="Selecionar XML TISS",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
            )
        finally:
            root.destroy()
        if caminho:
            return {"caminho": caminho}
        return {"cancelado": True}
    except Exception as e:
        return {"erro": str(e)}


@router.get("/dialog/pasta")
def dialog_pasta():
    """Open folder dialog and return selected path."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        try:
            root.withdraw()
            root.attributes("-topmost", True)
            caminho = filedialog.askdirectory(title="Selecionar Pasta de XMLs")
        finally:
            root.destroy()
        if caminho:
            return {"caminho": caminho}
        return {"cancelado": True}
    except Exception as e:
        return {"erro": str(e)}


@router.get("/dialog/salvar-como")
def dialog_salvar_como():
    """Open save-as dialog and return selected path."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        try:
            root.withdraw()
            root.attributes("-topmost", True)
            caminho = filedialog.asksaveasfilename(
                title="Salvar XML TISS",
                defaultextension=".xml",
                filetypes=[("XML files", "*.xml")],
            )
        finally:
            root.destroy()
        if caminho:
            return {"caminho": caminho}
        return {"cancelado": True}
    except Exception as e:
        return {"erro": str(e)}