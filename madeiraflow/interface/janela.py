from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
import logging
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from madeiraflow.aplicacao.portas import ErroPersistencia
from madeiraflow.aplicacao.servicos import DadosMaterial, Servicos
from madeiraflow.dominio.modelos import (
    Chapa, ItemProjeto, Material, Projeto, RegraNegocio, StatusProjeto, Unidade, exigir, numero,
)
from madeiraflow.dominio.reposicao import ReposicaoAlvo, ReposicaoMinima
from .formatos import horario, moeda, quantidade as q

VERDE = "#214b3b"
FUNDO = "#f2f3ed"
TEXTO = "#20372d"


def tabela(pai: tk.Misc, colunas: list[tuple[str, str, int]]) -> ttk.Treeview:
    quadro = ttk.Frame(pai)
    quadro.pack(fill="both", expand=True, pady=8)
    quadro.rowconfigure(0, weight=1)
    quadro.columnconfigure(0, weight=1)
    arvore = ttk.Treeview(quadro, columns=[c[0] for c in colunas], show="headings", selectmode="browse", height=6)
    for chave, titulo, largura in colunas:
        arvore.heading(chave, text=titulo)
        arvore.column(chave, width=largura, minwidth=60, anchor="w")
    vertical = ttk.Scrollbar(quadro, orient="vertical", command=arvore.yview)
    horizontal = ttk.Scrollbar(quadro, orient="horizontal", command=arvore.xview)
    arvore.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    arvore.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    arvore.tag_configure("alerta", foreground="#a34a1f", background="#fff4e5")
    return arvore


def preencher(arvore: ttk.Treeview, linhas: list[tuple[str, tuple, tuple]]) -> None:
    selecionado = arvore.selection()
    arvore.delete(*arvore.get_children())
    for id, valores, tags in linhas:
        arvore.insert("", "end", iid=id, values=valores, tags=tags)
    if selecionado and arvore.exists(selecionado[0]):
        arvore.selection_set(selecionado[0])


class Janela(ttk.Frame):
    def __init__(self, raiz: tk.Tk, servicos: Servicos, caminho: Path,
                 backup: Callable[[str], None], demo: bool = False) -> None:
        super().__init__(raiz, padding=20)
        self.raiz, self.servicos, self.backup = raiz, servicos, backup
        raiz.title("MadeiraFlow · Estoque e produção" + (" · Demonstração" if demo else ""))
        raiz.geometry("1230x780")
        raiz.minsize(960, 640)
        self._tema()
        self.pack(fill="both", expand=True)
        topo = ttk.Frame(self)
        topo.pack(fill="x", pady=(0, 14))
        ttk.Label(topo, text="MadeiraFlow", style="Marca.TLabel").pack(side="left")
        ttk.Label(topo, text="ESTOQUE E PRODUÇÃO", style="Suave.TLabel").pack(side="left", padx=22)
        ttk.Button(topo, text="Criar backup", command=self._backup).pack(side="right")
        ttk.Button(topo, text="Atualizar", command=lambda: self.executar(self.atualizar)).pack(side="right", padx=8)
        self.status = tk.StringVar(value="Pronto.")
        rodape = ttk.Frame(self)
        rodape.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Label(rodape, textvariable=self.status, style="Suave.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(rodape, text=f"{'DEMONSTRAÇÃO · ' if demo else ''}Base: {caminho}",
                  style="Suave.TLabel").pack(anchor="w")
        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True)
        self.paineis = {}
        for nome in ("Visão geral", "Materiais", "Projetos", "Movimentações", "Reposição"):
            painel = ttk.Frame(self.abas, padding=16)
            self.abas.add(painel, text=f"  {nome}  ")
            self.paineis[nome] = painel
        self.busca = tk.StringVar()
        self.politica = tk.StringVar(value="Até o alvo")
        self._visao()
        self._materiais()
        self._projetos()
        self._historico()
        self._reposicao()
        self.busca.trace_add("write", lambda *_: self.executar(self._filtrar_materiais))
        self.atualizar()

    def _tema(self) -> None:
        self.raiz.configure(background=FUNDO)
        estilo = ttk.Style(self.raiz)
        estilo.theme_use("clam")
        estilo.configure(".", font=("Segoe UI", 10), background=FUNDO, foreground=TEXTO)
        estilo.configure("TFrame", background=FUNDO)
        estilo.configure("TButton", padding=(12, 8), background="#e0e9dd")
        estilo.map("TButton", background=[("active", "#ccdcc9")])
        estilo.configure("TEntry", fieldbackground="white", padding=5)
        estilo.configure("TCombobox", fieldbackground="white", padding=5)
        estilo.configure("Marca.TLabel", font=("Segoe UI", 26, "bold"), foreground=VERDE)
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 19, "bold"), foreground=VERDE)
        estilo.configure("Suave.TLabel", foreground="#647366", font=("Segoe UI", 9))
        estilo.configure("Kpi.TLabel", font=("Segoe UI", 25, "bold"), foreground=VERDE)
        estilo.configure("Treeview", background="white", fieldbackground="white", rowheight=34)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=8, background="#dfe8da")
        estilo.map("Treeview", background=[("selected", VERDE)], foreground=[("selected", "white")])
        estilo.configure("TNotebook.Tab", padding=(10, 10))

    def executar(self, operacao: Callable, mensagem: str = "") -> bool:
        try:
            operacao()
            if mensagem:
                self.atualizar()
                self.status.set(mensagem)
            return True
        except (RegraNegocio, ErroPersistencia) as erro:
            self.status.set(str(erro))
            messagebox.showwarning("Operação não confirmada", str(erro), parent=self.raiz)
        except Exception:
            logging.exception("Erro inesperado na interface")
            messagebox.showerror("Operação interrompida", "Ocorreu um erro inesperado. Consulte o terminal e atualize os dados.",
                                 parent=self.raiz)
        return False

    def _cabecalho(self, painel: ttk.Frame, titulo: str, subtitulo: str) -> ttk.Frame:
        ttk.Label(painel, text=titulo, style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(painel, text=subtitulo, style="Suave.TLabel").pack(anchor="w", pady=(4, 12))
        barra = ttk.Frame(painel)
        barra.pack(fill="x")
        return barra

    def _visao(self) -> None:
        painel = self.paineis["Visão geral"]
        self._cabecalho(painel, "Sua oficina, em perspectiva", "Disponibilidade confiável para planejar a próxima produção.")
        cartoes = ttk.Frame(painel)
        cartoes.pack(fill="x", pady=20)
        self.kpis = []
        for nome in ("Materiais cadastrados", "Projetos reservados", "Materiais em alerta", "Valor físico em estoque"):
            cartao = ttk.LabelFrame(cartoes, text=nome, padding=16)
            cartao.pack(side="left", fill="both", expand=True, padx=(0, 12))
            valor = ttk.Label(cartao, text="0", style="Kpi.TLabel")
            valor.pack(anchor="w")
            self.kpis.append(valor)
        ttk.Label(painel, text="Atenção à reposição", style="Titulo.TLabel").pack(anchor="w", pady=(8, 0))
        ttk.Label(painel, text="Físico: no depósito  ·  Reservado: comprometido com projetos  ·  Disponível = físico − reservado",
                  style="Suave.TLabel").pack(side="bottom", anchor="w", pady=6)
        self.alertas = tabela(painel, [("sku", "SKU", 130), ("nome", "Material", 290),
                                      ("disponivel", "Disponível", 120), ("minimo", "Mínimo", 110), ("unidade", "Unidade", 100)])

    def _materiais(self) -> None:
        painel = self.paineis["Materiais"]
        barra = self._cabecalho(painel, "Catálogo e estoque", "Selecione um material para editar, receber ou conferir o inventário.")
        for nome, acao in [("Novo material", lambda: self.formulario_material()),
                           ("Editar", lambda: self.formulario_material(self._material_selecionado())),
                           ("Excluir", self._excluir), ("Receber", self._receber), ("Inventário", self._contar)]:
            ttk.Button(barra, text=nome, command=lambda fn=acao: self.executar(fn)).pack(side="left", padx=(0, 7))
        ttk.Entry(barra, textvariable=self.busca, width=25).pack(side="right")
        ttk.Label(barra, text="Buscar SKU/nome: ").pack(side="right")
        ttk.Label(painel, text="Quantidades: 12,5 ou 12.5, sem milhares. Chapas e UN são inteiras. Saldo muda por recebimento, inventário e projetos.",
                  style="Suave.TLabel").pack(side="bottom", anchor="w", pady=6)
        self.materiais = tabela(painel, [("sku", "SKU", 125), ("nome", "Material", 260), ("un", "Un.", 70),
                                        ("fisico", "Físico", 90), ("reservado", "Reservado", 90),
                                        ("disponivel", "Disponível", 100), ("custo", "Custo médio", 110),
                                        ("valor", "Valor físico", 120), ("caracteristicas", "Características", 320)])
        self.materiais.bind("<Double-1>", lambda _: self.executar(lambda: self.formulario_material(self._material_selecionado())))

    def _projetos(self) -> None:
        barra = self._cabecalho(self.paineis["Projetos"], "Projetos de produção", "Planeje os itens, reserve o conjunto e conclua o consumo uma única vez.")
        for nome, acao in [("Novo projeto", lambda: self.formulario_projeto()),
                           ("Editar", lambda: self.formulario_projeto(self._projeto_selecionado())),
                           ("Ver itens", self._itens), ("Reservar", lambda: self.acao_projeto("reservar")),
                           ("Concluir produção", lambda: self.acao_projeto("concluir")),
                           ("Cancelar projeto", lambda: self.acao_projeto("cancelar"))]:
            ttk.Button(barra, text=nome, command=lambda fn=acao: self.executar(fn)).pack(side="left", padx=(0, 7))
        self.projetos = tabela(self.paineis["Projetos"], [("nome", "Projeto", 290), ("cliente", "Cliente", 250),
                                                        ("status", "Situação", 170), ("itens", "Itens", 80)])
        self.projetos.bind("<Double-1>", lambda _: self.executar(self._itens))

    def _historico(self) -> None:
        painel = self.paineis["Movimentações"]
        self._cabecalho(painel, "Histórico rastreável", "Registros do mais recente ao mais antigo. SKU e nome preservam o contexto de cada operação.")
        abas = ttk.Notebook(painel)
        abas.pack(fill="both", expand=True)
        movimentos, auditoria = ttk.Frame(abas), ttk.Frame(abas)
        abas.add(movimentos, text="Movimentações")
        abas.add(auditoria, text="Auditoria")
        self.movimentos = tabela(movimentos, [("hora", "Data e hora", 160), ("tipo", "Tipo", 110),
                                             ("sku", "SKU", 110), ("nome", "Material", 220),
                                             ("qtd", "Quantidade", 100), ("un", "Un.", 65),
                                             ("fisico", "Físico após", 100), ("reservado", "Reserva após", 110),
                                             ("ref", "Referência", 340)])
        self.auditoria = tabela(auditoria, [("hora", "Data e hora", 170), ("acao", "Ação", 240), ("detalhe", "Detalhe", 600)])

    def _reposicao(self) -> None:
        painel = self.paineis["Reposição"]
        barra = self._cabecalho(painel, "Planejar a próxima compra", "Sugestões para materiais com disponível menor ou igual ao mínimo.")
        ttk.Label(barra, text="Política de reposição: ").pack(side="left")
        seletor = ttk.Combobox(barra, textvariable=self.politica, values=["Até o mínimo", "Até o alvo"], state="readonly", width=20)
        seletor.pack(side="left")
        seletor.bind("<<ComboboxSelected>>", lambda _: self.executar(self._atualizar_reposicao))
        ttk.Label(painel, text="Estimativa baseada no custo médio registrado. A sugestão não cria pedido nem altera o estoque.",
                  style="Suave.TLabel").pack(side="bottom", anchor="w")
        self.total_compra = ttk.Label(painel, style="Titulo.TLabel")
        self.total_compra.pack(side="bottom", anchor="e", pady=12)
        self.compras = tabela(painel, [("sku", "SKU", 125), ("nome", "Material", 260), ("disp", "Disponível", 110),
                                      ("min", "Mínimo", 100), ("alvo", "Alvo", 100),
                                      ("qtd", "Comprar", 100), ("un", "Un.", 60), ("valor", "Estimativa", 130)])

    def atualizar(self) -> None:
        self.estado = self.servicos.consulta.consultar()
        valores = [len(self.estado.materiais), sum(p.status is StatusProjeto.RESERVADO for p in self.estado.projetos.values()),
                   len(self.estado.alertas), moeda(sum((m.valor_estoque for m in self.estado.materiais.values()), Decimal(0)))]
        for rotulo, valor in zip(self.kpis, valores):
            rotulo.configure(text=str(valor))
        preencher(self.alertas, [(m.id, (m.sku, m.nome, q(m.disponivel), q(m.minimo), m.unidade.value), ("alerta",))
                                for m in self.estado.materiais.values() if m.id in self.estado.alertas])
        self._filtrar_materiais()
        preencher(self.projetos, [(p.id, (p.nome, p.cliente, p.status.value, len(p.itens)), ()) for p in self.estado.projetos.values()])
        preencher(self.movimentos, [(m.id, (horario(m.instante), m.tipo.value, m.sku, m.nome, q(m.quantidade),
                                           m.unidade.value, q(m.fisico_apos), q(m.reservado_apos), m.referencia), ())
                                   for m in reversed(self.estado.movimentos)])
        preencher(self.auditoria, [(str(i), (horario(a.instante), a.acao, a.detalhe), ())
                                  for i, a in reversed(list(enumerate(self.estado.auditoria)))])
        self._atualizar_reposicao()
        self.status.set("Dados atualizados. Alterações são salvas automaticamente após cada operação.")

    def _filtrar_materiais(self) -> None:
        termo = self.busca.get().strip().casefold()
        preencher(self.materiais, [(m.id, (m.sku, m.nome, m.unidade.value, q(m.fisico), q(m.reservado),
                                           q(m.disponivel), q(m.custo_medio), moeda(m.valor_estoque), m.caracteristicas),
                                   ("alerta",) if m.estoque_baixo else ())
                                  for m in self.estado.materiais.values() if termo in f"{m.sku} {m.nome}".casefold()])

    def _atualizar_reposicao(self) -> None:
        politicas = {"Até o mínimo": ReposicaoMinima(), "Até o alvo": ReposicaoAlvo()}
        sugestoes = self.servicos.consulta.sugerir_compras(politicas[self.politica.get()])
        preencher(self.compras, [(s.material.id, (s.material.sku, s.material.nome, q(s.material.disponivel),
                                                 q(s.material.minimo), q(s.material.alvo), q(s.quantidade),
                                                 s.material.unidade.value, moeda(s.estimativa)), ()) for s in sugestoes])
        self.total_compra.configure(text="Estimativa total: " + moeda(sum((s.estimativa for s in sugestoes), Decimal(0))))

    def _selecionado(self, arvore: ttk.Treeview) -> str:
        exigir(bool(arvore.selection()), "Selecione uma linha da tabela.")
        return arvore.selection()[0]

    def _material_selecionado(self) -> Material:
        return self.servicos.consulta.consultar().material(self._selecionado(self.materiais))

    def _projeto_selecionado(self) -> Projeto:
        return self.servicos.consulta.consultar().projeto(self._selecionado(self.projetos))

    def _excluir(self) -> None:
        material = self._material_selecionado()
        if messagebox.askyesno("Excluir material", f"Excluir {material.sku} do catálogo?", parent=self.raiz):
            self.executar(lambda: self.servicos.cadastro.excluir(material.id), "Material excluído.")

    def _receber(self) -> None:
        material = self._material_selecionado()

        def salvar(valores: dict[str, str]) -> None:
            self.servicos.estoque.receber(material.id, numero(valores["quantidade"]), numero(valores["custo"]), valores["referencia"])

        Formulario(self, f"Receber · {material.sku}", [("quantidade", f"Quantidade ({material.unidade.value})", ""),
                    ("custo", "Custo unitário (R$)", ""), ("referencia", "Documento / fornecedor", "")], salvar)

    def _contar(self) -> None:
        material = self._material_selecionado()

        def salvar(valores: dict[str, str]) -> None:
            self.servicos.estoque.contar(material.id, numero(valores["contado"]), valores["justificativa"])

        Formulario(self, f"Inventário · {material.sku} · reservado {q(material.reservado)}", [
            ("contado", f"Contagem física ({material.unidade.value})", q(material.fisico)),
            ("justificativa", "Justificativa da conferência", "")], salvar)

    def acao_projeto(self, acao: str) -> None:
        projeto = self._projeto_selecionado()
        mensagens = {"reservar": "Reservar todos os materiais?", "concluir": "Confirmar o consumo integral dos materiais reservados?",
                     "cancelar": "Cancelar o projeto e liberar a reserva existente?"}
        if messagebox.askyesno(projeto.nome, mensagens[acao], parent=self.raiz):
            operacoes = {"reservar": self.servicos.projetos.reservar, "concluir": self.servicos.projetos.concluir,
                         "cancelar": self.servicos.projetos.cancelar}
            self.executar(lambda: operacoes[acao](projeto.id), "Operação confirmada e salva.")

    def _itens(self) -> None:
        projeto = self._projeto_selecionado()
        estado = self.servicos.consulta.consultar()
        linhas = [f"{projeto.nome} · {projeto.cliente} · {projeto.status.value}", ""]
        for item in projeto.itens:
            material = estado.material(item.material_id)
            linhas.append(f"{material.sku} · {q(item.quantidade)} {material.unidade.value} · disponível agora: {q(material.disponivel)}")
        messagebox.showinfo("Itens do projeto", "\n".join(linhas), parent=self.raiz)

    def _backup(self) -> None:
        destino = filedialog.asksaveasfilename(parent=self.raiz, title="Criar backup em arquivo novo",
                                             defaultextension=".sqlite3", filetypes=[("Banco SQLite", "*.sqlite3")])
        if destino:
            self.executar(lambda: self.backup(destino), "Backup criado: " + destino)

    def formulario_material(self, material: Material | None = None) -> FormularioMaterial:
        return FormularioMaterial(self, material)

    def formulario_projeto(self, projeto: Projeto | None = None) -> FormularioProjeto:
        if projeto is not None:
            projeto.exigir_planejado()
        return FormularioProjeto(self, projeto)


class Formulario(tk.Toplevel):
    def __init__(self, janela: Janela, titulo: str, campos: list[tuple[str, str, str]],
                 salvar: Callable[[dict[str, str]], None] | None = None) -> None:
        super().__init__(janela.raiz)
        self.janela, self.salvar = janela, salvar
        self.title(titulo)
        self.transient(janela.raiz)
        self.configure(background=FUNDO)
        self.resizable(False, False)
        self.corpo = ttk.Frame(self, padding=22)
        self.corpo.pack(fill="both", expand=True)
        self.variaveis: dict[str, tk.StringVar] = {}
        self.entradas: dict[str, tk.Widget] = {}
        self.linha = 0
        for chave, rotulo, valor in campos:
            self.campo(chave, rotulo, valor)
        self.botoes = ttk.Frame(self, padding=(22, 10, 22, 18))
        self.botoes.pack(fill="x")
        self.botao_salvar = ttk.Button(self.botoes, text="Salvar", command=self.confirmar)
        self.botao_salvar.pack(side="right")
        ttk.Button(self.botoes, text="Cancelar", command=self.destroy).pack(side="right", padx=8)
        self.bind("<Escape>", lambda _: self.destroy())
        self.grab_set()
        if self.entradas:
            next(iter(self.entradas.values())).focus_set()

    def campo(self, chave: str, rotulo: str, valor: str = "", opcoes: list[str] | None = None) -> None:
        ttk.Label(self.corpo, text=rotulo).grid(row=self.linha, column=0, sticky="w", padx=(0, 14), pady=7)
        variavel = tk.StringVar(value=valor)
        entrada = (ttk.Combobox(self.corpo, textvariable=variavel, values=opcoes, state="readonly", width=46)
                   if opcoes else ttk.Entry(self.corpo, textvariable=variavel, width=49))
        entrada.grid(row=self.linha, column=1, sticky="ew", pady=7)
        self.variaveis[chave], self.entradas[chave] = variavel, entrada
        self.linha += 1

    def valores(self) -> dict[str, str]:
        return {chave: variavel.get() for chave, variavel in self.variaveis.items()}

    def submeter(self) -> None:
        if self.salvar is not None:
            self.salvar(self.valores())

    def confirmar(self) -> None:
        if self.janela.executar(self.submeter, "Operação confirmada e salva."):
            self.destroy()


class FormularioMaterial(Formulario):
    def __init__(self, janela: Janela, material: Material | None) -> None:
        self.material = material
        chapa = isinstance(material, Chapa)
        super().__init__(janela, "Editar material" if material else "Novo material", [])
        self.campo("sku", "SKU", material.sku if material else "")
        self.campo("nome", "Nome", material.nome if material else "")
        self.campo("unidade", "Unidade", material.unidade.value if material else "CHAPA", [u.value for u in Unidade])
        self.campo("minimo", "Estoque mínimo", q(material.minimo) if material else "0")
        self.campo("alvo", "Estoque alvo", q(material.alvo) if material else "10")
        self.campo("descricao", "Acabamento / especificação", (material.acabamento if chapa else material.especificacao) if material else "")
        for chave, rotulo in [("comprimento", "Comprimento (mm)"), ("largura", "Largura (mm)"), ("espessura", "Espessura (mm)")]:
            self.campo(chave, rotulo, q(getattr(material, chave)) if chapa else "")
        if material:
            self.entradas["unidade"].configure(state="disabled")
        self.variaveis["unidade"].trace_add("write", lambda *_: self._dimensoes())
        self._dimensoes()
        self.entradas["sku"].focus_set()

    def _dimensoes(self) -> None:
        for chave in ("comprimento", "largura", "espessura"):
            self.entradas[chave].configure(state="normal" if self.variaveis["unidade"].get() == "CHAPA" else "disabled")

    def submeter(self) -> None:
        v = self.valores()
        unidade = Unidade(v["unidade"])
        dimensoes = {k: numero(v[k]) if unidade is Unidade.CHAPA else Decimal(0)
                     for k in ("comprimento", "largura", "espessura")}
        dados = DadosMaterial(sku=v["sku"], nome=v["nome"], unidade=unidade, minimo=numero(v["minimo"]),
                              alvo=numero(v["alvo"]), descricao=v["descricao"], **dimensoes)
        if self.material is None:
            self.janela.servicos.cadastro.cadastrar(dados)
        else:
            self.janela.servicos.cadastro.editar(self.material.id, dados)


class FormularioProjeto(Formulario):
    def __init__(self, janela: Janela, projeto: Projeto | None) -> None:
        self.projeto = projeto
        self.itens = list(projeto.itens) if projeto else []
        self.estado = janela.servicos.consulta.consultar()
        super().__init__(janela, "Editar projeto" if projeto else "Novo projeto", [
            ("nome", "Nome do projeto", projeto.nome if projeto else ""),
            ("cliente", "Cliente", projeto.cliente if projeto else "")])
        self.catalogo = {f"{m.sku} · {m.nome} ({m.unidade.value})": m.id for m in self.estado.materiais.values()}
        self.campo("material", "Material", next(iter(self.catalogo), ""), list(self.catalogo))
        self.campo("quantidade", "Quantidade", "1")
        barra = ttk.Frame(self.corpo)
        barra.grid(row=self.linha, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Button(barra, text="Adicionar item", command=lambda: janela.executar(self.adicionar)).pack(side="left")
        ttk.Button(barra, text="Remover selecionado", command=lambda: janela.executar(self.remover)).pack(side="left", padx=8)
        quadro = ttk.Frame(self.corpo, height=180)
        quadro.grid(row=self.linha + 1, column=0, columnspan=2, sticky="nsew")
        self.lista = tabela(quadro, [("sku", "SKU", 150), ("qtd", "Quantidade", 130), ("un", "Unidade", 90)])
        self.lista.configure(height=5)
        self._atualizar_itens()

    def adicionar(self) -> None:
        v = self.valores()
        exigir(v["material"] in self.catalogo, "Cadastre e selecione um material.")
        id = self.catalogo[v["material"]]
        exigir(not any(i.material_id == id for i in self.itens), "Material já adicionado. Remova o item para alterar a quantidade.")
        quantidade = self.estado.material(id).unidade.validar(numero(v["quantidade"]))
        self.itens.append(ItemProjeto(id, quantidade))
        self._atualizar_itens()

    def remover(self) -> None:
        id = self.janela._selecionado(self.lista)
        self.itens = [i for i in self.itens if i.material_id != id]
        self._atualizar_itens()

    def _atualizar_itens(self) -> None:
        preencher(self.lista, [(i.material_id, (self.estado.material(i.material_id).sku, q(i.quantidade),
                                               self.estado.material(i.material_id).unidade.value), ()) for i in self.itens])

    def submeter(self) -> None:
        v = self.valores()
        if self.projeto is None:
            self.janela.servicos.projetos.criar(v["nome"], v["cliente"], tuple(self.itens))
        else:
            self.janela.servicos.projetos.editar(self.projeto.id, v["nome"], v["cliente"], tuple(self.itens))
