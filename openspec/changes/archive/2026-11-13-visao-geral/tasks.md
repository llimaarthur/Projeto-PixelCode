# Tasks: Visão geral

## 1. Levantamento e contratos existentes

- [x] Confirmar campos, status e ordenação disponíveis nas respostas de
  `finance/dashboard`, `appointments` e `contacts`.
- [x] Mapear os períodos, cálculos, comparações, formatação e estados já
  cobertos por `finance_service.py` e pelos testes do Financeiro.
- [x] Confirmar contrato e custo de paginação para total de clientes, clientes
  ativos e comparação histórica mensal; não usar apenas a página atual.
- [x] Confirmar que contatos não fornecem foto e definir avatar com iniciais
  como fallback.
- [x] Registrar os casos de teste para preservar o comportamento existente de
  Financeiro, Agenda, Clientes, sessão e sidebar.

## 2. Componentes compartilhados

- [x] Extrair/generalizar o cartão de métrica e sparkline para valor em BRL ou
  contagem, ícone, variação e estado acessível, preservando os KPIs atuais do
  Financeiro.
- [x] Extrair/reutilizar apresentação do donut e do gráfico de linha/área sem
  duplicar cálculos nem acoplar o filtro do cabeçalho ao filtro do fluxo.
- [x] Generalizar os estados visuais de skeleton, vazio e erro por bloco.
- [x] Criar apresentação somente leitura de movimentação, sem expor ações de
  edição ou estorno.
- [x] Executar testes direcionados e confirmar que os componentes extraídos não
  alteram a tela Financeiro existente.

## 3. Rota, shell e período global

- [x] Substituir o placeholder de `app_page()` em `/app`, mantendo a proteção de
  sessão e usando `_app_shell()` e `_app_sidebar()` existentes.
- [x] Implementar cabeçalho, saudação com nome autenticado, subtítulo e seletor
  “Últimos 7 dias”, “Últimos 30 dias”, “Últimos 90 dias” e “Ano atual”, com
  padrão “Últimos 30 dias”.
- [x] Implementar o seletor global sem reutilizar o estado do período próprio do
  gráfico de fluxo; recalcular métricas dependentes e comparações equivalentes.
- [x] Preservar o breadcrumb, o botão Sair, o perfil e as demais rotas e itens da
  sidebar.

## 4. Métricas e blocos do painel

- [x] Compor os quatro cartões dinâmicos: Entradas, Saídas, Lucro Líquido e
  Novos Clientes no período selecionado, com sparkline e comparação
  correspondente.
- [x] Implementar a Visão Rápida do Financeiro com rosca, lucro líquido,
  entradas, saídas, Saldo Atual e link para Financeiro.
- [x] Implementar o Fluxo de Caixa com Entradas e Saídas, eixo BRL, legenda e
  seletor 6 meses/12 meses/Ano atual.
- [x] Implementar lista somente leitura de próximos agendamentos com data,
  destaque de “Hoje”, cliente, serviço, horário e fallback de iniciais.
- [x] Implementar resumo de Clientes com total, variação mensal, percentual de
  ativos, barra de progresso e link para Clientes.
- [x] Implementar Movimentações Recentes com ordenação, sinal/cor, detalhe e
  link para Financeiro, sem ações de escrita.
- [x] Não implementar nem solicitar dados para “Serviços Mais Procurados”.

## 5. Integração e isolamento de dados

- [x] Reutilizar o dashboard financeiro e seus cálculos existentes para métricas,
  resumo, fluxo e movimentações, sem duplicar regra financeira.
- [x] Integrar consultas existentes de Agenda e Clientes, respeitando paginação,
  autorização e fuso/formatos usados nas telas atuais.
- [x] Isolar loading, vazio e erro por bloco/origem para uma falha não impedir a
  renderização das demais origens.
- [x] Não adicionar chamadas HTTP de escrita, endpoints, entidades ou mudanças
  de comportamento nas telas existentes.

## 6. Estilo, responsividade e acessibilidade

- [x] Implementar grid e estilos próprios aproveitando tema escuro, tokens e
  breakpoints existentes.
- [x] Ajustar o layout dos quatro cartões de métrica para manter texto e
  sparkline separados no grid de quatro colunas.
- [x] Validar grid de quatro e três colunas em desktop e empilhamento em
  viewports menores sem rolagem horizontal.
- [x] Adicionar rótulos acessíveis a gráficos, tendências, progresso, seletores,
  links e estados.
- [x] Validar sinais e texto além da cor para variações e entradas/saídas.

## 7. Testes e validação

- [x] Adicionar testes para variações positivas, negativas, zero/indisponível,
  período global e comparações sem divisão por zero.
- [x] Adicionar regressão para agregar movimentações no formato normalizado
  (`input_datetime`) retornado pelo dashboard financeiro.
- [x] Adicionar testes para contagens totais/ativos com paginação, lista de
  agendamentos vazia/futura e movimentações somente leitura.
- [x] Adicionar testes de falha isolada e estados loading/vazio/erro por bloco.
- [x] Executar testes direcionados do frontend e compilação/validação da rota
  Reflex.
- [x] Revisar Financeiro, Agenda, Clientes, sidebar e fluxo de logout para
  confirmar que continuam inalterados.
- [x] Validar o comportamento responsivo e os links “Ver mais”, “Ver todos” e
  “Ver todas”.
