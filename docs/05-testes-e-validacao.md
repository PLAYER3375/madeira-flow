# Testes e validação

Execute `python scripts/verificar.py` ou `test.bat`. O relatório fica em build/resultados-testes.txt; falha retorna código diferente de zero. Para os sete testes gráficos: defina RUN_GUI_TESTS=1 em sessão com Tk/display. Sem a variável, esses sete aparecem como ignorados; isso não é evidência de sua execução.

## Estratégia

| Nível | Arquivos | O que verifica |
|---|---|---|
| Regras e colaboração | tests/test_regras.py | Sucesso/rejeição de RN01–12, precisão, estados, integralidade, Strategy/Observer |
| Integração | tests/test_persistencia.py | SQLite real, reabertura, rollback, revisão concorrente, corrupção, backup, CLI e arquitetura |
| Interface | tests/test_interface.py | Widgets/formulários/callbacks reais; mensagens substituídas para não bloquear |

São 70 métodos de teste: 63 sem GUI e sete gráficos, com subcenários parametrizados por subTest. A evidência de entrega está em evidencias/testes.txt. Ambiente local: Windows e Python 3.14.2. O workflow prepara Windows/Linux e Python 3.11/3.14; não há evidência de CI remoto.

## Sucesso e rejeição das regras críticas

| Regra | Sucesso | Rejeição/limite |
|---|---|---|
| RN01 | Normalização/cadastro | SKU repetido ou obrigatório ausente |
| RN02 | Chapas e frações de até três casas em unidades contínuas | Fração em UN/CHAPA, quarta casa, dimensão inválida, troca de unidade |
| RN03 | Média ponderada e entrada | Quantidade/custo inválidos, referência vazia |
| RN04 | Físico/reservado/disponível e valor | Entidade imutável e reservado maior que físico |
| RN05 | Projeto com vários itens | Sem itens/nome/cliente, repetido, inexistente, não positivo ou fracionado |
| RN06 | Reserva integral/edição planejada | Falta no último item, disputa por saldo, reserva/edição repetida |
| RN07 | Consumo de vários itens | Conclusão sem reserva ou duplicada |
| RN08 | Cancelar planejado/reservado | Cancelar ou reservar estados terminais |
| RN09 | Ajustes positivo/negativo/zero | Abaixo da reserva, negativo, sem justificativa |
| RN10 | Exclusão livre/edição preservando histórico | Saldo, movimento ou projeto impede exclusão |
| RN11 | Políticas e remoção de alerta | Limites inválidos; alerta no mínimo com compra mínima zero |
| RN12 | Commit conjunto | Observador falha, escrita falha, trigger SQLite aborta e cópia não vaza |

O rollback real instala trigger que aborta UPDATE, tenta recebimento e compara o snapshot/revisão antes e depois, inclusive após reabrir. O conflito usa duas conexões e tenta gravar revisão antiga após um commit. Os testes de arquivo inválido verificam que o conteúdo não é substituído.

## Verificação manual complementar

Conferir em seu monitor: legibilidade com escala do Windows, barras horizontais, navegação entre abas, foco/seleção, fechar/cancelar formulários sem salvar, mensagens reais e diálogo de backup. Os testes gráficos automatizados não substituem acessibilidade e avaliação visual. Siga docs/07-apresentacao-e-demo.md com base nova e confirme os saldos indicados.

## Limites

Não se mediu capacidade/latência, não se testou queda física de energia e não se simulou ambiente multiusuário em rede. A atomicidade testada cobre falhas de aplicação/escrita e integridade transacional SQLite no escopo local. Testes de interface exercitam os callbacks reais e substituem apenas diálogos bloqueantes.
