from dataclasses import FrozenInstanceError, replace
from decimal import Decimal as D

from madeiraflow.aplicacao.eventos import AlertaEstoqueObserver, AuditoriaObserver, EventoDominio, PublicadorEventos
from madeiraflow.composicao import montar
from madeiraflow.dominio.modelos import Chapa, ItemProjeto, RegraNegocio, StatusProjeto, TipoMovimento, Unidade, numero
from madeiraflow.dominio.reposicao import ReposicaoAlvo, ReposicaoMinima
from .base import Base, INSTANTE, dados


class TestRegras(Base):
    def test_rn01_normaliza_sku_e_textos(self):
        id = self.s.cadastro.cadastrar(dados("  par-01 ", nome="  Parafuso  "))
        self.assertEqual((self.estado().material(id).sku, self.estado().material(id).nome), ("PAR-01", "Parafuso"))

    def test_rn01_rejeita_sku_duplicado_sem_confirmar(self):
        self.material("par")
        antes = self.repo.carregar()
        with self.assertRaises(RegraNegocio):
            self.s.cadastro.cadastrar(dados(" PAR "))
        self.assertEqual(self.repo.carregar(), antes)

    def test_rn01_rejeita_obrigatorios_e_sku_invalido(self):
        for alteracoes in ({"sku": ""}, {"nome": " "}, {"descricao": ""}, {"sku": "com espaço"}):
            with self.subTest(alteracoes=alteracoes), self.assertRaises(RegraNegocio):
                self.s.cadastro.cadastrar(dados(**alteracoes))
        self.assertEqual(len(self.estado().materiais), 0)

    def test_rn02_chapa_tem_dimensoes_e_comportamento_especifico(self):
        id = self.material("MDF", unidade=Unidade.CHAPA)
        material = self.estado().material(id)
        self.assertIsInstance(material, Chapa)
        self.assertIn("2750 × 1850 × 18 mm", material.caracteristicas)

    def test_rn02_chapa_rejeita_dimensao_nao_positiva(self):
        with self.assertRaises(RegraNegocio):
            self.s.cadastro.cadastrar(dados("MDF", Unidade.CHAPA, largura=D(0)))

    def test_rn02_chapas_e_un_nao_admitem_fracao(self):
        for unidade in (Unidade.CHAPA, Unidade.UN):
            with self.subTest(unidade=unidade), self.assertRaises(RegraNegocio):
                self.s.cadastro.cadastrar(dados("A", unidade, minimo=D("0.5")))

    def test_rn02_unidades_continuas_admitem_tres_casas(self):
        for unidade in (Unidade.M, Unidade.L, Unidade.KG):
            with self.subTest(unidade=unidade):
                self.assertEqual(unidade.validar(D("1.125")), D("1.125"))

    def test_rn02_rejeita_quarta_casa_na_quantidade(self):
        with self.assertRaises(RegraNegocio):
            Unidade.KG.validar(D("0.0001"))

    def test_rn02_edicao_nao_muda_unidade(self):
        id = self.material()
        with self.assertRaises(RegraNegocio):
            self.s.cadastro.editar(id, dados(unidade=Unidade.KG))
        self.assertIs(self.estado().material(id).unidade, Unidade.UN)

    def test_rn03_custo_medio_ponderado_e_movimento(self):
        id = self.material(saldo="10")
        self.s.estoque.receber(id, D(5), D("5.00"), "NF 2")
        material = self.estado().material(id)
        self.assertEqual((material.fisico, material.custo_medio, material.valor_estoque), (D(15), D("3.0000"), D(45)))
        self.assertEqual(self.estado().movimentos[-1].tipo, TipoMovimento.ENTRADA)

    def test_rn03_arredonda_half_up_em_quatro_casas(self):
        id = self.material(saldo="199")
        self.s.estoque.receber(id, D(1), D("2.01"), "NF 2")
        # 400,01 / 200 = 2,00005: o empate distingue HALF_UP de HALF_EVEN.
        self.assertEqual(self.estado().material(id).custo_medio, D("2.0001"))

    def test_rn03_recebimento_rejeita_quantidade_custo_ou_referencia(self):
        id = self.material()
        antes = self.repo.carregar()
        for quantidade, custo, referencia in [("0", "1", "NF"), ("-1", "1", "NF"), ("1", "0", "NF"),
                                                ("1", "1.001", "NF"), ("1", "1", " ")]:
            with self.subTest(q=quantidade, custo=custo, referencia=referencia), self.assertRaises(RegraNegocio):
                self.s.estoque.receber(id, D(quantidade), D(custo), referencia)
            self.assertEqual(self.repo.carregar(), antes)

    def test_rn04_disponivel_e_valor(self):
        id = self.material()
        p = self.projeto((id, "3"))
        self.s.projetos.reservar(p)
        material = self.estado().material(id)
        self.assertEqual((material.fisico, material.reservado, material.disponivel, material.valor_estoque),
                         (D(10), D(3), D(7), D(20)))

    def test_rn04_entidade_imutavel_e_saldo_invalido_rejeitado(self):
        material = dados().construir()
        with self.assertRaises(FrozenInstanceError):
            material.fisico = D(-1)
        with self.assertRaises(RegraNegocio):
            replace(material, reservado=D(1))

    def test_rn05_projeto_com_varios_itens_nao_reserva_ao_planejar(self):
        a, b = self.material("A"), self.material("B")
        p = self.projeto((a, "2"), (b, "3"))
        self.assertEqual(len(self.estado().projeto(p).itens), 2)
        self.assertEqual(self.estado().material(a).reservado, 0)

    def test_rn05_rejeita_projeto_sem_itens_nome_ou_cliente(self):
        id = self.material()
        for nome, cliente, itens in [("X", "Y", ()), ("", "Y", (ItemProjeto(id, D(1)),)),
                                     ("X", "", (ItemProjeto(id, D(1)),))]:
            with self.subTest(nome=nome, cliente=cliente), self.assertRaises(RegraNegocio):
                self.s.projetos.criar(nome, cliente, itens)

    def test_rn05_rejeita_item_duplicado_inexistente_e_fracionado(self):
        id = self.material()
        for itens in [((id, "1"), (id, "2")), (("ausente", "1"),), ((id, "0.5"),)]:
            with self.subTest(itens=itens), self.assertRaises(RegraNegocio):
                self.projeto(*itens)

    def test_rn05_rejeita_item_nao_positivo(self):
        for valor in ("0", "-1"):
            with self.subTest(valor=valor), self.assertRaises(RegraNegocio):
                ItemProjeto("id", D(valor))

    def test_rn06_reserva_integral(self):
        a, b = self.material("A"), self.material("B")
        p = self.projeto((a, "3"), (b, "4"))
        self.s.projetos.reservar(p)
        self.assertEqual(self.estado().projeto(p).status, StatusProjeto.RESERVADO)
        self.assertEqual((self.estado().material(a).reservado, self.estado().material(b).reservado), (D(3), D(4)))

    def test_rn06_falta_no_ultimo_item_preserva_todo_estado(self):
        a, b = self.material("A"), self.material("B", "1")
        p = self.projeto((a, "3"), (b, "2"))
        antes = self.repo.carregar()
        with self.assertRaisesRegex(RegraNegocio, "B"):
            self.s.projetos.reservar(p)
        self.assertEqual(self.repo.carregar(), antes)

    def test_rn06_projetos_nao_prometem_mesmo_saldo(self):
        id = self.material()
        p, outro = self.projeto((id, "7")), self.projeto((id, "4"))
        self.s.projetos.reservar(p)
        with self.assertRaises(RegraNegocio):
            self.s.projetos.reservar(outro)
        self.assertEqual(self.estado().material(id).reservado, D(7))

    def test_rn06_planejado_pode_ser_editado(self):
        id = self.material()
        p = self.projeto((id, "1"))
        self.s.projetos.editar(p, "Novo nome", "Outra cliente", (ItemProjeto(id, D(2)),))
        self.assertEqual(self.estado().projeto(p).itens[0].quantidade, D(2))

    def test_rn06_reservado_nao_pode_ser_editado_ou_reservado_de_novo(self):
        id = self.material()
        p = self.projeto((id, "1"))
        self.s.projetos.reservar(p)
        antes = self.repo.carregar()
        for operacao in [lambda: self.s.projetos.editar(p, "X", "Y", (ItemProjeto(id, D(1)),)),
                         lambda: self.s.projetos.reservar(p)]:
            with self.assertRaises(RegraNegocio):
                operacao()
            self.assertEqual(self.repo.carregar(), antes)

    def test_rn07_conclusao_reduz_fisico_e_reservado_preservando_disponivel(self):
        a, b = self.material("A"), self.material("B")
        p = self.projeto((a, "3"), (b, "4"))
        self.s.projetos.reservar(p)
        self.s.projetos.concluir(p)
        self.assertEqual(self.estado().projeto(p).status, StatusProjeto.CONCLUIDO)
        self.assertEqual((self.estado().material(a).fisico, self.estado().material(a).reservado,
                          self.estado().material(a).disponivel), (D(7), D(0), D(7)))
        self.assertEqual(sum(m.tipo is TipoMovimento.CONSUMO for m in self.estado().movimentos), 2)

    def test_rn07_rejeita_conclusao_sem_reserva_e_duplicada(self):
        id = self.material()
        p = self.projeto((id, "3"))
        with self.assertRaises(RegraNegocio):
            self.s.projetos.concluir(p)
        self.s.projetos.reservar(p)
        self.s.projetos.concluir(p)
        antes = self.repo.carregar()
        with self.assertRaises(RegraNegocio):
            self.s.projetos.concluir(p)
        self.assertEqual(self.repo.carregar(), antes)

    def test_rn08_cancelamento_libera_sem_alterar_fisico(self):
        id = self.material()
        p = self.projeto((id, "3"))
        self.s.projetos.reservar(p)
        self.s.projetos.cancelar(p)
        self.assertEqual((self.estado().material(id).fisico, self.estado().material(id).reservado), (D(10), D(0)))
        self.assertEqual(self.estado().movimentos[-1].tipo, TipoMovimento.LIBERACAO)

    def test_rn08_cancelamento_planejado_sem_movimento(self):
        id = self.material()
        p = self.projeto((id, "3"))
        quantidade = len(self.estado().movimentos)
        self.s.projetos.cancelar(p)
        self.assertEqual(self.estado().projeto(p).status, StatusProjeto.CANCELADO)
        self.assertEqual(len(self.estado().movimentos), quantidade)

    def test_rn08_terminais_nao_podem_ser_cancelados_ou_reservados(self):
        id = self.material()
        p = self.projeto((id, "1"))
        outro = self.projeto((id, "1"))
        self.s.projetos.cancelar(p)
        self.s.projetos.reservar(outro)
        self.s.projetos.concluir(outro)
        for projeto in (p, outro):
            for operacao in (self.s.projetos.cancelar, self.s.projetos.reservar):
                with self.subTest(projeto=projeto, operacao=operacao), self.assertRaises(RegraNegocio):
                    operacao(projeto)

    def test_rn09_contagem_registra_diferenca_assinada_e_preserva_custo(self):
        id = self.material()
        self.s.estoque.contar(id, D(8), "Duas unidades danificadas")
        self.assertEqual(self.estado().movimentos[-1].quantidade, D(-2))
        self.assertEqual(self.estado().material(id).custo_medio, D(2))
        self.s.estoque.contar(id, D(11), "Recontagem")
        self.assertEqual(self.estado().movimentos[-1].quantidade, D(3))

    def test_rn09_contagem_igual_gera_evidencia_zero(self):
        id = self.material()
        self.s.estoque.contar(id, D(10), "Conferido")
        self.assertEqual(self.estado().movimentos[-1].quantidade, D(0))

    def test_rn09_rejeita_abaixo_reserva_negativo_e_sem_justificativa(self):
        id = self.material()
        p = self.projeto((id, "4"))
        self.s.projetos.reservar(p)
        antes = self.repo.carregar()
        for contado, motivo in [("3", "Conferência"), ("-1", "Conferência"), ("5", "")]:
            with self.subTest(contado=contado), self.assertRaises(RegraNegocio):
                self.s.estoque.contar(id, D(contado), motivo)
            self.assertEqual(self.repo.carregar(), antes)

    def test_rn10_exclui_material_sem_referencias(self):
        id = self.material(saldo="0")
        self.s.cadastro.excluir(id)
        self.assertNotIn(id, self.estado().materiais)
        self.assertNotIn(id, self.estado().alertas)

    def test_rn10_rejeita_exclusao_com_saldo_historico_ou_projeto(self):
        com_saldo = self.material("A")
        com_historico = self.material("B")
        self.s.estoque.contar(com_historico, D(0), "Inventário")
        com_projeto = self.material("C", "0")
        self.projeto((com_projeto, "1"))
        for id in (com_saldo, com_historico, com_projeto):
            with self.subTest(id=id), self.assertRaises(RegraNegocio):
                self.s.cadastro.excluir(id)

    def test_rn10_edicao_preserva_id_saldo_e_snapshot_historico(self):
        id = self.material()
        self.s.cadastro.editar(id, dados("NOVO", nome="Nome novo"))
        self.assertEqual((self.estado().material(id).sku, self.estado().material(id).fisico), ("NOVO", D(10)))
        self.assertEqual(self.estado().movimentos[0].sku, "PAR")

    def test_rn11_strategy_minima_e_alvo(self):
        id = self.material(saldo="1")
        material = self.estado().material(id)
        self.assertEqual((ReposicaoMinima().sugerir(material), ReposicaoAlvo().sugerir(material)), (D(1), D(9)))

    def test_rn11_alerta_no_limite_com_sugestao_minima_zero(self):
        id = self.material(saldo="2")
        self.assertIn(id, self.estado().alertas)
        self.assertEqual(ReposicaoMinima().sugerir(self.estado().material(id)), 0)
        self.s.estoque.receber(id, D(1), D(2), "NF 2")
        self.assertNotIn(id, self.estado().alertas)
        self.assertEqual(ReposicaoAlvo().sugerir(self.estado().material(id)), 0)

    def test_rn11_rejeita_limites_invalidos(self):
        for minimo, alvo in [("-1", "3"), ("2", "2"), ("3", "2")]:
            with self.subTest(minimo=minimo, alvo=alvo), self.assertRaises(RegraNegocio):
                dados(minimo=D(minimo), alvo=D(alvo)).construir()

    def test_rn11_cancelamento_remove_alerta(self):
        id = self.material()
        p = self.projeto((id, "8"))
        self.s.projetos.reservar(p)
        self.assertIn(id, self.estado().alertas)
        self.s.projetos.cancelar(p)
        self.assertNotIn(id, self.estado().alertas)

    def test_strategy_substituivel_sem_mudar_servico(self):
        self.material(saldo="1")

        class PoliticaTeste:
            def sugerir(self, material):
                return D(42)

        self.assertEqual(self.s.consulta.sugerir_compras(PoliticaTeste())[0].quantidade, D(42))

    def test_rn12_commit_inclui_movimentos_alertas_e_auditoria(self):
        id = self.material(saldo="1")
        estado = self.estado()
        self.assertIn(id, estado.alertas)
        self.assertEqual((len(estado.movimentos), len(estado.auditoria)), (1, 2))
        self.assertEqual(estado.auditoria[-1].instante, INSTANTE)

    def test_rn12_falha_observador_descarta_tudo(self):
        id = self.material()
        antes = self.repo.carregar()
        publicador = PublicadorEventos()
        publicador.inscrever(AlertaEstoqueObserver())
        publicador.inscrever(AuditoriaObserver())

        class ObservadorFalho:
            def atualizar(self, evento, estado):
                raise RuntimeError("Falha injetada")

        publicador.inscrever(ObservadorFalho())
        servicos = montar(self.repo, lambda: INSTANTE, publicador)
        with self.assertRaises(RuntimeError):
            servicos.estoque.receber(id, D(1), D(1), "NF")
        self.assertEqual(self.repo.carregar(), antes)

    def test_rn12_copia_de_consulta_nao_modifica_repositorio(self):
        self.material()
        self.estado().materiais.clear()
        self.assertEqual(len(self.estado().materiais), 1)

    def test_observer_inscricao_e_remocao(self):
        publicador = PublicadorEventos()
        observador = AuditoriaObserver()
        estado = self.estado()
        publicador.inscrever(observador)
        publicador.inscrever(observador)
        publicador.publicar(EventoDominio("TESTE", "x", INSTANTE), estado)
        publicador.remover(observador)
        publicador.publicar(EventoDominio("TESTE", "x", INSTANTE), estado)
        self.assertEqual(len(estado.auditoria), 1)

    def test_numeros_aceitam_virgula_e_ponto(self):
        self.assertEqual(numero("12,5"), numero("12.5"))
        self.assertEqual(numero("1.000"), D(1))  # Ponto sempre é decimal; não representa milhar.

    def test_numeros_rejeitam_nao_finitos_float_e_formato_ambiguo(self):
        for valor in ("NaN", "Infinity", "-Infinity", "1.234,50", "abc", 1.2, True, "1e9999", "0.0000000000001"):
            with self.subTest(valor=valor), self.assertRaises(RegraNegocio):
                numero(valor)

    def test_pesquisa_por_nome_sku_e_sem_resultado(self):
        id = self.material("PAR-X")
        self.assertEqual(self.s.consulta.pesquisar("par-x")[0].id, id)
        self.assertEqual(len(self.s.consulta.pesquisar("parafuso")), 1)
        self.assertEqual(self.s.consulta.pesquisar("ausente"), [])
