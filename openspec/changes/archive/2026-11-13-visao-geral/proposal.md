# Change: Visão geral

## Why

A rota `/app` autenticada ainda apresenta somente uma mensagem de boas-vindas,
embora Financeiro, Agenda e Clientes já concentrem os dados e fluxos necessários
para um resumo operacional da barbearia. A pessoa administradora precisa abrir
essas áreas separadamente para entender o estado do negócio.

Esta change transforma a rota existente em uma visão geral somente leitura,
reaproveitando os serviços, consultas, cálculos, componentes visuais e o shell já
implementados. A nova tela não cria uma segunda fonte de verdade nem altera as
rotinas das áreas existentes.

## What Changes

- Substituir o conteúdo de boas-vindas de `/app` por um painel responsivo com
  cabeçalho, seletor de período (7, 30 e 90 dias ou ano atual) e quatro
  métricas dinâmicas: Entradas, Saídas, Lucro Líquido e Novos Clientes,
  comparadas ao período anterior equivalente.
- Apresentar um resumo financeiro com rosca, lucro líquido, entradas, saídas,
  Saldo Atual e navegação para Financeiro.
- Apresentar o fluxo de caixa com entradas e saídas e os períodos de 6 meses,
  12 meses e ano atual.
- Apresentar os próximos agendamentos, o resumo de clientes ativos e as
  movimentações recentes, com links para as respectivas áreas.
- Reaproveitar consultas, cálculos e apresentação existentes; extrair
  componentes visuais compartilhados quando necessário, preservando o
  comportamento de Financeiro, Agenda e Clientes.
- Manter a navegação autenticada, o tema escuro, o breadcrumb, o botão Sair e a
  sidebar existentes.
- **Fora do escopo:** o card **“Serviços Mais Procurados”** mostrado na imagem
  de referência não será implementado nem exibido.
- Não adicionar operações de escrita, novos endpoints ou alterações funcionais
  às telas existentes.

## Capabilities

### New Capabilities

- `visao-geral`: painel autenticado, somente leitura, que agrega informações
  financeiras, de agenda e de clientes existentes.

### Modified Capabilities

- Nenhuma. As capacidades de Financeiro, Agenda e Clientes permanecem
  inalteradas; a nova tela apenas as consome.

## Impact

- `frontend/frontend/auth_state.py`: substituir a tela placeholder de `/app`,
  reutilizar o shell e carregar dados existentes de Financeiro, Agenda e
  Clientes.
- `frontend/frontend/finance_page.py` e
  `frontend/frontend/finance_service.py`: extrair ou reutilizar apresentação e
  cálculos de métricas, sparkline, rosca, fluxo de caixa, estados por bloco e
  movimentações, sem remover os controles de escrita da tela Financeiro.
- `frontend/frontend/dashboard_components.py` e
  `frontend/frontend/overview_service.py`: componentes de apresentação
  compartilhados e agregação por período sobre os dados financeiros existentes.
- Consultas já existentes do Xano: `finance/dashboard`, `appointments` e
  `contacts`. Não são propostos endpoints novos nem mudanças no backend.
- `frontend/assets/styles.css`: acrescentar o grid e os estilos próprios do
  painel, aproveitando tokens, shell, tema escuro e breakpoints atuais.
- Clientes não possuem foto no contrato atualmente encontrado; a lista usará
  avatar com iniciais como fallback até que uma origem de foto exista.
- Artefatos OpenSpec: `design.md`, `specs/visao-geral/spec.md` e `tasks.md`.
