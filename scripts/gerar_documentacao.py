"""Gera PDF/SVG/HTML offline a partir dos capítulos e das fontes UML da entrega."""

from html import escape
import json
from pathlib import Path
import re
import textwrap

from reportlab.graphics import renderPDF, renderSVG
from reportlab import rl_config
from reportlab.graphics.shapes import Drawing, Ellipse, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

RAIZ = Path(__file__).resolve().parents[1]
# Evita diferenças apenas por data/ID interno ao regenerar os mesmos documentos.
rl_config.invariant = 1
DOCS = RAIZ / "docs"
UML = DOCS / "uml"
VERDE = colors.HexColor("#214b3b")
CLARO = colors.HexColor("#e9efe3")
LARANJA = colors.HexColor("#ad602d")
FONT = "Helvetica"
BOLD = "Helvetica-Bold"
for normal, negrito in [
    (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
]:
    if normal.exists() and negrito.exists():
        pdfmetrics.registerFont(TTFont("MF", str(normal)))
        pdfmetrics.registerFont(TTFont("MF-Bold", str(negrito)))
        pdfmetrics.registerFontFamily("MF", normal="MF", bold="MF-Bold", italic="MF", boldItalic="MF-Bold")
        FONT, BOLD = "MF", "MF-Bold"
        break


class Vetor:
    """Coordenadas em pixels a partir do topo, compartilhadas por SVG e PDF."""

    def __init__(self, largura, altura):
        self.w, self.h = largura, altura
        self.d = Drawing(largura, altura)
        self.rect(0, 0, largura, altura, colors.white)

    def rect(self, x, y, w, h, cor=CLARO):
        self.d.add(Rect(x, self.h-y-h, w, h, fillColor=cor, strokeColor=VERDE, strokeWidth=1))

    def text(self, x, y, texto, size=17, bold=False, anchor="start", cor=VERDE):
        self.d.add(String(x, self.h-y, texto, fontName=BOLD if bold else FONT,
                          fontSize=size, fillColor=cor, textAnchor=anchor))

    def linha(self, x1, y1, x2, y2, seta=False, tracejada=False, triangulo=False):
        self.d.add(Line(x1, self.h-y1, x2, self.h-y2, strokeColor=VERDE,
                        strokeWidth=1.1, strokeDashArray=[6, 4] if tracejada else None))
        if seta or triangulo:
            import math
            angulo = math.atan2(y2-y1, x2-x1)
            pontos = [(x2, y2)] + [(x2-13*math.cos(angulo+s), y2-13*math.sin(angulo+s)) for s in (-0.45, 0.45)]
            self.d.add(Polygon([v for x,y in pontos for v in (x, self.h-y)],
                               fillColor=colors.white if triangulo else VERDE, strokeColor=VERDE))

    def caixa(self, x, y, titulo, linhas, w=260):
        h = 58 + 24*len(linhas)
        self.rect(x, y, w, h, colors.white)
        self.rect(x, y, w, 38)
        self.text(x+w/2, y+26, titulo, 16, True, "middle")
        for i, linha in enumerate(linhas):
            self.text(x+12, y+61+i*24, linha, 14)
        return x, y, w, h

    def salvar(self, nome):
        svg = renderSVG.drawToString(self.d)
        # Navegadores usam fontes locais; PDF incorpora a fonte TTF registrada.
        svg = svg.replace('font-family: MF-Bold', 'font-family: Segoe UI, Arial').replace('font-family: MF', 'font-family: Segoe UI, Arial')
        (UML / f"{nome}.svg").write_text(svg, encoding="utf-8")
        return self.d


def relacionar(v, a, b, rotulo="", heranca=False, tracejada=False, composicao=False, agregacao=False):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    if abs((ay+ah/2)-(by+bh/2)) > abs((ax+aw/2)-(bx+bw/2)) * 0.65:
        x1, x2 = ax+aw/2, bx+bw/2
        y1, y2 = (ay+ah, by) if by > ay else (ay, by+bh)
    else:
        y1, y2 = ay+ah/2, by+bh/2
        x1, x2 = (ax+aw, bx) if bx > ax else (ax, bx+bw)
    v.linha(x1, y1, x2, y2, seta=not (composicao or agregacao), triangulo=heranca, tracejada=tracejada)
    if composicao or agregacao:
        import math
        angulo = math.atan2(y2-y1,x2-x1)
        ux,uy=math.cos(angulo),math.sin(angulo)
        pontos=[(x1,y1),(x1+8*ux-6*uy,y1+8*uy+6*ux),(x1+16*ux,y1+16*uy),
                (x1+8*ux+6*uy,y1+8*uy-6*ux)]
        v.d.add(Polygon([p for x,y in pontos for p in (x,v.h-y)],
                        fillColor=VERDE if composicao else colors.white,strokeColor=VERDE))
    if rotulo:
        v.text((x1+x2)/2+8, (y1+y2)/2-8, rotulo, 14)


def casos():
    v = Vetor(1250, 980)
    v.rect(330, 45, 855, 890, colors.white)
    v.text(755, 78, "MadeiraFlow — fronteira do sistema", 22, True, "middle")
    nomes = ["Manter catálogo", "Receber materiais", "Acompanhar disponibilidade", "Conciliar inventário",
             "Planejar projeto", "Reservar materiais", "Concluir produção", "Cancelar projeto",
             "Rastrear movimentos e auditoria", "Planejar reposição"]
    atores = [(155, 200, "Estoquista", [1, 2, 4]), (155, 485, "Produção", [3, 5, 6, 7, 8]),
              (155, 785, "Gestor", [3, 9, 10])]
    for x, y, nome, ucs in atores:
        v.d.add(Ellipse(x, v.h-y, 15, 15, fillColor=colors.white, strokeColor=VERDE))
        for p in [(x,y+15,x,y+65), (x-30,y+35,x+30,y+35), (x,y+65,x-25,y+100), (x,y+65,x+25,y+100)]:
            v.linha(*p)
        v.text(x, y+125, nome, 18, True, "middle")
        for uc in ucs:
            v.linha(x+30, y+35, 500, 135+(uc-1)*79)
    for i, nome in enumerate(nomes, 1):
        y = 135+(i-1)*79
        v.d.add(Ellipse(790, v.h-y, 290, 30, fillColor=CLARO, strokeColor=VERDE))
        v.text(790, y+6, f"UC{i:02d} · {nome}", 17, anchor="middle")
    return v.salvar("01-casos-de-uso")


def dominio():
    v = Vetor(1450, 970)
    v.text(35, 35, "Modelo conceitual — conceitos, atributos e multiplicidades", 23, True)
    b = {}
    especificacoes = [
        ("Material", 80, 90, ["sku; nome; unidade", "minimo; alvo", "fisico; reservado; custo_medio", "/disponivel"]),
        ("Chapa", 30, 380, ["comprimento; largura; espessura", "acabamento"]),
        ("Insumo", 430, 380, ["especificacao"]),
        ("Projeto", 1000, 90, ["nome; cliente; status"]),
        ("ItemProjeto", 1000, 380, ["quantidade"]),
        ("Movimentacao", 900, 690, ["instante; tipo; quantidade", "sku; nome; unidade", "fisico_apos; reservado_apos", "custo_unitario; referencia"]),
    ]
    for nome,x,y,linhas in especificacoes:
        b[nome] = (x,y,300,58+24*len(linhas))
    # Rotas ortogonais mantêm multiplicidades visíveis e evitam atravessar classes.
    for xs,ys,xe,ye in [(180,380,180,300),(180,300,170,300),(580,380,580,280),(580,280,300,280)]:
        v.linha(xs,ys,xe,ye)
    v.linha(170,300,170,244,triangulo=True); v.linha(300,280,300,244,triangulo=True)
    v.text(40,340,"especializa",15); v.text(445,340,"especializa",15)
    relacionar(v,b['Projeto'],b['ItemProjeto'],"1 contém 1..*",composicao=True)
    for pontos,rotulo,x,y in [
        ([(1000,420),(850,420),(850,170),(380,170)],"0..* itens especificam 1 material",480,155),
        ([(900,765),(800,765),(800,550),(375,550),(375,244)],"0..* movimentos registram 1 material",390,535),
        ([(1200,765),(1380,765),(1380,130),(1300,130)],"0..* movimentos / 0..1 projeto",910,650),
    ]:
        for i in range(len(pontos)-1):
            v.linha(*pontos[i],*pontos[i+1],seta=i==len(pontos)-2)
        v.text(x,y,rotulo,15)
    for nome,x,y,linhas in especificacoes:
        v.caixa(x,y,nome,linhas,300)
    v.text(40, 920, "Disponível = físico − reservado; 0 ≤ reservado ≤ físico. Referências no código usam IDs permanentes.", 18)
    return v.salvar("02-dominio")


def design():
    v = Vetor(1920, 1330)
    v.text(25, 30, "Classes de design — contratos, coordenação e variações", 23, True)
    fonte = (UML / "03-classes-design.puml").read_text(encoding="utf-8")
    posicoes = {
        "Janela": (530,65), "CadastroService": (20,260), "EstoqueService": (330,260),
        "ProjetoService": (640,260), "ConsultaService": (950,260), "Transacoes": (480,540),
        "EstadoEstoque": (20,800), "RepositorioEstado": (480,800), "SQLiteRepositorio": (640,1100),
        "MemoriaRepositorio": (950,1100), "PublicadorEventos": (1020,540), "ObservadorEstoque": (1310,800),
        "AlertaEstoqueObserver": (1260,1100), "AuditoriaObserver": (1570,1100),
        "PoliticaReposicao": (1430,260), "ReposicaoMinima": (1330,540), "ReposicaoAlvo": (1630,540),
        "Material": (20,1100), "Projeto": (330,1100),
    }
    classes = {}
    for match in re.finditer(r"^(?:abstract )?(class|interface) (\w+)(?:[^\n{]*)?(?: \{\n([^}]+)\})?$", fonte, re.M):
        tipo, nome, atributos = match.groups()
        linhas = [s.strip().replace("+", "") for s in (atributos or "").splitlines()]
        linhas = [s for linha in linhas for s in textwrap.wrap(linha, 34)]
        if tipo == "interface":
            linhas.insert(0,"«Protocol»")
        if not linhas:
            linhas = ["implementação do contrato"]
        x,y = posicoes[nome]
        classes[nome] = (x,y,270,58+24*len(linhas))
    for linha in fonte.splitlines():
        match = re.match(r'(\w+)(?: "[^"]+")? (\.\.\|>|-->|\.\.>|o--)(?: "[^"]+")? (\w+)', linha)
        if match:
            a,rel,b = match.groups()
            if a in classes and b in classes:
                relacionar(v,classes[a],classes[b],"1 → 0..*" if rel == "o--" else "",heranca=rel=="..|>",tracejada=rel.startswith(".."),agregacao=rel=="o--")
    for nome,(x,y,w,h) in classes.items():
        match = re.search(rf"^(?:abstract )?(class|interface) {nome}\b(?:[^\n{{]*)?(?: \{{\n([^}}]+)\}})?$",fonte,re.M)
        tipo,attrs = match.groups()
        linhas = [s for l in (attrs or "").splitlines() for s in textwrap.wrap(l.strip().replace("+",""),34)]
        if tipo == "interface": linhas.insert(0,"«Protocol»")
        v.caixa(x,y,nome,linhas or ["implementação do contrato"],270)
    v.text(30,1300,"Seta tracejada triangular: implementação estrutural de Protocol. Entidades devolvem novas versões; o estado reúne os agregados.",18)
    return v.salvar("03-classes-design")


def sequencia(concluir=False):
    nome = "05-sequencia-conclusao" if concluir else "04-sequencia-reserva"
    v = Vetor(1880, 1740)
    nomes = ["Produção", "Janela", "ProjetoService", "Transacoes", "RepositorioEstado", "EstadoEstoque",
             "Projeto", "Material", "PublicadorEventos", "ObservadorEstoque"]
    centros = [95+i*187 for i in range(10)]
    for i,n in enumerate(nomes):
        v.rect(centros[i]-86,35,172,65)
        v.text(centros[i],73,n,14,True,"middle")
        v.linha(centros[i],100,centros[i],1695,tracejada=True)
    y = 140

    def mensagem(a,b,rotulo,resposta=False):
        nonlocal y
        y += 46
        if a==b:
            v.text(centros[a]+10,y,rotulo,14)
        else:
            v.linha(centros[a],y,centros[b],y,seta=True,tracejada=resposta)
            v.text((centros[a]+centros[b])/2,y-10,rotulo,14,anchor="middle")

    mensagem(0,1,"concluir e confirmar" if concluir else "reservar e confirmar")
    mensagem(1,2,"concluir(id)" if concluir else "reservar(id)")
    mensagem(2,3,"executar(acao, detalhe, operacao)")
    mensagem(3,4,"carregar()")
    mensagem(4,3,"Snapshot(estado isolado, revisao)",True)
    mensagem(3,2,"operacao(estado) [função local]")
    mensagem(2,6,"concluir() [exige RESERVADO]" if concluir else "exigir_planejado()")
    if not concluir:
        mensagem(2,7,"loop TODOS os itens: validar_reserva(q)")
    else:
        mensagem(6,2,"novo projeto CONCLUIDO",True)
    v.rect(10,y+18,1850,30,colors.HexColor("#f7eee2"))
    v.text(25,y+39,"alt — estado permitido e todos os itens válidos",15,True)
    y += 40
    mensagem(2,7,"loop itens: consumir_reserva(q)" if concluir else "loop itens: reservar(q)")
    mensagem(7,2,"nova entidade",True)
    mensagem(2,5,"guardar_material(material); registrar movimento")
    if not concluir:
        mensagem(2,6,"reservar() → novo projeto RESERVADO")
    mensagem(2,5,"guardar_projeto(novo)")
    mensagem(2,3,"operação concluída localmente",True)
    mensagem(3,8,"publicar(evento, estado)")
    mensagem(8,9,"loop inscritos: atualizar(evento, estado)")
    mensagem(3,5,"validar()")
    mensagem(3,4,"salvar(estado, revisao)")
    mensagem(4,4,"UPDATE por revisão; COMMIT")
    mensagem(3,2,"sucesso após commit",True)
    mensagem(2,1,"sucesso",True)
    mensagem(1,0,"saldos e situação atualizados",True)
    v.rect(10,y+18,1850,30,colors.HexColor("#f7eee2"))
    v.text(25,y+39,"else — estado proibido / falta em qualquer item",15,True)
    y += 40
    mensagem(2,3,"RegraNegocio; sem salvar",True)
    mensagem(3,2,"erro; snapshot descartado",True)
    mensagem(2,1,"mensagem de rejeição",True)
    mensagem(1,0,"estado confirmado anterior preservado",True)
    v.text(30,1650,"Falha de observador, escrita ou conflito de revisão também impede confirmação. Nenhum efeito externo nos observadores.",17,True)
    return v.salvar(nome)


def estados():
    v = Vetor(1300,740)
    v.text(30,40,"Ciclo de vida do projeto",25,True)
    planejado=(80,170,260,100); reservado=(530,170,260,100)
    concluido=(980,170,260,100); cancelado=(530,520,260,100)
    for a,b,label in [(planejado,reservado,"reservar [todos disponíveis]"),(reservado,concluido,"concluir [consumir reserva]"),
                      (planejado,cancelado,"cancelar"),(reservado,cancelado,"cancelar [liberar reserva]")]:
        relacionar(v,a,b,label)
    for nome,box in [("PLANEJADO",planejado),("RESERVADO",reservado),("CONCLUIDO",concluido),("CANCELADO",cancelado)]:
        x,y,w,h=box; v.rect(*box); v.text(x+w/2,y+58,nome,23,True,"middle")
    v.d.add(Ellipse(25,v.h-220,9,9,fillColor=VERDE,strokeColor=VERDE))
    v.linha(35,220,80,220,True)
    v.linha(130,170,130,100)
    v.linha(130,100,285,100)
    v.linha(285,100,285,170,True)
    v.text(90,85,"editar [itens válidos]",17)
    for x,y in [(1110,340),(920,570)]:
        v.d.add(Ellipse(x,v.h-y,13,13,fillColor=colors.white,strokeColor=VERDE))
        v.d.add(Ellipse(x,v.h-y,8,8,fillColor=VERDE,strokeColor=VERDE))
    v.linha(1110,270,1110,327,True)
    v.linha(790,570,907,570,True)
    v.text(35,695,"CONCLUIDO e CANCELADO são terminais. Reserva não altera físico; conclusão reduz físico e reservado juntos.",18)
    return v.salvar("06-estados-projeto")


def inline(texto):
    texto = escape(texto)
    texto = re.sub(r"\[([^]]+)\]\([^)]+\)",r"\1",texto)
    texto = re.sub(r"\*\*([^*]+)\*\*",r"<b>\1</b>",texto)
    return re.sub(r"`([^`]+)`",r"\1",texto)


def elementos(markdown, estilos):
    linhas=markdown.splitlines(); resultado=[]; i=0
    while i < len(linhas):
        linha=linhas[i]
        if linha.startswith("|"):
            tabela=[]
            while i<len(linhas) and linhas[i].startswith("|"):
                celulas=[s.strip() for s in linhas[i].strip("|").split("|")]
                if not all(re.fullmatch(r"[:\- ]+",s) for s in celulas):
                    tabela.append([Paragraph(inline(s),estilos["Celula"]) for s in celulas])
                i+=1
            larguras = [505/len(tabela[0])]*len(tabela[0])
            if len(larguras)==3: larguras=[85,245,175]
            if len(larguras)==4: larguras=[55,160,95,195]
            t=Table(tabela,colWidths=larguras,repeatRows=1,hAlign="LEFT")
            t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),CLARO),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#ccd8c6")),
                                   ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),
                                   ("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
            resultado.extend([t,Spacer(1,14)]); continue
        if linha.startswith("```"):
            bloco=[]; i+=1
            while i<len(linhas) and not linhas[i].startswith("```"):
                bloco.append(linhas[i]); i+=1
            resultado.append(Preformatted("\n".join(bloco),estilos["Codigo"]))
        elif linha.startswith("#"):
            n=len(linha)-len(linha.lstrip("#"))
            resultado.append(Paragraph(inline(linha.lstrip("# ")),estilos["Titulo" if n==1 else "Secao"]))
        elif linha.strip():
            resultado.append(Paragraph(inline(linha),estilos["Corpo"]))
        i+=1
    return resultado


def rodape(canvas, documento):
    canvas.saveState(); canvas.setFont(FONT,8); canvas.setFillColor(VERDE)
    canvas.drawString(44,25,"MadeiraFlow Python · APSOO")
    canvas.drawRightString(A4[0]-44,25,str(documento.page)); canvas.restoreState()


def documento(autoria):
    estilos={
        "Titulo":ParagraphStyle("Titulo",fontName=BOLD,fontSize=23,leading=29,textColor=VERDE,spaceAfter=18),
        "Secao":ParagraphStyle("Secao",fontName=BOLD,fontSize=14,leading=19,textColor=VERDE,spaceBefore=15,spaceAfter=9,keepWithNext=True),
        "Corpo":ParagraphStyle("Corpo",fontName=FONT,fontSize=10,leading=15,spaceAfter=9),
        "Celula":ParagraphStyle("Celula",fontName=FONT,fontSize=8.5,leading=12),
        "Codigo":ParagraphStyle("Codigo",fontName="Courier",fontSize=8,leading=11),
    }
    conteudo=[Spacer(1,70),Paragraph("MadeiraFlow",estilos["Titulo"]),Paragraph("Estoque e produção para marcenarias",estilos["Secao"]),
              Paragraph("DOCUMENTO TÉCNICO · VERSÃO PYTHON",estilos["Corpo"]),Spacer(1,40)]
    for valor in [autoria["disciplina"],autoria["professor"],*[f"{a['nome']} · {a['matricula']}" for a in autoria["integrantes"]],
                  autoria["turma"],autoria["ano"],"Preencher autoria antes da submissão.",
                  "12 RF · 6 RNF · 12 RN · 10 casos de uso · Strategy · Observer · DI"]:
        conteudo.append(Paragraph(inline(valor),estilos["Corpo"]))
    htmls=[]
    for caminho in sorted(DOCS.glob("0[1-6]-*.md")):
        conteudo.append(PageBreak())
        markdown=caminho.read_text(encoding="utf-8")
        conteudo.extend(elementos(markdown,estilos))
        htmls.append("<article><pre>"+escape(markdown)+"</pre></article>")
    SimpleDocTemplate(str(DOCS/"documento-tecnico.pdf"),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=42,bottomMargin=45,
                      title="MadeiraFlow Python — Documento técnico",author="Projeto APSOO").build(conteudo,onFirstPage=rodape,onLaterPages=rodape)
    (DOCS/"documento-tecnico.html").write_text('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Documento técnico</title>'
        '<style>body{max-width:1100px;margin:auto;padding:40px;font:16px/1.6 system-ui;color:#214b3b}pre{white-space:pre-wrap;font:inherit}article{border-bottom:1px solid #ccd8c6;padding:20px 0}</style>'
        +"<h1>MadeiraFlow Python — documento técnico</h1>"+"".join(htmls)+"</html>",encoding="utf-8")


SLIDES = [
    ("MadeiraFlow", "Estoque e produção para marcenarias", ["Projeto final de Análise e Projeto de Software Orientado a Objetos", "Python · Tkinter · SQLite", "Autoria: preencher docs/autoria.json"], "evidencias/01-visao-geral.png"),
    ("Uma chapa pode já estar prometida", "Problema e atores", ["Saldo físico sozinho não informa o compromisso com encomendas.", "Estoquista recebe e confere; produção planeja e consome; gestor acompanha e repõe.", "Disponível = físico − reservado."], "evidencias/02-materiais.png"),
    ("Comportamento além de CRUD", "12 RF · 6 RNF · 12 regras", ["Reserva de todos os itens ou de nenhum.", "Conclusão única; cancelamento libera sem alterar físico.", "Contagem nunca abaixo do reservado; custo médio ponderado."], None),
    ("Conceitos antes da tecnologia", "Domínio e Information Expert", ["Material conhece unidade, saldo e custo.", "Projeto conhece itens e ciclo de vida.", "ItemProjeto expressa quantidade; Movimentacao preserva o contexto."], "uml/02-dominio.svg"),
    ("Cada responsabilidade tem um lugar", "Interface → Aplicação → Domínio", ["Janela apresenta e coleta; serviços coordenam.", "Entidades imutáveis protegem regras e devolvem novas versões.", "Repositório confirma o conjunto; contratos permitem substituição."], None),
    ("Padrões com resultado observável", "Strategy · Observer · injeção de dependências", ["Strategy troca política mínima/alvo sem alterar ConsultaService.", "Observer mantém alertas e auditoria sem dependência concreta nos serviços.", "Observadores participam do snapshot; relógio e repositório são injetados."], None),
    ("Demo 1 — planejar e reservar", "Ao vivo: Balcão Horizonte", ["Base nova: MDF branco físico 10, reservado 4, disponível 6.", "Projeto: 1 MDF branco + 10 parafusos; PLANEJADO não altera saldos.", "Reservar → MDF 10 / 5 / 5. Conferir RESERVA e auditoria."], "evidencias/03-projetos.png"),
    ("Demo 2 — concluir produção", "Consumo integral e baixa única", ["Concluir Balcão → MDF físico 9, reservado 4, disponível 5.", "Disponível não muda: o material já estava comprometido.", "Tentar concluir de novo → rejeição sem nova baixa."], None),
    ("Falhar sem deixar metade pronta", "Reserva integral e transação", ["Novo projeto: 1 MDF + 99999 cavilhas.", "A reserva rejeita a falta e preserva também a chapa.", "Snapshot isolado → regras → observers → validar → salvar por revisão."], None),
    ("Reposição usa o disponível", "Uma escolha real do gestor", ["Cavilha: disponível 60, mínimo 80 e alvo 400.", "Política mínima sugere 20; alvo sugere 340.", "Cancelar Cozinha Aurora libera 90 e remove o alerta de cavilhas."], "evidencias/05-reposicao.png"),
    ("Regras verificáveis", "70 testes: 63 de regras/integração e sete gráficos", ["Sucesso e rejeição das regras críticas.", "SQLite real: reabertura, rollback, revisão concorrente, corrupção e backup.", "Widgets/callbacks reais; test.bat e relatório. CI preparado, sem execução remota afirmada."], None),
    ("Limites e evolução", "Decisões sustentam o escopo", ["Offline e base local pequena; snapshot até 32 MB.", "Sem corte, retalhos, fiscal, devolução ou consumo parcial.", "Evolução exige requisitos e estados novos; persistência tem contrato substituível."], None),
]


def slides(autoria):
    c=Canvas(str(DOCS/"apresentacao.pdf"),pagesize=(1280,720)); c.setTitle("MadeiraFlow Python — Apresentação")
    htmls=[]
    for i,(titulo,sub,itens,imagem) in enumerate(SLIDES,1):
        itens=list(itens)
        if i==1:
            itens[-1]=" · ".join(f"{a['nome']} / {a['matricula']}" for a in autoria["integrantes"])
        c.setFillColor(colors.HexColor("#f3f4ee")); c.rect(0,0,1280,720,fill=1,stroke=0)
        c.setFillColor(VERDE); c.rect(0,0,14,720,fill=1,stroke=0)
        c.setFont(BOLD,13); c.setFillColor(LARANJA); c.drawString(48,680,"MADEIRAFLOW / APSOO / PYTHON")
        c.setFillColor(VERDE); c.setFont(BOLD,34); c.drawString(48,612,titulo)
        c.setFont(FONT,19); c.drawString(48,566,sub)
        largura=490 if imagem else 1150; y=500
        for item in itens:
            estilo=ParagraphStyle("Slide",fontName=FONT,fontSize=22,leading=32,textColor=VERDE)
            p=Paragraph("• "+inline(item),estilo); w,h=p.wrap(largura,300); p.drawOn(c,52,y-h); y-=h+26
        if imagem and imagem.endswith(".png") and (DOCS/imagem).exists():
            c.drawImage(str(DOCS/imagem),570,180,width=660,height=418,preserveAspectRatio=True,anchor="c",mask="auto")
        elif imagem:
            desenho = DESENHOS[imagem.split("/")[-1].replace(".svg","")]
            escala=min(660/desenho.width,390/desenho.height); c.saveState(); c.translate(570,160); c.scale(escala,escala)
            renderPDF.draw(desenho,c,0,0); c.restoreState()
        c.setFont(FONT,11); c.drawString(48,25,f"{i} / {len(SLIDES)} · Projeto final APSOO")
        c.showPage()
        htmls.append(f'<section><small>MADEIRAFLOW / APSOO / PYTHON</small><h1>{escape(titulo)}</h1><p>{escape(sub)}</p><div class="conteudo">'
                     +'<ul>'+''.join(f'<li>{escape(item)}</li>' for item in itens)+'</ul>'
                     +(f'<img src="{imagem}" alt="{escape(sub)}">' if imagem else '')+f'</div><footer>{i} / {len(SLIDES)}</footer></section>')
    c.save()
    (DOCS/"apresentacao.html").write_text('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>MadeiraFlow — apresentação</title>'
        '<style>*{box-sizing:border-box}body{margin:0;font:22px/1.5 system-ui;color:#214b3b;background:#f3f4ee}section{display:none;min-height:100vh;padding:45px 4vw 80px;border-left:14px solid #214b3b}section.ativo{display:block}h1{font-size:44px;line-height:1.2;margin:25px 0}small{color:#ad602d}.conteudo{display:flex;gap:35px;align-items:center;margin-top:35px}ul{flex:1}li{margin:25px 0}img{width:55%;max-height:58vh;object-fit:contain}footer{position:fixed;bottom:20px;font-size:14px}nav{position:fixed;right:20px;bottom:20px}button{padding:10px 18px;font:inherit;font-size:16px}@media print{section{display:block;break-after:page}nav{display:none}footer{position:static}}@media(max-width:800px){.conteudo{display:block}img{width:100%}h1{font-size:32px}}</style>'
        +''.join(htmls)+'<nav><button onclick="m(n-1)">← Anterior</button> <button onclick="m(n+1)">Próximo →</button></nav>'
        '<script>const s=[...document.querySelectorAll("section")];let n=0;function m(i){n=Math.max(0,Math.min(s.length-1,i));s.forEach((v,j)=>v.classList.toggle("ativo",j===n));location.hash=n+1;scrollTo(0,0)}document.addEventListener("keydown",e=>{if(["ArrowRight"," ","PageDown"].includes(e.key)){e.preventDefault();m(n+1)}if(["ArrowLeft","PageUp"].includes(e.key)){e.preventDefault();m(n-1)}});m(Number(location.hash.slice(1)||1)-1)</script></html>',encoding="utf-8")


DESENHOS={}


def main():
    UML.mkdir(exist_ok=True)
    desenhos=[casos(),dominio(),design(),sequencia(),sequencia(True),estados()]
    nomes=[p.stem for p in sorted(UML.glob("*.puml"))]
    DESENHOS.update(zip(nomes,desenhos))
    c=Canvas(str(DOCS/"modelos-uml.pdf"),pagesize=landscape(A3)); c.setTitle("MadeiraFlow Python — Modelos UML")
    for nome,desenho in DESENHOS.items():
        w,h=landscape(A3) if desenho.width>desenho.height*1.1 else A3
        c.setPageSize((w,h)); c.setFillColor(VERDE); c.setFont(BOLD,18); c.drawString(30,h-35,nome)
        escala=min((w-60)/desenho.width,(h-110)/desenho.height)
        c.saveState(); c.translate(30,h-65-desenho.height*escala); c.scale(escala,escala); renderPDF.draw(desenho,c,0,0); c.restoreState()
        c.setFont(FONT,8); c.drawString(30,20,f"Fonte editável: {nome}.puml · versão Python · ampliar PDF para inspecionar detalhes"); c.showPage()
    c.save()
    (UML/"index.html").write_text('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Modelos UML — MadeiraFlow</title>'
        '<style>body{font:17px system-ui;padding:25px;color:#214b3b}img{max-width:100%;border:1px solid #ccc}article{margin-bottom:50px}</style><h1>Modelos UML — MadeiraFlow Python</h1>'
        +''.join(f'<article><h2>{n}</h2><a href="{n}.puml">Fonte PlantUML</a><br><a href="{n}.svg"><img src="{n}.svg" alt="{n}"></a></article>' for n in nomes)+"</html>",encoding="utf-8")
    autoria=json.loads((DOCS/"autoria.json").read_text(encoding="utf-8"))
    documento(autoria); slides(autoria)
    print("Gerados: documento técnico, seis modelos SVG, caderno UML e apresentação PDF/HTML.")


if __name__ == "__main__":
    main()
