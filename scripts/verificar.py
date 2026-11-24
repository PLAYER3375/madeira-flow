"""Executa testes e grava relatório, distinguindo testes gráficos não executados."""

import io
import os
from pathlib import Path
import platform
import sys
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def main() -> int:
    os.chdir(RAIZ)
    saida = io.StringIO()
    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=str(RAIZ))
    resultado = unittest.TextTestRunner(stream=saida, verbosity=2).run(suite)
    texto = (f"MadeiraFlow Python — evidência de execução\nPython: {sys.version}\n"
             f"Plataforma: {platform.platform()}\nRUN_GUI_TESTS={os.environ.get('RUN_GUI_TESTS', '0')}\n\n"
             + saida.getvalue())
    destino = RAIZ / "build" / "resultados-testes.txt"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"Relatório: {destino}")
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
