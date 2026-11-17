# Casos de uso

Fronteira: MadeiraFlow. Atores humanos: Estoquista, Produção e Gestor. Persistência é detalhe interno. Diagrama em `uml/01-casos-de-uso.svg`, fonte PlantUML ao lado.

| UC | Objetivo | Ator | RF / RN |
|---|---|---|---|
| UC01 | Manter catálogo de materiais | Estoquista | RF01–02 / RN01–02, RN10–11 |
| UC02 | Receber materiais | Estoquista | RF03 / RN02–04, RN12 |
| UC03 | Acompanhar disponibilidade | Gestor/Produção | RF04 / RN04 |
| UC04 | Conciliar inventário | Estoquista | RF05 / RN02, RN04, RN09, RN12 |
| UC05 | Planejar projeto | Produção | RF06 / RN05–06 |
| UC06 | Reservar materiais do projeto | Produção | RF07 / RN04, RN06, RN11–12 |
| UC07 | Concluir produção | Produção | RF08 / RN04, RN07, RN12 |
| UC08 | Cancelar projeto | Produção | RF09 / RN08, RN12 |
| UC09 | Rastrear movimentos e auditoria | Gestor | RF10 / RN10, RN12 |
| UC10 | Planejar reposição | Gestor | RF11–12 / RN11 |

## UC06 — Reservar materiais (central)

**Ator:** produção. **Gatilho:** separar os materiais de uma encomenda. **Pré:** base acessível e projeto PLANEJADO com itens válidos. **Garantia mínima:** rejeição preserva todo o estado confirmado. **Pós:** projeto RESERVADO; físico preservado; reservado acrescido de cada item; movimentos/alertas/auditoria confirmados juntos.

1. Ator seleciona projeto e consulta itens.
2. Solicita Reservar e confirma.
3. `ProjetoService.reservar` chama `Transacoes.executar`, que carrega snapshot isolado e revisão.
4. Operação chama `Projeto.exigir_planejado` e `Material.validar_reserva` para TODOS os itens.
5. Cada `Material.reservar` devolve nova entidade; serviço guarda material e registra RESERVA.
6. `Projeto.reservar` devolve projeto RESERVADO, guardado no estado.
7. Publicador notifica alertas/auditoria e o estado valida relações.
8. Repositório salva se a revisão ainda é atual; interface mostra saldos.

**Alternativas:** sem seleção, solicita uma linha. Confirmação cancelada não executa. Estado proibido rejeita. Falta de material informa SKU, disponível e solicitado; nada é comprometido. Falha de observador, banco ou conflito de revisão não confirma. Em conflito, ator atualiza e decide tentar novamente.

**Exemplo:** A físico=10, B físico=1, reservas zero. Pedido A=3/B=2 falha; A reservado continua zero. Após receber B=1, pode reservar. **Sequência:** `04-sequencia-reserva`. **Testes:** RN06 integral, falta no último item, disputa; RN12 rollback.

## UC07 — Concluir produção (central)

**Ator:** produção. **Gatilho:** confirmar consumo dos materiais separados. **Pré:** projeto RESERVADO. **Pós:** CONCLUIDO; físico/reservado reduzidos pela mesma quantidade; disponível preservado; movimentos CONSUMO, alertas e auditoria confirmados.

1. Ator seleciona projeto, consulta itens e solicita Concluir produção.
2. Interface explica a baixa integral e solicita confirmação.
3. Transacoes carrega snapshot; `Projeto.concluir` exige RESERVADO e prepara nova entidade.
4. Cada `Material.consumir_reserva` reduz físico/reservado; serviço guarda e registra CONSUMO.
5. Serviço guarda o projeto CONCLUIDO.
6. Observadores atualizam snapshot; relações são validadas; repositório confirma uma vez.
7. Interface mostra situação e saldos.

**Alternativas:** cancelar confirmação não altera dados. PLANEJADO/CANCELADO/CONCLUIDO rejeitam; segunda conclusão não baixa novamente. Falha em qualquer colaboração descarta conjunto. **Exemplo:** físico=10/reservado=4/disponível=6 → físico=6/reservado=0/disponível=6. **Sequência:** `05-sequencia-conclusao`. **Testes:** RN07 vários itens, sem reserva e duplicada.

## Demais especificações

**UC01:** estoquista informa SKU/nome/unidade/limites/características; sistema valida e cadastra. Busca localiza por nome/SKU. Edição mantém tipo/unidade/ID/saldos. Exclusão exige confirmação e ausência de saldo/histórico/projeto. Erro preserva campos; cancelar formulário não grava.

**UC02:** seleciona material, informa quantidade/custo/referência. Sistema valida, calcula média ponderada e registra ENTRADA. Físico zero adota custo do recebimento. Entrada inválida/falha de escrita não confirma.

**UC03:** consulta saldos e valor na Visão geral/Materiais. Busca vazia mostra todos; sem correspondência, tabela vazia. Valores monetários são agregáveis; quantidades de unidades diferentes não.

**UC04:** informa contado e justificativa. Sistema rejeita fração incompatível/negativo/abaixo da reserva. AJUSTE registra contado menos físico anterior, inclusive zero. Reserva/custo preservados.

**UC05:** informa nome/cliente e adiciona itens. Duplicatas e quantidades incompatíveis rejeitam. Salvar cria PLANEJADO sem reservar. Edição exige essa situação.

**UC08:** confirma cancelamento. RESERVADO libera itens e registra LIBERACAO; PLANEJADO muda estado e audita. Físico preservado. Estados terminais rejeitam.

**UC09:** consulta movimentos/auditoria do registro mais recente ao antigo. Histórico preserva SKU/nome, quantidade, unidade, referência e saldos posteriores. Sem edição/exclusão pela interface.

**UC10:** escolhe mínima/alvo; sistema sugere quantidade e estimativa pelo custo médio dos materiais em alerta. No mínimo, alerta permanece e mínima pode ser zero. Recebimento/cancelamento pode remover alerta. Sem pedido de compra automático.
