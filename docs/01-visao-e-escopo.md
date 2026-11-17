# Visão do problema e escopo

Uma marcenaria compartilha chapas, parafusos, cavilhas, fitas e cola entre encomendas. Conhecer apenas o saldo no depósito permite prometer o mesmo material para dois clientes. Isso interrompe a produção e leva a compras sem necessidade conhecida.

O MadeiraFlow diferencia físico, reservado e disponível, com lista de materiais para cada projeto. Separação e consumo são operações integrais e rastreáveis.

## Atores

| Ator | Objetivos |
|---|---|
| Estoquista | Manter materiais, receber entregas e conferir inventário |
| Responsável pela produção | Planejar encomendas, reservar, concluir ou cancelar |
| Gestor | Acompanhar disponibilidade, histórico e reposição |

São papéis operacionais, sem contas e permissões nesta versão local.

## Escopo

Inclui chapas/insumos, custo médio, inventário justificado, projetos com vários materiais, reserva/baixa/cancelamento integrais, histórico, auditoria, alertas, duas políticas de reposição, persistência e demonstração.

Exclui plano de corte, retalhos, chapas fracionadas, orçamento de móveis, pedidos ao fornecedor, financeiro, fiscal, devoluções, múltiplos depósitos, autenticação e arquivo compartilhado por rede. Produção informa quantas chapas inteiras serão necessárias.

## Glossário

| Termo | Significado |
|---|---|
| SKU | Identificação única do material, normalizada em maiúsculas |
| Chapa | Painel inteiro com dimensões em mm e acabamento |
| Insumo | Material auxiliar em UN, M, L ou KG |
| Físico | Quantidade existente no depósito |
| Reservado | Parcela comprometida com projetos reservados |
| Disponível | Físico menos reservado |
| Mínimo / alvo | Limite de alerta / quantidade desejada após reposição |
| Projeto | Encomenda com nome, cliente, itens e situação de produção |
| Custo médio | Média ponderada dos recebimentos |
| Baixa | Consumo do material previamente reservado |

## Fontes e processo

O enunciado é `APSOO_Trabalho_Pratico_Projeto_Final.pptx.pdf`, p. 3–5, 8–16 e 18–29. Os demais sete PDFs são contexto conceitual: exercícios de outros domínios não viram requisitos do MadeiraFlow. Tecnologia livre (p. 4) permite a reconstrução em Python. A versão Java permanece separada; todos os artefatos desta pasta descrevem Python.
