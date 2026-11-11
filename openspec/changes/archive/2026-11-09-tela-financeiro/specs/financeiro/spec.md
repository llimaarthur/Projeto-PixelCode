# Spec Delta: Financeiro

## Propósito

Definir o painel financeiro autenticado da barbearia, incluindo registro e
consulta de movimentações, indicadores, fluxo de caixa e resumo mensal.

## ADDED Requirements

### Requirement: Acesso autenticado e navegação Financeiro
O sistema SHALL disponibilizar a rota `/financeiro` somente para usuários com
sessão interna válida. A sidebar SHALL apresentar "Financeiro" com estado ativo
nessa rota, e o shell SHALL exibir o breadcrumb correspondente e a ação "Sair".

#### Scenario: Usuário autenticado abre Financeiro
- **WHEN** um usuário interno autenticado acessa `/financeiro`
- **THEN** o sistema apresenta a tela no shell compartilhado e destaca
  "Financeiro" na navegação

#### Scenario: Usuário sem sessão abre Financeiro
- **WHEN** um visitante sem sessão acessa `/financeiro`
- **THEN** o sistema aplica o redirecionamento de autenticação já usado pelas
  demais páginas internas

### Requirement: Cabeçalho da tela Financeiro
A tela SHALL apresentar o breadcrumb "Lotus Barber / Financeiro", eyebrow
"FINANCEIRO", título "Controle financeiro da sua barbearia" e o subtítulo
"Acompanhe seus recebimentos, visualize o fluxo de caixa e mantenha suas
finanças em dia."

#### Scenario: Abrir a tela Financeiro
- **WHEN** a rota autenticada é carregada
- **THEN** o cabeçalho apresenta breadcrumb, eyebrow, título e subtítulo na
  hierarquia definida

### Requirement: Origem dos dados financeiros
A tela SHALL consumir movimentações persistidas no ledger Xano por uma camada
de serviço independente da interface. Administradores e profissionais
autenticados SHALL consultar e registrar movimentações. Mocks SHALL ser usados
somente em desenvolvimento quando explicitamente habilitados e sem URL de API
configurada. Uma API configurada SHALL ter prioridade sobre o mock. Em produção,
a ausência ou falha da API SHALL ser apresentada com estado amigável e SHALL NOT
ser substituída por dados fictícios.

#### Scenario: Provider de desenvolvimento habilitado sem API
- **WHEN** o ambiente é de desenvolvimento, não há URL de API configurada e o
  provider mock está explicitamente habilitado
- **THEN** a interface recebe os dados de demonstração pelo contrato financeiro

#### Scenario: API configurada e mock habilitado
- **WHEN** existe URL de API configurada mesmo que o mock esteja habilitado
- **THEN** a interface consulta o ledger real e não apresenta dados de mock

#### Scenario: API financeira falha em produção
- **WHEN** a consulta financeira em produção falha ou não está configurada
- **THEN** a interface exibe mensagem amigável de erro e não apresenta valores
  fictícios ou mensagens técnicas do provedor

#### Scenario: Consulta financeira autorizada
- **WHEN** o provider de API solicita dados com a sessão interna válida
- **THEN** a requisição reutiliza autenticação e tratamento de erros existentes
  e respeita a autorização aplicada pelo backend

### Requirement: Registro de movimentações
O sistema SHALL permitir que administradores e profissionais autenticados
registrem entradas e saídas com valor positivo, descrição, detalhe opcional e
data/hora. O backend SHALL validar os dados e persistir o usuário responsável.
Movimentações SHALL ser compartilhadas entre os usuários autorizados da
barbearia e não poderão ter data futura. Lançamentos ativos SHALL poder ser
editados; cada edição SHALL preservar os valores anteriores, o usuário
responsável e o horário da alteração em um histórico de auditoria. Lançamentos
SHALL poder ser estornados com motivo obrigatório, sem exclusão física; o
estorno SHALL preservar o lançamento e removê-lo de todos os totais financeiros.
Lançamentos estornados SHALL ser imutáveis.

#### Scenario: Registrar entrada ou saída
- **WHEN** um usuário autorizado envia uma movimentação válida
- **THEN** o backend a persiste e o painel atualiza os indicadores e a lista

#### Scenario: Rejeitar movimentação inválida
- **WHEN** o valor não é positivo, a descrição é inválida ou a data está no
  futuro
- **THEN** o backend rejeita o lançamento e a interface mostra orientação
  amigável sem mensagem técnica

#### Scenario: Registrar movimentação sem API
- **WHEN** a API financeira não está configurada
- **THEN** o painel pode apresentar mock explicitamente habilitado em
  desenvolvimento, mas não simula sucesso de gravação

#### Scenario: Editar movimentação ativa
- **WHEN** um usuário autorizado salva alterações válidas em um lançamento ativo
- **THEN** o backend atualiza o lançamento, registra os valores anteriores,
  usuário e horário no histórico, e o painel recalcula os indicadores

#### Scenario: Estornar movimentação
- **WHEN** um usuário autorizado confirma o estorno com um motivo válido
- **THEN** o backend marca o lançamento como estornado, registra o motivo e o
  usuário no histórico, mantém o lançamento visível e remove seu valor dos
  indicadores e do saldo acumulado

#### Scenario: Preservar lançamentos estornados
- **WHEN** um usuário consulta ou tenta editar um lançamento estornado
- **THEN** o lançamento permanece identificado como estornado no histórico e o
  backend rejeita novas edições ou estornos

### Requirement: Indicadores de recebimento
A tela SHALL apresentar "Recebido Hoje", "Recebido na Semana" e "Recebido no
Mês", com valor em BRL, comparação com o período anterior, indicador visual e
sparkline. A variação SHALL ser calculada dos valores atual e anterior, não
armazenada como percentual fixo.

#### Scenario: Comparar indicador com período anterior
- **WHEN** o provider retorna valor atual e anterior válidos para um indicador
- **THEN** a interface calcula e apresenta a variação percentual, indicando
  aumento em verde e redução em vermelho

#### Scenario: Não há período de comparação
- **WHEN** o período anterior está ausente ou tem valor zero
- **THEN** a interface não divide por zero nem inventa uma porcentagem e informa
  que não há comparação disponível

#### Scenario: Exibir indicadores da referência em mock
- **WHEN** os dados de demonstração são habilitados em desenvolvimento
- **THEN** os cards mostram os valores de referência de hoje, semana e mês, com
  recebimentos de R$ 1.245,00, R$ 5.860,00 e R$ 18.720,00 e comparativos
  anteriores que permitem recalcular as variações de +12%, +8% e +15%

### Requirement: Fluxo de caixa por período
A tela SHALL exibir um gráfico de entradas e saídas com os períodos "6 meses",
"12 meses" e "Ano atual". O período padrão SHALL ser "6 meses"; mudar a seleção
SHALL atualizar o intervalo, o subtítulo e a série apresentados.
O gráfico SHALL identificar as séries na legenda, usar eixo Y de R$ 0 a
R$ 25.000,00 e mostrar os meses no eixo X. O ponto ativo SHALL ter destaque
visual e tooltip com mês, entradas e saídas.

#### Scenario: Selecionar período
- **WHEN** o usuário seleciona um dos períodos disponíveis
- **THEN** o gráfico atualiza dados, rótulos de eixo e subtítulo para o período
  escolhido

#### Scenario: Consultar ponto do gráfico
- **WHEN** o usuário aponta, focaliza ou navega até um ponto da série
- **THEN** a interface informa mês, entradas e saídas em BRL por tooltip
  acessível, como "Outubro — Entradas: R$ 18.720,00 / Saídas: R$ 9.450,00"

#### Scenario: Gráfico sem dados
- **WHEN** não há movimentações registradas para o período selecionado
- **THEN** o gráfico exibe estado vazio e não desenha séries de demonstração

#### Scenario: Fluxo derivado do ledger
- **WHEN** existem entradas e saídas registradas no ledger
- **THEN** o gráfico soma os valores por mês e separa as séries por tipo de
  movimentação no intervalo escolhido

### Requirement: Resumo do mês e lucro líquido
A tela SHALL apresentar entradas, saídas, donut, lucro líquido mensal e saldo
acumulado. O lucro líquido SHALL ser calculado como entradas menos saídas do
mês. O saldo acumulado SHALL ser calculado como entradas menos saídas
registradas desde a criação do ledger, sem saldo inicial, e SHALL ser
identificado como valor acumulado (não saldo bancário).

#### Scenario: Calcular lucro líquido mensal
- **WHEN** o provider retorna entradas e saídas do mês
- **THEN** o centro do donut e o resumo mostram lucro líquido igual a entradas
  menos saídas, formatado em BRL

#### Scenario: Exibir resumo de demonstração
- **WHEN** o provider mock está explicitamente habilitado em desenvolvimento
- **THEN** o resumo mostra entradas de R$ 18.720,00, saídas de R$ 9.450,00 e
  lucro líquido de R$ 9.270,00

#### Scenario: Saldo acumulado independente do resumo mensal
- **WHEN** o acumulado desde a criação do ledger difere do lucro líquido mensal
- **THEN** a interface apresenta o lucro do mês e o saldo acumulado com seus
  escopos distintos

#### Scenario: Resumo sem dados
- **WHEN** o provider não retorna entradas ou saídas suficientes para o resumo
- **THEN** o bloco apresenta estado vazio ou erro e não calcula lucro fictício

### Requirement: Movimentações recentes
A tela SHALL apresentar uma lista de movimentações de entrada e saída com tipo,
descrição, detalhe, valor em BRL e data/hora. Entradas e saídas SHALL ter
indicações semânticas distintas além da cor.

#### Scenario: Exibir movimentações registradas
- **WHEN** o provider retorna movimentações recentes
- **THEN** cada item mostra natureza, título, detalhe, valor e horário relativo
  em pt-BR, incluindo "Hoje, HH:mm" para itens do dia

#### Scenario: Filtrar movimentações estornadas
- **WHEN** a lista contém movimentações estornadas
- **THEN** elas ficam ocultas por padrão e podem ser exibidas ou ocultadas pelo
  controle da lista, sem alterar os totais financeiros

#### Scenario: Exibir lista mock de referência
- **WHEN** o provider mock está explicitamente habilitado em desenvolvimento
- **THEN** a lista inclui Pagamento de Serviço (Cliente: João Silva,
  +R$ 120,00, Hoje às 16:20), Pagamento de Fornecedor (Produtos, −R$ 450,00,
  Hoje às 14:32) e Serviço Realizado (Cliente: Lucas Souza, +R$ 100,00,
  Hoje às 13:10)

#### Scenario: Lista sem movimentações
- **WHEN** não há movimentações recentes
- **THEN** a lista apresenta estado vazio sem exibir itens de exemplo

#### Scenario: Falha ao consultar movimentações
- **WHEN** a consulta de movimentações falha
- **THEN** a lista apresenta erro explícito e mantém os demais blocos
  independentes

#### Scenario: Atualizar ao entrar na seção
- **WHEN** um usuário navega para Financeiro sem recarregar a aplicação
- **THEN** a seção consulta o endpoint de dashboard, atualiza os dados e mantém
  o shell e o item ativo da sidebar

### Requirement: Estados de carregamento e falha por bloco
KPIs, fluxo de caixa, resumo mensal e movimentações SHALL apresentar estados
próprios de carregamento, vazio e erro, sem bloquear a página inteira nem
mostrar falha como sucesso.

#### Scenario: Carregamento inicial
- **WHEN** um bloco está aguardando os dados do provider
- **THEN** o bloco apresenta skeleton acessível e os demais podem renderizar seus
  próprios estados

#### Scenario: Falha isolada
- **WHEN** a consulta de um bloco falha e outras consultas concluem
- **THEN** o bloco com falha mostra erro e os blocos bem-sucedidos permanecem
  disponíveis

### Requirement: Formatação, responsividade e acessibilidade
A tela SHALL formatar valores em BRL usando `Intl.NumberFormat` com localidade
`pt-BR`, apresentar datas e horários em pt-BR, funcionar por teclado e manter
conteúdo utilizável em telas estreitas. Gráficos SHALL ter nomes e descrições
acessíveis e SHALL NOT depender apenas de cor ou hover.

#### Scenario: Formatar valor monetário e horário
- **WHEN** a tela exibe um valor ou movimentação
- **THEN** o valor usa BRL e separadores `pt-BR`, e itens do dia usam o padrão
  "Hoje, HH:mm" no fuso `America/Sao_Paulo`

#### Scenario: Navegar pelo seletor e gráfico
- **WHEN** o usuário opera o seletor de período e os pontos do gráfico por teclado
- **THEN** há ordem de foco lógica, estado selecionado anunciado e tooltip ou
  descrição dos dados sem exigir hover

#### Scenario: Visualizar em viewport mobile
- **WHEN** a tela é exibida em viewport estreito
- **THEN** os KPIs empilham e a coluna lateral aparece abaixo do gráfico, sem
  rolagem horizontal da página

### Requirement: Operações disponíveis no painel
A tela SHALL permitir consultar, registrar, editar e estornar entradas e saídas.
SHALL NOT permitir exclusão física de lançamentos, exportar dados ou realizar
conciliação bancária nesta capability.

#### Scenario: Usuário consulta e registra dados financeiros
- **WHEN** o usuário autenticado interage com os cards, filtros, lista ou
  ações de movimentação
- **THEN** a interface consulta, registra, edita ou estorna lançamentos e atualiza os dados
  persistidos

#### Scenario: Usuário não encontra exclusão física
- **WHEN** o usuário abre a tela Financeiro
- **THEN** lançamentos ativos podem ser editados ou estornados, sem controles
  para exclusão física
