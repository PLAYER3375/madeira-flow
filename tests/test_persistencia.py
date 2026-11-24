import ast
from contextlib import closing
from dataclasses import replace
from decimal import Decimal as D
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from madeiraflow.aplicacao.portas import ConflitoDeVersao, ErroPersistencia
from madeiraflow.composicao import montar
from madeiraflow.dominio.modelos import ItemProjeto, RegraNegocio
from madeiraflow.infraestrutura.codec import desserializar, serializar
from madeiraflow.infraestrutura.demo import preencher
from madeiraflow.infraestrutura.repositorios import MemoriaRepositorio, SQLiteRepositorio
from .base import dados


class TestPersistencia(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporario.cleanup)
        self.caminho = Path(self.temporario.name) / "estoque.sqlite3"
        self.repo = SQLiteRepositorio(self.caminho)
        self.addCleanup(self.repo.fechar)
        self.s = montar(self.repo)

    def test_sqlite_preserva_dominio_decimal_e_historico_apos_reabrir(self):
        preencher(self.repo)
        antes = self.repo.carregar()
        self.repo.fechar()
        with SQLiteRepositorio(self.caminho) as outro:
            self.assertEqual(outro.carregar(), antes)
            self.assertFalse(outro.novo)

    def test_rn12_rollback_sqlite_real_quando_update_falha(self):
        id = self.s.cadastro.cadastrar(dados())
        antes = self.repo.carregar()
        with closing(sqlite3.connect(self.caminho)) as conexao, conexao:
            conexao.execute("CREATE TRIGGER impedir BEFORE UPDATE ON estado BEGIN SELECT RAISE(ABORT, 'falha injetada'); END")
        with self.assertRaises(ErroPersistencia):
            self.s.estoque.receber(id, D(3), D(2), "NF")
        self.assertEqual(self.repo.carregar(), antes)
        self.repo.fechar()
        with SQLiteRepositorio(self.caminho) as outro:
            self.assertEqual(outro.carregar(), antes)

    def test_concorrencia_rejeita_snapshot_antigo_sem_perder_commit(self):
        with SQLiteRepositorio(self.caminho) as outro:
            antigo = outro.carregar()
            self.s.cadastro.cadastrar(dados())
            with self.assertRaises(ConflitoDeVersao):
                outro.salvar(antigo.estado, antigo.revisao)
            self.assertEqual(len(outro.carregar().estado.materiais), 1)

    def test_memoria_tambem_rejeita_revisao_antiga(self):
        memoria = MemoriaRepositorio()
        snapshot = memoria.carregar()
        memoria.salvar(snapshot.estado, snapshot.revisao)
        with self.assertRaises(ConflitoDeVersao):
            memoria.salvar(snapshot.estado, snapshot.revisao)

    def test_rn12_erro_de_io_nao_confirma(self):
        id = self.s.cadastro.cadastrar(dados())
        antes = self.repo.carregar()
        with patch.object(self.repo, "salvar", side_effect=ErroPersistencia("disco cheio")):
            with self.assertRaises(ErroPersistencia):
                self.s.estoque.receber(id, D(1), D(1), "NF")
        self.assertEqual(self.repo.carregar(), antes)

    def test_corrompido_nao_e_sobrescrito(self):
        self.repo.fechar()
        self.caminho.write_bytes(b"arquivo corrompido")
        with self.assertRaises(ErroPersistencia):
            SQLiteRepositorio(self.caminho)
        self.assertEqual(self.caminho.read_bytes(), b"arquivo corrompido")

    def test_arquivo_vazio_nao_e_reinicializado(self):
        self.repo.fechar()
        self.caminho.write_bytes(b"")
        with self.assertRaises(ErroPersistencia):
            SQLiteRepositorio(self.caminho)
        self.assertEqual(self.caminho.stat().st_size, 0)

    def test_versao_futura_recusada(self):
        self.repo.fechar()
        with closing(sqlite3.connect(self.caminho)) as conexao, conexao:
            conexao.execute("PRAGMA user_version=999")
        with self.assertRaises(ErroPersistencia):
            SQLiteRepositorio(self.caminho)

    def test_json_invalido_recusado_sem_limpar_base(self):
        with closing(sqlite3.connect(self.caminho)) as conexao, conexao:
            conexao.execute("UPDATE estado SET conteudo='{' WHERE id=1")
        with self.assertRaises(ErroPersistencia):
            self.repo.carregar()
        with closing(sqlite3.connect(self.caminho)) as conexao, conexao:
            self.assertEqual(conexao.execute("SELECT conteudo FROM estado").fetchone()[0], "{")

    def test_reserva_inconsistente_e_recusada_pelo_codec(self):
        preencher(self.repo)
        dados_json = json.loads(serializar(self.repo.carregar().estado))
        dados_json["materiais"][0]["reservado"] = "0"
        with self.assertRaises(RegraNegocio):
            desserializar(json.dumps(dados_json))

    def test_backup_restauravel_e_rejeita_sobrescrita(self):
        preencher(self.repo)
        destino = self.caminho.with_name("backup.sqlite3")
        self.repo.backup(destino)
        with SQLiteRepositorio(destino) as copia:
            self.assertEqual(copia.carregar(), self.repo.carregar())
        for caminho in (destino, self.caminho):
            with self.subTest(caminho=caminho), self.assertRaises(ErroPersistencia):
                self.repo.backup(caminho)

    def test_demo_usa_servicos_e_quantidades_esperadas(self):
        preencher(self.repo)
        estado = self.repo.carregar().estado
        cavilha = next(m for m in estado.materiais.values() if m.sku == "CAV-8X30")
        self.assertEqual((len(estado.materiais), len(estado.projetos), len(estado.alertas)), (6, 2, 2))
        self.assertEqual((cavilha.fisico, cavilha.reservado, cavilha.disponivel), (D(150), D(90), D(60)))
        self.assertEqual(len(estado.auditoria), 15)
        with self.assertRaises(RegraNegocio):
            preencher(self.repo)

    def test_demo_falha_de_seed_nao_deixa_base_parcial(self):
        antes = self.repo.carregar()
        with patch("madeiraflow.infraestrutura.demo.montar", side_effect=RuntimeError("falha")):
            with self.assertRaises(RuntimeError):
                preencher(self.repo)
        self.assertEqual(self.repo.carregar(), antes)

    def test_repositorio_fechado_gera_erro_compreensivel(self):
        self.repo.fechar()
        with self.assertRaisesRegex(ErroPersistencia, "fechado"):
            self.repo.carregar()

    def test_cli_cria_demo_valida_e_nao_repete_seed(self):
        caminho = self.caminho.with_name("cli.sqlite3")
        comando = [sys.executable, "-X", "utf8", "-m", "madeiraflow", "--demo", "--data", str(caminho), "--verificar"]
        for _ in range(2):
            resultado = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            self.assertIn("6 materiais, 2 projetos", resultado.stdout)
        with SQLiteRepositorio(caminho) as repo:
            self.assertEqual(repo.carregar().revisao, 1)

    def test_cli_corrompido_retorna_erro(self):
        self.repo.fechar()
        self.caminho.write_bytes(b"invalido")
        resultado = subprocess.run([sys.executable, "-m", "madeiraflow", "--data", str(self.caminho), "--verificar"],
                                   capture_output=True)
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn(b"MadeiraFlow", resultado.stderr)

    def test_dominio_nao_depende_de_ui_sqlite_ou_aplicacao(self):
        pasta = Path(__file__).resolve().parents[1] / "madeiraflow" / "dominio"
        for arquivo in pasta.glob("*.py"):
            arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
            for no in ast.walk(arvore):
                modulos = ([n.name for n in no.names] if isinstance(no, ast.Import)
                           else [no.module or ""] if isinstance(no, ast.ImportFrom) else [])
                for modulo in modulos:
                    self.assertFalse(any(proibido in modulo for proibido in ("sqlite", "tkinter", "aplicacao", "infraestrutura", "interface")),
                                     f"Dependência indevida em {arquivo.name}: {modulo}")
