"""Verificação de widgets e callbacks reais; mensagens são substituídas para não bloquear."""

from decimal import Decimal as D
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from madeiraflow.dominio.modelos import StatusProjeto
from .base import Base


@unittest.skipUnless(os.environ.get("RUN_GUI_TESTS") == "1", "Use RUN_GUI_TESTS=1 em uma sessão com Tk/display.")
class TestInterface(Base):
    def setUp(self):
        super().setUp()
        import tkinter as tk
        from madeiraflow.interface.janela import Janela

        self.raiz = tk.Tk()
        self.raiz.withdraw()
        self.addCleanup(self.raiz.destroy)
        self.janela = Janela(self.raiz, self.s, Path("teste.sqlite3"), lambda _: None)
        self.raiz.update_idletasks()
        self.aviso = self.enterContext(patch("madeiraflow.interface.janela.messagebox.showwarning"))
        self.erro = self.enterContext(patch("madeiraflow.interface.janela.messagebox.showerror"))
        self.enterContext(patch("madeiraflow.interface.janela.messagebox.askyesno", return_value=True))

    def preencher(self, formulario, **valores):
        for chave, valor in valores.items():
            formulario.variaveis[chave].set(valor)

    def test_formulario_material_salva_pelos_servicos(self):
        form = self.janela.formulario_material()
        self.preencher(form, sku="UI-01", nome="Parafuso UI", unidade="UN", minimo="1", alvo="20", descricao="Zincado")
        form.botao_salvar.invoke()
        self.assertEqual(len(self.estado().materiais), 1)
        self.assertEqual(len(self.janela.materiais.get_children()), 1)
        self.assertFalse(form.winfo_exists())
        self.erro.assert_not_called()

    def test_formulario_invalido_permanece_aberto_sem_confirmar(self):
        form = self.janela.formulario_material()
        form.botao_salvar.invoke()
        self.aviso.assert_called_once()
        self.assertTrue(form.winfo_exists())
        self.assertEqual(len(self.estado().materiais), 0)

    def test_formulario_projeto_adiciona_itens_e_salva(self):
        id = self.material()
        self.janela.atualizar()
        form = self.janela.formulario_projeto()
        self.preencher(form, nome="Balcão UI", cliente="Ana", quantidade="3")
        form.adicionar()
        form.botao_salvar.invoke()
        self.assertEqual(next(iter(self.estado().projetos.values())).itens[0].material_id, id)
        self.assertEqual(len(self.janela.projetos.get_children()), 1)
        self.erro.assert_not_called()

    def test_callbacks_de_reserva_conclusao_e_rejeicao_duplicada(self):
        id = self.material()
        p = self.projeto((id, "3"))
        self.janela.atualizar()
        self.janela.projetos.selection_set(p)
        self.janela.acao_projeto("reservar")
        self.assertEqual(self.estado().projeto(p).status, StatusProjeto.RESERVADO)
        self.janela.acao_projeto("concluir")
        self.assertEqual(self.estado().material(id).fisico, D(7))
        self.janela.acao_projeto("concluir")
        self.aviso.assert_called_once()
        self.assertEqual(self.estado().material(id).fisico, D(7))
        self.erro.assert_not_called()

    def test_pesquisa_e_selecao_sem_resultados(self):
        self.material("UI")
        self.janela.atualizar()
        self.janela.busca.set("ausente")
        self.assertEqual(self.janela.materiais.get_children(), ())
        self.assertFalse(self.janela.executar(self.janela._material_selecionado))
        self.aviso.assert_called_once()
        self.erro.assert_not_called()

    def test_strategy_atualiza_tabela_de_reposicao(self):
        id = self.material(saldo="1")
        self.janela.atualizar()
        self.janela.politica.set("Até o mínimo")
        self.janela._atualizar_reposicao()
        self.assertEqual(str(self.janela.compras.set(id, "qtd")), "1")
        self.janela.politica.set("Até o alvo")
        self.janela._atualizar_reposicao()
        self.assertEqual(str(self.janela.compras.set(id, "qtd")), "9")

    def test_formulario_recebimento_e_inventario(self):
        from madeiraflow.interface.janela import Formulario

        id = self.material()
        self.janela.atualizar()
        self.janela.materiais.selection_set(id)
        self.janela._receber()
        form = next(w for w in self.raiz.winfo_children() if isinstance(w, Formulario))
        self.preencher(form, quantidade="5", custo="4,00", referencia="NF UI")
        form.botao_salvar.invoke()
        self.assertEqual(self.estado().material(id).fisico, D(15))
        self.janela._contar()
        form = next(w for w in self.raiz.winfo_children() if isinstance(w, Formulario))
        self.preencher(form, contado="14", justificativa="Uma unidade danificada")
        form.botao_salvar.invoke()
        self.assertEqual(self.estado().movimentos[-1].quantidade, D(-1))
        self.erro.assert_not_called()
