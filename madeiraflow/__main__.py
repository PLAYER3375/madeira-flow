from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .aplicacao.portas import ErroPersistencia
from .composicao import montar
from .dominio.modelos import RegraNegocio
from .infraestrutura.demo import preencher
from .infraestrutura.repositorios import SQLiteRepositorio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MadeiraFlow — estoque e produção para marcenarias")
    parser.add_argument("--demo", action="store_true", help="exemplos em uma base separada, criados somente na primeira execução")
    parser.add_argument("--data", type=Path, help="caminho do banco SQLite; relativo à pasta de trabalho")
    parser.add_argument("--verificar", action="store_true", help="validar a base sem abrir a interface")
    parser.add_argument("--backup", type=Path, help="criar uma cópia SQLite consistente em arquivo novo e sair")
    args = parser.parse_args(argv)
    caminho = args.data or Path("dados-demo" if args.demo else "dados") / "estoque.sqlite3"
    try:
        with SQLiteRepositorio(caminho) as repositorio:
            if args.demo and repositorio.novo:
                preencher(repositorio)
            if args.backup:
                repositorio.backup(args.backup)
                print(f"Backup criado em {args.backup.resolve()}")
            elif args.verificar:
                estado = repositorio.carregar().estado
                print(f"Base válida: {len(estado.materiais)} materiais, {len(estado.projetos)} projetos, "
                      f"{len(estado.movimentos)} movimentos, {len(estado.alertas)} alertas.")
            else:
                # Import tardio mantém domínio/CLI/testes disponíveis em instalações sem Tk.
                import tkinter as tk
                from .interface.janela import Janela

                raiz = tk.Tk()
                Janela(raiz, montar(repositorio), repositorio.caminho, repositorio.backup, args.demo)
                raiz.mainloop()
        return 0
    except (ErroPersistencia, RegraNegocio, OSError, ImportError) as erro:
        print(f"MadeiraFlow: {erro}", file=sys.stderr)
        return 1
    except Exception as erro:
        # Inclui TclError (display/Tk indisponível) sem esconder falhas da aplicação.
        if erro.__class__.__name__ == "TclError":
            print(f"Interface indisponível: {erro}. Verifique a instalação do Tk e a sessão gráfica.", file=sys.stderr)
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
