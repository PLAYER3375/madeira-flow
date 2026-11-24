# Arquitetura e decisões de design OO

## Responsabilidades

| Módulo | Papel |
|---|---|
| dominio | Entidades imutáveis, regras, estado, histórico e políticas |
| aplicacao | CadastroService, EstoqueService, ProjetoService, ConsultaService, Transacoes, contratos/eventos |
| infraestrutura | SQLiteRepositorio, MemoriaRepositorio, codec JSON e demonstração |
| interface | Janela, formulários e formatação Tkinter |
| composicao.py | Liga dependências por construtor |
| __main__.py | Configuração, entrada CLI e ciclo da sessão |

Interface → Aplicação → Domínio. Infraestrutura implementa RepositorioEstado, contrato da aplicação. Domínio não importa UI/SQLite/aplicação/infraestrutura; teste AST verifica a restrição. Servicos é um conjunto explícito de dependências, sem busca global.

## GRASP

| Princípio | Decisão concreta |
|---|---|
| Information Expert | Material calcula disponível/custo/reserva; Projeto protege transições |
| Creator | CadastroService dispõe dos dados para construir Chapa/Insumo; Projeto contém ItemProjeto |
| Controller | Serviços coordenam intenções do operador, sem concentrar regras das entidades |
| Low Coupling | Transacoes depende do contrato RepositorioEstado, substituível por memória |
| High Cohesion | Cadastro, estoque, projetos, consultas e persistência têm responsáveis próprios |
| Polymorphism / Protected Variations | Protocol para políticas/observadores; Material abstrato com Chapa/Insumo |
| Pure Fabrication / Indirection | Transacoes/repositório isolam responsabilidades técnicas |

## Strategy — reposição

**Problema/contexto:** gestor decide comprar apenas a falta até o mínimo ou recompor até o alvo. **Solução:** PoliticaReposicao.sugerir é implementada por ReposicaoMinima e ReposicaoAlvo. **Participantes:** esses três tipos, ConsultaService.sugerir_compras e seletor da Janela. Serviço depende do contrato, sem condicional por nome da política.

Disponível=60/mínimo=80/alvo=400 → mínima=20/alvo=340. Acima do mínimo, ambas zero. No limite, alerta permanece e mínima=0. **Custo:** classes adicionais para fórmulas pequenas, justificadas pela escolha funcional real. Teste injeta terceira política sem mudar serviço.

## Observer — efeitos locais

**Problema/contexto:** vários casos de uso precisam atualizar alertas/auditoria, sem repetir dependências concretas em cada serviço. **Solução:** PublicadorEventos mantém ObservadorEstoque; AlertaEstoqueObserver recalcula alertas e AuditoriaObserver acrescenta registro. **Participantes:** esses tipos, EventoDominio, Transacoes e composicao.montar.

Notificação síncrona após alteração local e antes de salvar. Evento é fato local pendente de confirmação. Observadores só alteram snapshot isolado; falha descarta tentativa inteira. Não enviam e-mail/API. A ordem dos atuais não interfere, pois escrevem coleções diferentes. **Custo:** fluxo indireto e recálculo O(n). Efeitos externos futuros exigiriam pós-commit/outbox.

## Injeção de dependências

montar(repositorio, relogio, eventos) liga objetos por construtor. Testes usam memória e horário fixo; produção SQLite/UTC. Interface recebe Servicos e função de backup. Não se introduziu Singleton/Registry sem necessidade concreta. Strategy e Observer são os dois padrões centrais; DI sustenta testabilidade.

## Decisões arquiteturais

**ADR-001 — Python desktop:** Python 3.11+, Tkinter e biblioteca padrão permitem execução offline sem servidor/pacotes. Web/toolkit externo adicionariam dependências à demonstração local. `.pyz` exige Python/Tk, sem embutir interpretador. Tecnologia livre: enunciado p. 4.

**ADR-002 — imutabilidade/transação:** dataclass(frozen=True) e tuplas protegem estado das entidades. Operações devolvem novas entidades por replace; EstadoEstoque as reúne. Transacoes carrega cópia, executa, publica, valida relações e salva uma vez. Python não fornece privacidade absoluta; contratos e fronteira de serviços preservam regras de uso.

**ADR-003 — SQLite/snapshot:** tabela estado(id=1,revisao,conteudo) contém JSON versionado e decimais em texto, sem ORM/pickle. BEGIN IMMEDIATE, UPDATE condicionado à revisão e COMMIT confirmam o conjunto. Revisão antiga causa ConflitoDeVersao e exige nova decisão do usuário. Snapshot facilita unidade de consistência neste escopo; tabelas normalizadas seriam melhores para grandes volumes/consultas, com mapeamento adicional. Leitura/escrita O(tamanho da base), teto 32 MB, uso local. application_id, versão, quick_check e validação de relações recusam base inválida. Backup usa API SQLite e fecha explicitamente o destino. Revisão não transforma a interface em sistema colaborativo.

**ADR-004 — precisão/histórico:** Decimal evita representação binária de float; média quatro casas HALF_UP e exibição monetária duas. Movimentos guardam ID e SKU/nome da época. Corrigir cadastro não reescreve histórico. Não se somam unidades diferentes.

## Modelos

Em uml/: casos de uso, domínio conceitual, classes de design, sequências de reserva/conclusão e estados do projeto. Conceitual contém apenas conceitos de negócio; design acrescenta serviços/contratos/adaptadores. Fontes PlantUML editáveis; SVG/PDF para leitura offline. Os vetores locais representam as mesmas relações/chamadas documentadas, sem serviço externo.
