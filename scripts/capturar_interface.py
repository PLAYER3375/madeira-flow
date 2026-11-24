"""Capturas reais de uma janela Tkinter no Windows; exige Pillow e sessão gráfica."""

import os
from pathlib import Path
import sys
import tkinter as tk

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from PIL import ImageGrab
from madeiraflow.composicao import montar
from madeiraflow.infraestrutura.demo import preencher
from madeiraflow.infraestrutura.repositorios import MemoriaRepositorio
from madeiraflow.interface.janela import Janela


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Este capturador foi preparado para Windows com sessão gráfica.")
    repositorio = MemoriaRepositorio()
    preencher(repositorio)
    raiz = tk.Tk()
    try:
        janela = Janela(raiz, montar(repositorio), Path("dados-demo/estoque.sqlite3"), lambda _: None, True)
        raiz.geometry("1230x780+20+20")
        raiz.attributes("-topmost", True)
        destino = RAIZ / "docs/evidencias"
        destino.mkdir(parents=True, exist_ok=True)
        for i, nome in enumerate(["visao-geral", "materiais", "projetos", "movimentacoes", "reposicao"]):
            janela.abas.select(i)
            raiz.update()
            pronto = tk.BooleanVar(raiz, False)
            raiz.after(300, pronto.set, True)
            raiz.wait_variable(pronto)
            raiz.update()
            x, y = raiz.winfo_rootx(), raiz.winfo_rooty()
            imagem = ImageGrab.grab((x, y, x + raiz.winfo_width(), y + raiz.winfo_height()), all_screens=True)
            arquivo = destino / f"{i+1:02d}-{nome}.png"
            imagem.save(arquivo)
            print(arquivo)
    finally:
        raiz.destroy()


if __name__ == "__main__":
    main()
