# Requisitos e regras de negócio

## Requisitos funcionais

| ID | Capacidade | UC |
|---|---|---|
| RF01 | Cadastrar chapas/insumos com SKU, unidade, limites e características | UC01 |
| RF02 | Pesquisar, editar e excluir materiais preservando referências | UC01 |
| RF03 | Receber material com quantidade, custo e referência | UC02 |
| RF04 | Consultar físico, reservado, disponível e valor | UC03 |
| RF05 | Conferir inventário com contagem e justificativa | UC04 |
| RF06 | Criar/editar projetos planejados com vários materiais | UC05 |
| RF07 | Reservar integralmente os materiais de um projeto | UC06 |
| RF08 | Concluir produção consumindo reserva uma única vez | UC07 |
| RF09 | Cancelar projeto e liberar eventual reserva | UC08 |
| RF10 | Consultar movimentos e auditoria em ordem inversa de registro | UC09 |
| RF11 | Exibir alertas atualizados de disponível baixo | UC10 |
| RF12 | Comparar reposição até o mínimo e até o alvo | UC10 |

## Requisitos não funcionais

| ID | Restrição mensurável | Verificação |
|---|---|---|
| RNF01 | Offline com Python 3.11+ e Tk, sem pacotes de execução externos | Lançadores e `.pyz`; execução local em 3.14.2 |
| RNF02 | Preservar dados e confirmar negócio/histórico/alertas/auditoria juntos | Reabertura, rollback SQLite e falhas injetadas |
| RNF03 | Rejeitar gravação com revisão antiga preservando commit recente | Duas conexões e conflito otimista |
| RNF04 | Fluxos pela interface e erro compreensível sem fechar formulário inválido | Sete testes gráficos e roteiro manual |
| RNF05 | Domínio independente de UI, aplicação, SQLite e infraestrutura | Teste AST |
| RNF06 | Um comando de teste, relatório e código de erro em falha | `test.bat` / `scripts/verificar.py` |

Base até 32 MB de conteúdo JSON. Operação local pequena, sem meta de latência não medida.

## Regras

| ID | Regra |
|---|---|
| RN01 | SKU obrigatório/único, trim e maiúsculas, até 30 caracteres A–Z/0–9/._-. Nome e características obrigatórios |
| RN02 | CHAPA/UN inteiros; M/L/KG até três casas. Dimensões positivas. Tipo/unidade não mudam na edição |
| RN03 | Recebimento com quantidade/custo positivos, custo até duas casas e referência. Média ponderada pelo físico anterior, com quatro casas HALF_UP |
| RN04 | 0 ≤ reservado ≤ físico; disponível = físico − reservado; sem edição de saldo no cadastro |
| RN05 | Projeto com nome, cliente e ao menos um item existente; sem duplicatas; quantidade positiva compatível com unidade |
| RN06 | Somente PLANEJADO é editável/reservável. Reserva valida TODOS os itens e rejeita integralmente se faltar qualquer um |
| RN07 | Somente RESERVADO conclui. Consumo reduz físico/reservado e gera movimentos; segunda baixa rejeitada |
| RN08 | PLANEJADO/RESERVADO podem cancelar. Liberação preserva físico. CONCLUIDO/CANCELADO são terminais |
| RN09 | Contagem não negativa, nunca abaixo do reservado, justificada; diferença assinada inclusive zero; custo médio preservado |
| RN10 | Exclusão exige saldo zero e ausência de projeto/movimento. Edição preserva ID/saldos; histórico mantém SKU/nome da época |
| RN11 | Mínimo ≥ 0; alvo > mínimo; limites compatíveis com unidade. Alerta se disponível ≤ mínimo. Mínima=max(0,mínimo−disponível); alvo=max(0,alvo−disponível), somente em alerta |
| RN12 | Operação, movimentos, alertas e auditoria confirmados juntos; falha de validação, observador ou persistência descarta tentativa |

Média = (físico anterior × custo médio anterior + quantidade recebida × custo unitário) / novo físico. Não há conversão/soma de quantidades entre unidades distintas. Estimativa não é cotação. Referência de recebimento não é chave fiscal de deduplicação. Vírgula ou ponto são decimais, sem milhares. Números não finitos são rejeitados; valores de entrada e saldo resultante são limitados a um trilhão.
