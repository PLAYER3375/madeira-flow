# Apresentação e demonstração

Use uma base nova: `python -m madeiraflow --demo --data dados-demo/apresentacao-01.sqlite3`. Escolha outro nome em ensaios seguintes. Sem --data, demo.bat reabre a demonstração anterior com as alterações já feitas.

## Roteiro de 12–15 minutos

1. Problema/atores/limites (2 min): uma chapa pode existir no depósito e já estar prometida. Mostrar físico, reservado e disponível.
2. Requisitos/modelo (2 min): reserva integral, baixa única e diagrama conceitual. Diferenciar análise de design.
3. Arquitetura/padrões (3 min): entidades Expert, serviços Controller, contratos e repositório. Mostrar Strategy no código e seletor; Observer nos alertas/auditoria.
4. Dois fluxos centrais e erro (5 min): executar os passos abaixo sem editar banco/código.
5. Testes/limites (1–3 min): executar suíte, explicar rollback e propostas de evolução.

## Fluxo 1 — Planejar e reservar

Na base nova, MDF branco: físico 10, reservado 4, disponível 6. Parafuso: 500/180/320.

1. Projetos → Novo projeto → Balcão Horizonte / Cliente exemplo.
2. Adicionar MDF-BR18 quantidade 1 e PAR-4X40 quantidade 10; salvar.
3. Mostrar PLANEJADO e saldos inalterados.
4. Selecionar Balcão Horizonte → Reservar → confirmar.
5. MDF: 10/5/5. Parafuso: 500/190/310. Mostrar RESERVA por item no histórico e auditoria.

## Fluxo 2 — Concluir produção

1. Selecionar Balcão Horizonte → Concluir produção → confirmar.
2. MDF: físico 9, reservado 4, disponível 5. Parafuso: 490/180/310.
3. Mostrar CONCLUIDO e movimentos CONSUMO.
4. Tentar concluir de novo: mensagem rejeita; MDF continua físico 9.

O disponível não muda na conclusão: o compromisso já havia reduzido esse número na reserva.

## Cenário inválido — integralidade

Criar Falta de cavilhas / Cliente exemplo com MDF-BR18=1 e CAV-8X30=99999. Tentar reservar. Erro deve identificar cavilha; MDF continua reservado 4. Mostrar projeto ainda PLANEJADO e nenhum movimento da tentativa. Explicar validação de todos os itens e snapshot descartável.

## Padrões e persistência

Cavilha inicia disponível 60/mínimo 80/alvo 400. Mínima sugere 20; alvo 340. Cola sugere 0,5 ou 8,5 kg. Cancelar Cozinha Aurora libera 90 cavilhas: físico 150, reservado 0, disponível 150; o alerta desaparece. Explicar Observer sem chamada concreta a alerta/auditoria dentro de ProjetoService.

Criar backup pelo botão; fechar e reabrir com o mesmo --data para mostrar permanência. Não reiniciar demo em outro arquivo para demonstrar persistência: isso criaria novos exemplos.

## Código para mostrar

dominio/modelos.py: Material, Projeto e EstadoEstoque.validar. aplicacao/servicos.py: ProjetoService.reservar/concluir. aplicacao/transacoes.py: limite da confirmação. dominio/reposicao.py: Strategy. aplicacao/eventos.py: Observer. infraestrutura/repositorios.py: UPDATE por revisão e rollback. composicao.py: injeção de dependências.

## Conferência antes de apresentar

Preencher autoria e regenerar documentos. Conferir escala da tela, scroll, seleção e diálogos reais. Executar testes com RUN_GUI_TESTS=1. Manter terminal disponível com `python -m madeiraflow --demo --verificar`. O guia de estudos externo contém explicações ampliadas e perguntas de discussão; não faz parte do ZIP do projeto.
