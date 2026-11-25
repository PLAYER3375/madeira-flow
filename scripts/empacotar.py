"""Produz aplicativo .pyz e pacote de entrega; não inclui bases nem guia pessoal."""

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile
import zipapp

RAIZ = Path(__file__).resolve().parents[1]


def main() -> None:
    destino = RAIZ / "dist"
    destino.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporario:
        staging = Path(temporario)
        shutil.copytree(RAIZ / "madeiraflow", staging / "madeiraflow", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        zipapp.create_archive(staging, destino / "MadeiraFlow.pyz", main="madeiraflow.__main__:main", compressed=True)
    # O bundle acompanha o ZIP; o repositório de trabalho também mantém .git/.
    if (RAIZ / ".git").is_dir():
        subprocess.run(["git", "bundle", "create", str(destino / "historico.bundle"), "--all"], cwd=RAIZ, check=True)
    arquivos = []
    for caminho in sorted(RAIZ.rglob("*")):
        relativo = caminho.relative_to(RAIZ)
        if not caminho.is_file() or any(p in {".git", "__pycache__", ".venv", "dados", "dados-demo", "build", "dist"} for p in relativo.parts):
            continue
        arquivos.append((caminho, Path("MadeiraFlow-Python") / relativo))
    for nome in ("MadeiraFlow.pyz", "historico.bundle"):
        caminho = destino / nome
        if caminho.is_file():
            arquivos.append((caminho, Path("MadeiraFlow-Python/dist") / nome))
    manifesto = "\n".join(f"{sha256(origem.read_bytes()).hexdigest()}  {relativo.as_posix()}" for origem, relativo in arquivos) + "\n"
    pacote = destino / "MadeiraFlow-Python-entrega.zip"
    with ZipFile(pacote, "w", ZIP_DEFLATED) as arquivo:
        for origem, relativo in arquivos:
            arquivo.write(origem, relativo.as_posix())
        arquivo.writestr("manifesto.sha256", manifesto)
    print(f"Aplicativo: {destino / 'MadeiraFlow.pyz'}")
    print(f"Entrega: {pacote}")


if __name__ == "__main__":
    main()
