"""SQLite confirma snapshot e revisão em uma única transação ACID."""

from __future__ import annotations

from copy import deepcopy
from contextlib import closing
from pathlib import Path
import sqlite3

from madeiraflow.aplicacao.portas import ConflitoDeVersao, ErroPersistencia, Snapshot
from madeiraflow.dominio.modelos import EstadoEstoque
from .codec import desserializar, serializar

APPLICATION_ID = 0x4D465059  # MFPY, distingue a base de outros arquivos SQLite.


class MemoriaRepositorio:
    def __init__(self) -> None:
        self._estado = EstadoEstoque()
        self._revisao = 0

    def carregar(self) -> Snapshot:
        return Snapshot(deepcopy(self._estado), self._revisao)

    def salvar(self, estado: EstadoEstoque, revisao: int) -> None:
        estado.validar()
        if revisao != self._revisao:
            raise ConflitoDeVersao("Os dados mudaram. Atualize a consulta e tente novamente.")
        self._estado = deepcopy(estado)
        self._revisao += 1


class SQLiteRepositorio:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho).resolve()
        self.novo = not self.caminho.exists()
        self._conexao: sqlite3.Connection | None = None
        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            if not self.novo and self.caminho.stat().st_size == 0:
                raise ErroPersistencia("Arquivo de dados vazio ou incompleto; preserve-o e restaure um backup.")
            self._conexao = sqlite3.connect(self.caminho, timeout=3, isolation_level=None)
            self._conexao.execute("PRAGMA trusted_schema=OFF")
            self._conexao.execute("PRAGMA synchronous=FULL")
            if self.novo:
                self._inicializar()
            if (self._conexao.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
                    or self._conexao.execute("PRAGMA user_version").fetchone()[0] != 1):
                raise ErroPersistencia("Arquivo ou versão incompatível com MadeiraFlow Python.")
            if self._conexao.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ErroPersistencia("SQLite detectou corrupção. Restaure um backup.")
            self.carregar()  # Valida conteúdo e relações sem sobrescrever erros com base vazia.
        except Exception as erro:
            self.fechar()
            if isinstance(erro, ErroPersistencia):
                raise
            raise ErroPersistencia(f"Não foi possível abrir a base: {erro}") from erro

    def _inicializar(self) -> None:
        conexao = self._db()
        try:
            conexao.execute("BEGIN EXCLUSIVE")
            conexao.execute(f"PRAGMA application_id={APPLICATION_ID}")
            conexao.execute("PRAGMA user_version=1")
            conexao.execute("CREATE TABLE estado (id INTEGER PRIMARY KEY CHECK(id=1), "
                            "revisao INTEGER NOT NULL, conteudo TEXT NOT NULL)")
            conexao.execute("INSERT INTO estado VALUES (1, 0, ?)", (serializar(EstadoEstoque()),))
            conexao.execute("COMMIT")
        except Exception:
            if conexao.in_transaction:
                conexao.execute("ROLLBACK")
            raise

    def _db(self) -> sqlite3.Connection:
        if self._conexao is None:
            raise ErroPersistencia("Repositório fechado.")
        return self._conexao

    def carregar(self) -> Snapshot:
        try:
            linha = self._db().execute("SELECT revisao, conteudo FROM estado WHERE id=1").fetchone()
            if linha is None or not isinstance(linha[0], int) or linha[0] < 0:
                raise ErroPersistencia("Snapshot ausente ou revisão inválida.")
            return Snapshot(desserializar(linha[1]), linha[0])
        except ErroPersistencia:
            raise
        except Exception as erro:
            raise ErroPersistencia(f"Base inválida ou indisponível: {erro}") from erro

    def salvar(self, estado: EstadoEstoque, revisao: int) -> None:
        conteudo = serializar(estado)
        conexao = self._db()
        try:
            conexao.execute("BEGIN IMMEDIATE")
            atualizado = conexao.execute(
                "UPDATE estado SET conteudo=?, revisao=revisao+1 WHERE id=1 AND revisao=?",
                (conteudo, revisao))
            if atualizado.rowcount != 1:
                raise ConflitoDeVersao("Outro processo alterou a base. Atualize e tente novamente.")
            conexao.execute("COMMIT")
        except Exception as erro:
            if conexao.in_transaction:
                conexao.execute("ROLLBACK")
            if isinstance(erro, ErroPersistencia):
                raise
            raise ErroPersistencia(f"Operação não confirmada no banco: {erro}") from erro

    def backup(self, destino: str | Path) -> None:
        destino = Path(destino).resolve()
        if destino == self.caminho or destino.exists():
            raise ErroPersistencia("Escolha um arquivo de backup novo, diferente da base atual.")
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(destino)) as copia:
                self._db().backup(copia)
        except (OSError, sqlite3.Error) as erro:
            raise ErroPersistencia(f"Não foi possível criar backup: {erro}") from erro

    def fechar(self) -> None:
        if self._conexao is not None:
            self._conexao.close()
            self._conexao = None

    def __enter__(self) -> SQLiteRepositorio:
        return self

    def __exit__(self, *args: object) -> None:
        self.fechar()
