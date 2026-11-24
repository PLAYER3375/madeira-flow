# Rastreabilidade e entrega

## Requisitos, código e teste

| RF / UC | Implementação | Evidência |
|---|---|---|
| RF01–02 / UC01 | CadastroService; DadosMaterial; Material; EstadoEstoque | test_rn01*, test_rn02*, test_rn10*; formulário material |
| RF03 / UC02 | EstoqueService.receber; Material.receber | test_rn03*; recebimento UI |
| RF04 / UC03 | ConsultaService; Material.disponivel/valor_estoque | test_rn04*; pesquisa |
| RF05 / UC04 | EstoqueService.contar; Material.contar | test_rn09*; inventário UI |
| RF06 / UC05 | ProjetoService.criar/editar; Projeto; ItemProjeto | test_rn05*, test_rn06_planejado*; formulário projeto |
| RF07 / UC06 | ProjetoService.reservar; Material.validar_reserva/reservar | test_rn06*; callbacks UI |
| RF08 / UC07 | ProjetoService.concluir; Material.consumir_reserva | test_rn07*; callbacks UI |
| RF09 / UC08 | ProjetoService.cancelar; Material.liberar | test_rn08* |
| RF10 / UC09 | Movimentacao; AuditoriaObserver; Janela | test_rn07*, test_rn10_edicao*, test_rn12_commit* |
| RF11 / UC10 | AlertaEstoqueObserver; Material.estoque_baixo | test_rn11* |
| RF12 / UC10 | PoliticaReposicao; ConsultaService.sugerir_compras | test_rn11_strategy*; test_strategy*; seletor UI |

RNF01/06: lançadores/testes/.pyz. RNF02: reabertura e falhas. RNF03: concorrência/revisão antiga. RNF04: widgets e roteiro manual. RNF05: AST do domínio. Nomes completos no relatório de testes.

## Oito entregáveis do enunciado

| Entregável / páginas | Artefato desta versão |
|---|---|
| 1 — problema/escopo, p. 8 | 01-visao-e-escopo.md e documento-tecnico.pdf |
| 2 — RF/RNF/RN, p. 9 | 02-requisitos-e-regras.md: 12 RF, 6 RNF, 12 RN |
| 3 — casos de uso, p. 10 | 03-casos-de-uso.md; dez UC; duas especificações detalhadas; UML 01 |
| 4 — domínio, p. 12 | UML 02: conceitos e multiplicidades |
| 5 — classes de design, p. 13 | UML 03: operações, contratos, serviços/adaptadores |
| 6 — sequências, p. 14 | UML 04/05: reserva/conclusão, guardas e falhas |
| 7 — design, p. 15–16 | 04-arquitetura-e-design.md; GRASP, Strategy, Observer, DI |
| 8 — código/execução, p. 18 | Pacotes Python, scripts, Git, .pyz, base configurável e demo |

O pacote final da p. 23 inclui documento técnico, UML, fonte/histórico, README, software e apresentação. O ZIP gerado por scripts/empacotar.py reúne esses itens e o manifesto SHA-256. O guia pessoal externo é excluído.

## Coerência dos modelos

Conceitos Material/Chapa/Insumo/Projeto/ItemProjeto/Movimentacao têm classes correspondentes. Projeto contém uma tupla com um ou mais itens; cada item referencia material por ID. Movimento referencia material e opcionalmente projeto por ID e guarda rótulos históricos. Contratos Protocol são implementados estruturalmente por SQLite/memória, políticas e observadores. Métodos das sequências correspondem a ProjetoService, Transacoes, entidades e repositório. Ciclo coincide com StatusProjeto.

| Critério da p. 25 | Peso | Evidência |
|---|---|---|
| Análise e requisitos | 20% | Visão, regras, casos de uso e matriz |
| Modelagem/design OO | 25% | UML, GRASP, padrões contextualizados e arquitetura |
| Implementação funcional | 35% | UI, serviços, invariantes e SQLite |
| Qualidade/testes | 10% | Suíte executável, relatório, organização e CI preparado |
| Apresentação/demo | 10% | Slides e roteiro de dois fluxos centrais com rejeições |

## Histórico e pendências humanas

Git registra etapas reais desta reconstrução; autoria automatizada Codex. Não há histórico de semestre inventado, nem publicação remota. O bundle transporta os commits junto do ZIP. A apresentação oral é futura: os materiais estão preparados, e o estudante precisa preencher autoria em autoria.json, regenerar os documentos e ensaiar a defesa das decisões.
