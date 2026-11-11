# Design

## Contexto

O PixelCode é uma aplicação interna em Reflex. A navegação e os dados
operacionais existentes usam `AuthState`, o helper autenticado `_request` e o
shell `_app_shell`; o tema compartilhado está em `frontend/assets/styles.css`.
O Financeiro reutiliza esse shell, e a consulta de dados usa um ledger
persistente novo porque agendamentos não representam pagamentos confirmados e
não há fonte existente para despesas.

## Goals / Non-Goals

**Goals:**
- Mostrar uma visão financeira com valores e períodos calculados dos
  lançamentos reais.
- Permitir registrar e editar entradas e saídas com persistência e trilha de
  auditoria no Xano.
- Permitir estornar lançamentos com motivo obrigatório, sem apagar seu
  histórico.
- Manter mocks isolados como fallback explícito de desenvolvimento sem API.
- Reutilizar o tema e o shell existentes e atender teclado, leitores de tela e
  telas estreitas.

**Non-Goals:**
- Excluir fisicamente movimentações, integrar banco, ou associar lançamentos
  automaticamente a agendamentos.
- Definir conciliação de saldo ou saldo inicial de caixa/banco.
- Criar uma biblioteca de gráficos ou uma nova biblioteca visual.

## Decisões

### Rota, acesso e layout

A rota `/financeiro` utilizará o mecanismo de sessão existente, sem introduzir
papéis ou um fluxo de autenticação paralelo. O item da sidebar será integrado a
`_app_sidebar`, marcado como ativo para a rota, e o cabeçalho usará
`_app_shell` para breadcrumb, ação "Sair" e área de conteúdo. O acesso aos dados
e a criação de movimentações são validados no backend para administradores e
profissionais.

### Camada de dados e fronteira dos mocks

Criar a tabela Xano `finance_transaction`, com tipo (`income` ou `expense`),
estado (`active` ou `cancelled`), valor positivo, título, detalhe opcional,
data/hora da movimentação, usuário que registrou e metadados de estorno.
`finance_transaction_revision` preserva os valores anteriores, ação, usuário,
data/hora e motivo associado a cada edição ou estorno.

Administradores e profissionais podem consultar, registrar, editar e estornar
movimentações compartilhadas da barbearia. `GET /finance/dashboard` retorna a
lista ordenada do ledger, incluindo itens estornados para preservar o histórico.
`POST /finance/transactions` cria, `PATCH /finance/transactions/{id}` edita e
`PATCH /finance/transactions/{id}/cancel` estorna um lançamento. Edição e
estorno exigem lançamento ativo e autorização no backend; estorno também exige
motivo. Nenhuma operação remove fisicamente registros.

O provider de mock ficará isolado e habilitado apenas em desenvolvimento por
configuração explícita, somente quando nenhuma URL de API estiver configurada.
Quando a API estiver configurada, seus dados sempre prevalecem sobre mock. Em
produção, não haverá fallback automático para mock se a configuração estiver
ausente ou se a API falhar. A falha será exibida como mensagem amigável.

As APIs serão consultadas por `GET /finance/dashboard`,
`POST /finance/transactions`, `PATCH /finance/transactions/{id}` e
`PATCH /finance/transactions/{id}/cancel`, usando
`XANO_FINANCE_API_URL` como base do grupo Finance (`/api:PCFin01`). Ela não
pode reutilizar `XANO_API_URL` quando essa variável aponta para o grupo
Authentication; a configuração do Finance deve ser explícita no ambiente.
O contrato de leitura retorna movimentações com tipo, valor, título, detalhe e
data/hora. O serviço deriva KPIs, fluxo de caixa, resumo mensal e saldo
acumulado desses mesmos registros. A mudança de período seleciona a série
correspondente dos dados já carregados; ao registrar um lançamento, a tela
consulta o ledger novamente. Respostas inválidas ou erros não são completados
com mocks.

Os dados de mock reproduzirão os exemplos da referência:

- recebimentos do dia (R$ 1.245,00), semana (R$ 5.860,00) e mês
  (R$ 18.720,00), com variações recalculadas de +12%, +8% e +15% a partir dos
  valores do período anterior (R$ 1.111,61, R$ 5.425,93 e R$ 16.278,26);
- série de entradas e saídas por mês, com conjuntos para cada período do
  seletor, usando R$ 18.720,00 de entradas e R$ 9.450,00 de saídas no mês de
  referência;
- resumo do mês com lucro líquido de R$ 9.270,00 e saldo acumulado ilustrativo de
  R$ 9.270,00;
- Pagamento de Serviço (Cliente: João Silva, +R$ 120,00, Hoje às 16:20),
  Pagamento de Fornecedor (Produtos, −R$ 450,00, Hoje às 14:32) e Serviço
  Realizado (Cliente: Lucas Souza, +R$ 100,00, Hoje às 13:10).
- Cabeçalho com "Lotus Barber / Financeiro", "FINANCEIRO", "Controle
  financeiro da sua barbearia" e "Acompanhe seus recebimentos, visualize o
  fluxo de caixa e mantenha suas finanças em dia.".

Os percentuais serão calculados usando valor atual e valor do período anterior,
e não gravados como rótulos fixos. Dados insuficientes para comparação não
devem gerar variação enganosa: a interface apresentará "Sem comparação".
Valores ausentes na API não serão preenchidos com números de demonstração.
Os dados de mock devem incluir uma data de referência para que rótulos
relativos como "Hoje" não dependam do relógio do ambiente de desenvolvimento.

### Cálculos e formatação

- Lucro líquido mensal = entradas do mês - saídas do mês.
- Saldo acumulado = soma das entradas menos as saídas registradas desde a
  criação do ledger; não representa saldo bancário e não inclui saldo inicial.
- KPIs de hoje, semana e mês somam entradas do período e comparam com o período
  imediatamente anterior equivalente.
- O fluxo de caixa oferece 6 meses móveis, 12 meses móveis e o ano calendário
  atual. Meses sem movimentação dentro de um intervalo preenchido são exibidos
  com zero; intervalos sem movimentação exibem estado vazio.
- Variação percentual = `(atual - anterior) / anterior * 100`; tratar período
  anterior zero/ausente como indisponível, sem divisão por zero.
- Formatar moeda em BRL com `Intl.NumberFormat("pt-BR", { style: "currency",
  currency: "BRL" })`, mantendo centavos nos valores apresentados.
- Apresentar datas e horários no padrão pt-BR; movimentações de hoje usam
  "Hoje, HH:mm". Datas são calculadas no fuso `America/Sao_Paulo`.

### Gráficos

Não há componente de gráfico existente nem dependência visual de gráficos no
projeto. Criar componentes locais acessíveis e sem biblioteca adicional:

- sparkline SVG compacto e decorativo para cada KPI;
- gráfico SVG de área/linhas com eixos, grade, pontos e tooltip;
- donut SVG com valores e rótulos também disponíveis fora do desenho.

O gráfico principal carregará seus dados quando a página estiver pronta e
atualizará série e subtítulo ao trocar o período. O tooltip deve ser acionável
por hover e teclado/foco, com descrição textual acessível equivalente. O SVG
deve ter nome acessível e não ser a única fonte dos valores. Quando o ambiente
não suportar uma visualização do gráfico, a tabela/lista textual dos dados
continuará disponível.

### Estados e responsividade

Cada bloco (KPIs, fluxo de caixa, resumo do mês e movimentações) terá estados de
carregamento, vazio e erro próprios. O erro será visível e não terá formato de
sucesso; o carregamento usará skeletons com rótulos acessíveis. Um bloco vazio
não deve impedir a exibição dos demais que tenham dados.

No desktop, os KPIs ocupam três colunas; abaixo deles, o gráfico ocupa a coluna
principal e o resumo/movimentações ficam na lateral. Em viewports estreitas, os
KPIs empilham e a coluna lateral passa para baixo do gráfico, sem rolagem
horizontal da página.

### Tokens e componentes

| Necessidade | Reutilizar | Criar somente se necessário |
|---|---|---|
| Fundo, superfícies, bordas, texto, fonte e raio | `--pc-bg`, `--pc-surface`, `--pc-surface-raised`, `--pc-surface-soft`, `--pc-border`, `--pc-text`, `--pc-muted`, `--pc-subtle`, `--pc-font`, `--pc-radius` | Nenhum token paralelo |
| Ação, foco e seleção | `--pc-blue`, `--pc-blue-hover`, `:focus-visible` e estados de navegação existentes | Nenhum token paralelo |
| Entrada positiva e saldo | Sem token semântico implementado atualmente; usar o tom de sucesso previsto na fundação visual (`#70C69B`) e registrar como `--pc-success` | `--pc-success`, centralizado no CSS compartilhado |
| Variação/valor negativo | `--pc-red` existente, respeitando seu papel semântico e validando contraste para texto | `--pc-danger` somente se necessário; usar o tom de erro previsto na fundação visual (`#F07178`) e centralizá-lo no CSS compartilhado |
| Séries de entrada/saída e texto associado | Não há tokens financeiros no tema atual | `--pc-finance-outflow` (`#8B5CF6`), `--pc-finance-inflow-text` (`#80A5FF`) e `--pc-finance-outflow-text` (`#B69AFF`), com uso semântico e validação de contraste |
| Navegação e cabeçalho | `_app_sidebar`, `_app_shell`, `_brand`, `pc-nav-link`, breadcrumb e botão `Sair` | Nenhum novo shell |
| Superfícies e ações | Padrões existentes `pc-card-*`, `pc-button` e estilos de formulário | Cartões KPI, controles de período e estados financeiros somente se não houver componente equivalente reutilizável |
| Ícones | `rx.icon`/Lucide já usados, como calendário, gráfico, seta e lista | Nenhuma biblioteca de ícones |
| Gráfico | Nenhum gráfico existente identificado | SVG de sparkline, área/linha e donut, restritos à capability financeiro |

Nenhum componente poderá introduzir fonte, sombra, gradiente ou espaçamento
desconectado da fundação visual. Novos tons semânticos serão centralizados como
tokens no CSS, e o contraste efetivamente renderizado será verificado antes da
conclusão.

## Riscos / Trade-offs

- **Ledger manual** → a consistência depende da equipe registrar corretamente
  todas as entradas e saídas; não há conciliação bancária.
- **Mock em aplicação autenticada** → habilitar apenas explicitamente em
  desenvolvimento sem API evita apresentar valores fictícios como resultados
  reais; uma API configurada sempre tem prioridade.
- **SVG local em vez de biblioteca** → reduz dependências e mantém consistência,
  mas exige implementar e testar navegação, descrição e tooltip acessíveis.
- **Saldo acumulado separado do lucro líquido** → evita confundir o resultado
  do mês com entradas menos saídas desde a criação do ledger.

## Plano de migração

Criar a tabela financeira sem backfill, pois os agendamentos existentes não
confirmam recebimentos e não há dados de despesas. O ledger começa vazio; as
movimentações são cadastradas pela equipe na própria seção Financeiro.
