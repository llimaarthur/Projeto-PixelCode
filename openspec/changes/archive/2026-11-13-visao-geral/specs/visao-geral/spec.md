# visao-geral Specification

## Purpose

Definir a tela autenticada e somente leitura de Visão geral, que agrega dados
financeiros, de agenda e de clientes já existentes no Lotus Barber.

## ADDED Requirements

### Requirement: Acesso e shell da Visão geral

O sistema SHALL disponibilizar a Visão geral na rota autenticada `/app`,
reutilizando o shell, o breadcrumb, o botão Sair, a sidebar e o tema escuro já
existentes. A sidebar SHALL marcar “Visão geral” como ativo e manter os itens
Serviços, Clientes, Agenda, Equipe e Financeiro conforme as permissões atuais.

#### Scenario: Usuário autenticado abre a Visão geral

- **WHEN** uma pessoa autenticada abre `/app`
- **THEN** o shell apresenta o breadcrumb “Lotus Barber / Visão geral”, marca
  “Visão geral” na sidebar e renderiza a tela sem o placeholder de boas-vindas

#### Scenario: Pessoa sem sessão tenta abrir a Visão geral

- **WHEN** uma pessoa sem sessão abre `/app`
- **THEN** o controle de acesso existente direciona a pessoa para a tela de
  login sem carregar dados de clientes, agenda ou financeiro

#### Scenario: Usar a ação Sair

- **WHEN** a pessoa seleciona “Sair”
- **THEN** a ação de logout existente encerra a sessão e a Visão geral não
  oferece uma operação alternativa de autenticação ou edição

### Requirement: Cabeçalho e seletor de período

A tela SHALL apresentar a saudação “Bem-vindo de volta, {nome}!”, o subtítulo
“Aqui está um resumo completo da sua barbearia.” e um seletor com “Últimos 7
dias”, “Últimos 30 dias”, “Últimos 90 dias” e “Ano atual”, com padrão “Últimos
30 dias”. Ao mudar o período, SHALL recalcular os quatro cartões e seus
sparklines, comparando com o intervalo anterior de mesma duração; para “Ano
atual”, SHALL comparar com o intervalo equivalente do ano anterior. Os rótulos
dos cartões SHALL acompanhar a agregação selecionada. O seletor do cabeçalho
SHALL ser independente do filtro do gráfico de fluxo de caixa.

#### Scenario: Exibir cabeçalho com a identidade autenticada

- **WHEN** os dados da sessão contêm o nome da pessoa autenticada
- **THEN** o cabeçalho exibe “Bem-vindo de volta, {nome}!”, o subtítulo
  especificado e as opções de período, com “Últimos 30 dias” selecionado

#### Scenario: Nome da sessão ausente

- **WHEN** o perfil autenticado não contém um nome utilizável
- **THEN** a saudação mantém texto válido sem exibir um valor nulo ou placeholder
  técnico

#### Scenario: Alterar período global

- **WHEN** a pessoa seleciona outro período disponível no seletor do cabeçalho
- **THEN** os quatro cartões, seus rótulos, valores, comparações e sparklines
  refletem o intervalo selecionado e o intervalo anterior correspondente, sem
  reutilizar valores obsoletos

#### Scenario: Comparar ano atual

- **WHEN** a pessoa seleciona “Ano atual”
- **THEN** os cartões comparam do início do ano até a data atual com o mesmo
  intervalo de calendário do ano anterior

### Requirement: Cartões de métricas

A tela SHALL apresentar quatro cartões conforme o período selecionado:
Entradas, Saídas e Lucro Líquido financeiros, além de Novos Clientes. Cada
cartão SHALL comparar o período selecionado com o anterior equivalente e
apresentar ícone, valor, sparkline e variação calculada a partir dos dados
atuais e anteriores. “Novos Clientes” SHALL contar registros cujo
`first_contact_at` esteja no intervalo, sem tratar esse campo como data técnica
de criação. Variação positiva SHALL usar seta para cima e verde; variação
negativa SHALL usar seta para baixo e vermelho. Valores financeiros SHALL usar
formato BRL; clientes SHALL usar contagem inteira. Comparação indisponível
SHALL ser indicada sem divisão por zero ou percentual inventado.

#### Scenario: Exibir os quatro cartões

- **WHEN** as consultas retornam dados válidos para os quatro indicadores
- **THEN** a tela apresenta entradas, saídas, lucro líquido e novos clientes no
  período, cada qual com valor, ícone, sparkline e comparação correspondente

#### Scenario: Variação positiva

- **WHEN** o valor atual de um indicador supera o período comparável
- **THEN** o cartão apresenta a variação positiva com seta para cima e cor
  verde, além do texto do período de comparação

#### Scenario: Variação negativa

- **WHEN** o valor atual de um indicador é inferior ao período comparável
- **THEN** o cartão apresenta a variação negativa com seta para baixo e cor
  vermelha, além do texto do período de comparação

#### Scenario: Período anterior inexistente ou igual a zero

- **WHEN** não há valor anterior válido para calcular a variação percentual
- **THEN** o cartão não divide por zero, não exibe uma variação fictícia e
  informa que a comparação não está disponível

#### Scenario: Não há registros para um indicador

- **WHEN** a consulta não contém dados para um indicador
- **THEN** seu cartão apresenta estado vazio ou comparação indisponível sem
  inventar valor, mantendo os outros cartões utilizáveis

#### Scenario: Novos clientes são contados pela data disponível

- **WHEN** a consulta retorna contatos com `first_contact_at` dentro e fora do
  intervalo selecionado
- **THEN** o cartão “Novos Clientes” conta somente os registros no intervalo e
  compara com os registros no intervalo anterior equivalente

### Requirement: Visão rápida do Financeiro

A tela SHALL apresentar um bloco com gráfico de rosca de entradas e saídas,
lucro líquido no centro, legenda e valores de cada série, Saldo Atual em
destaque verde e link “Ver mais” para Financeiro. Os valores SHALL vir do
dashboard financeiro existente e obedecer às regras de movimentações ativas
usadas no Saldo Atual; SHALL NOT ser um novo cálculo de domínio independente.

#### Scenario: Consultar resumo financeiro

- **WHEN** o dashboard financeiro retorna resumo válido
- **THEN** o bloco apresenta entradas, saídas e lucro líquido em BRL, a rosca
  correspondente e o Saldo Atual em destaque verde

#### Scenario: Não há movimentações financeiras

- **WHEN** o dashboard não contém entradas ou saídas para compor o resumo
- **THEN** o bloco apresenta estado vazio sem lucro ou saldo fictício

#### Scenario: Navegar para Financeiro

- **WHEN** a pessoa seleciona “Ver mais”
- **THEN** o sistema navega para `/financeiro` sem executar alteração financeira

### Requirement: Fluxo de Caixa

A tela SHALL apresentar gráfico de linha/área com as séries de Entradas e
Saídas, legenda, eixo Y formatado em BRL e seletor “6 meses”, “12 meses” e “Ano
atual”. O padrão SHALL ser “6 meses”. Alterar esse seletor SHALL atualizar
intervalo, subtítulo e séries usando os dados e cálculos financeiros
existentes.

#### Scenario: Abrir o fluxo de caixa

- **WHEN** o bloco é exibido pela primeira vez com dados válidos
- **THEN** o gráfico mostra Entradas e Saídas, legenda, eixo Y em BRL e o
  período “6 meses” selecionado

#### Scenario: Alterar o período do gráfico

- **WHEN** a pessoa seleciona “12 meses” ou “Ano atual”
- **THEN** a série, o subtítulo e os rótulos do gráfico passam a refletir o
  intervalo selecionado sem alterar o seletor global do cabeçalho

#### Scenario: Fluxo sem dados

- **WHEN** não existem movimentações no intervalo selecionado
- **THEN** o gráfico apresenta estado vazio e não desenha séries fictícias

#### Scenario: Falha ao consultar o fluxo

- **WHEN** os dados necessários ao gráfico não podem ser carregados ou
  preparados
- **THEN** o bloco apresenta erro explícito e os blocos de outras fontes
  continuam disponíveis

### Requirement: Próximos agendamentos

A tela SHALL apresentar uma lista somente leitura de próximos atendimentos,
com horário, cliente, serviço e data; atendimentos de hoje SHALL ser destacados
como “Hoje”. Cada pessoa SHALL ter foto quando a fonte existente fornecer uma
imagem e, caso contrário, um avatar com iniciais. O link “Ver todos” SHALL
navegar para Agenda.

#### Scenario: Exibir atendimentos futuros

- **WHEN** a consulta existente da Agenda retorna atendimentos futuros
- **THEN** a lista exibe os próximos atendimentos em ordem cronológica com
  horário, nome do cliente, serviço e data formatados

#### Scenario: Destacar atendimento de hoje

- **WHEN** um atendimento está marcado para a data local atual da barbearia
- **THEN** sua data é identificada visualmente como “Hoje”

#### Scenario: Atendimento sem foto de cliente

- **WHEN** o registro não possui uma foto de cliente fornecida pela fonte
- **THEN** a lista mostra avatar com iniciais sem tentar usar foto de usuário ou
  profissional

#### Scenario: Agenda sem próximos atendimentos

- **WHEN** não existem atendimentos futuros no intervalo consultado
- **THEN** o bloco apresenta estado vazio e mantém o link para Agenda

#### Scenario: Navegar para Agenda

- **WHEN** a pessoa seleciona “Ver todos”
- **THEN** o sistema navega para a rota de Agenda sem criar, editar, confirmar ou
  cancelar agendamentos

### Requirement: Resumo de Clientes

A tela SHALL apresentar total de clientes cadastrados, variação em relação ao
mês anterior, percentual de clientes ativos sobre o total e barra de progresso,
além do link “Ver todos” para Clientes. Contagens e percentuais SHALL usar os
totais correspondentes da consulta de clientes, nunca somente os registros da
página visível.

#### Scenario: Exibir resumo de clientes

- **WHEN** as consultas de clientes fornecem totais válidos
- **THEN** o bloco apresenta total cadastrado, variação mensal e percentual de
  ativos, com barra de progresso coerente com esse percentual

#### Scenario: Nenhum cliente cadastrado

- **WHEN** o total de clientes é zero
- **THEN** o bloco mostra total zero e barra sem preenchimento, sem divisão por
  zero ou variação fabricada

#### Scenario: Contagens paginadas

- **WHEN** existem mais clientes do que cabem na página consultada
- **THEN** o total e o percentual usam as contagens totais retornadas pelos
  filtros correspondentes, não apenas os itens carregados na página atual

#### Scenario: Falha ou indisponibilidade da variação mensal

- **WHEN** não é possível determinar o total histórico no mês anterior com os
  dados existentes
- **THEN** o bloco não apresenta percentual de crescimento inventado, mantém
  total/ativos válidos quando disponíveis e indica comparação indisponível

#### Scenario: Navegar para Clientes

- **WHEN** a pessoa seleciona “Ver todos”
- **THEN** o sistema navega para a área de Clientes sem criar ou alterar contatos

### Requirement: Movimentações recentes

A tela SHALL apresentar movimentações existentes em ordem da mais recente para
a mais antiga, com descrição, cliente/detalhe disponível, valor, sinal, cor e
horário. Entradas SHALL ser identificadas com sinal positivo e verde; saídas
SHALL ser identificadas com sinal negativo e vermelho. O link “Ver todas”
SHALL navegar para Financeiro. A lista SHALL NOT apresentar ações de edição ou
estorno.

#### Scenario: Exibir entradas e saídas

- **WHEN** existem movimentações financeiras recentes
- **THEN** cada item apresenta descrição, cliente ou detalhe disponível,
  horário e valor em BRL, com semântica de sinal e cor apropriada

#### Scenario: Excluir estornadas dos valores operacionais

- **WHEN** o ledger contém movimentações estornadas
- **THEN** os indicadores e valores da Visão geral seguem as regras do Financeiro
  e não contam lançamentos estornados como movimentação ativa

#### Scenario: Nenhuma movimentação recente

- **WHEN** a consulta não retorna movimentações
- **THEN** o bloco apresenta estado vazio sem registros de demonstração em
  produção

#### Scenario: Navegar para Financeiro

- **WHEN** a pessoa seleciona “Ver todas”
- **THEN** o sistema navega para `/financeiro` sem executar edição ou estorno

### Requirement: Estados independentes, responsividade e leitura

Cada bloco SHALL apresentar estado de carregamento, vazio ou erro próprio e uma
falha SHALL NOT derrubar a página nem ocultar blocos cujas fontes estão
disponíveis. O painel SHALL manter o tema escuro, adaptar o grid de quatro e
três colunas conforme o espaço disponível e empilhar os blocos em telas
estreitas. Gráficos, tendência e progresso SHALL ter rótulos acessíveis e não
depender exclusivamente de cor.

#### Scenario: Carregamento inicial

- **WHEN** uma origem ainda está carregando
- **THEN** cada bloco dependente apresenta seu próprio indicador de
  carregamento e outros blocos podem exibir conteúdo já disponível

#### Scenario: Falha isolada de Clientes

- **WHEN** a consulta de clientes falha, mas Agenda e Financeiro estão
  disponíveis
- **THEN** somente o bloco de Clientes apresenta erro e os outros blocos
  continuam utilizáveis

#### Scenario: Falha isolada de Agenda

- **WHEN** a consulta de Agenda falha, mas Clientes e Financeiro estão
  disponíveis
- **THEN** somente o bloco de Agendamentos apresenta erro e os outros blocos
  continuam utilizáveis

#### Scenario: Falha financeira

- **WHEN** a fonte financeira falha
- **THEN** os blocos financeiros apresentam estado de erro, sem valores
  fictícios, enquanto Agenda e Clientes continuam renderizados quando suas
  fontes estão disponíveis

#### Scenario: Visualizar em viewport estreita

- **WHEN** a pessoa acessa a tela em viewport menor
- **THEN** cartões e blocos se reorganizam sem sobreposição ou rolagem
  horizontal para ler os conteúdos essenciais

#### Scenario: Navegação e interpretação acessíveis

- **WHEN** a pessoa navega por teclado ou usa tecnologia assistiva
- **THEN** seletores, links, gráficos e tendências têm nomes/descrições
  acessíveis e aumento ou redução não é comunicado apenas por cor

### Requirement: Somente leitura e exclusão de escopo

A Visão geral SHALL consumir e agregar dados existentes sem chamadas de
escrita, formulário, edição, estorno, criação de registros ou mudança de status.
O bloco “Serviços Mais Procurados” SHALL NOT ser implementado nem exibido.

#### Scenario: Consultar sem alterar dados

- **WHEN** a pessoa abre, filtra ou navega pela Visão geral
- **THEN** são realizadas somente consultas de leitura e a tela não altera
  clientes, agendamentos ou movimentações

#### Scenario: Conteúdo explicitamente fora do escopo

- **WHEN** a Visão geral é renderizada
- **THEN** não existe card, lista ou solicitação de dados para “Serviços Mais
  Procurados”
