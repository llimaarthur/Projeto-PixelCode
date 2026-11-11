# Proposta: Tela Financeiro do Lotus Barber

## Por quê

O painel já organiza clientes, serviços, agenda e equipe, e o domínio registra
pagamentos associados a agendamentos, mas ainda não oferece uma visão consolidada
de entradas, saídas e saldo. A equipe precisa consultar os principais indicadores
e movimentações sem recorrer a controles externos.

A tela seguirá a referência visual enviada, aplicada à fundação visual existente
do projeto. A referência é ilustrativa: seus valores não serão tratados como
dados reais.

## O que muda

- Adicionar a rota autenticada `/financeiro` e o item "Financeiro" na navegação
  lateral existente, com breadcrumb e estado ativo.
- Apresentar três indicadores de recebimento (hoje, semana e mês), com variação
  calculada em relação ao período anterior.
- Apresentar o fluxo de caixa em gráfico para 6 meses, 12 meses ou ano atual,
  com entradas, saídas, valores em BRL, tooltip e seleção acessível dos períodos.
- Apresentar resumo mensal com entradas, saídas, lucro líquido e saldo acumulado.
- Apresentar movimentações recentes com tipo, descrição, valor e data/hora.
- Permitir que administradores e profissionais registrem entradas e saídas no
  ledger persistente da barbearia.
- Permitir edição de lançamentos ativos com trilha de auditoria dos valores
  anteriores, autor e horário da alteração.
- Permitir estorno com motivo obrigatório, preservando o registro e excluindo
  seus valores dos cálculos financeiros.
- Criar endpoints Xano autenticados para registrar e consultar o ledger e
  calcular os indicadores com base nas movimentações cadastradas.
- Manter mocks apenas como fallback explícito de desenvolvimento quando a API
  financeira não estiver configurada.
- Cobrir carregamento, vazio e erro nos blocos da página, sem substituir falhas
  de API por valores de demonstração.

## Conteúdo da referência

- Cabeçalho: breadcrumb "Lotus Barber / Financeiro", eyebrow "FINANCEIRO",
  título "Controle financeiro da sua barbearia" e subtítulo "Acompanhe seus
  recebimentos, visualize o fluxo de caixa e mantenha suas finanças em dia."
- KPIs: hoje R$ 1.245,00 (+12%); semana R$ 5.860,00 (+8%); mês R$ 18.720,00
  (+15%). Os percentuais apresentados serão recalculados a partir dos valores
  atuais e anteriores do mock.
- Resumo mensal ilustrativo: entradas R$ 18.720,00, saídas R$ 9.450,00 e lucro
  líquido R$ 9.270,00.
- Movimentações ilustrativas: Pagamento de Serviço (Cliente: João Silva,
  +R$ 120,00, Hoje às 16:20); Pagamento de Fornecedor (Produtos, −R$ 450,00,
  Hoje às 14:32); Serviço Realizado (Cliente: Lucas Souza, +R$ 100,00, Hoje às
  13:10).

## Limites

- Não há exclusão física: lançamentos estornados permanecem identificados no
  histórico e não podem ser editados ou estornados novamente.
- Não inclui exportação, conciliação bancária, notificações ou relatórios
  analíticos.
- Os lançamentos são registros manuais compartilhados pelos usuários
  autenticados; não há integração bancária ou associação automática com
  agendamentos nesta change.
- O saldo acumulado representa entradas menos saídas registradas desde o início
  do ledger, sem saldo inicial de caixa/banco.
- Os valores da referência (incluindo despesas de fornecedor) só podem aparecer
  como mock em desenvolvimento. Em produção, ausência ou falha da API deve
  resultar em estado de erro/vazio explícito, nunca em dados fictícios.
- Não criar itens de menu para relatórios, configurações ou outras rotas ainda
  inexistentes.

## Capabilities

### Nova capability

- `financeiro`: consulta autenticada de indicadores, fluxo de caixa, resumo
  mensal e movimentações recentes, com formatação, estados e adaptação
  responsiva.

### Capabilities modificadas

Nenhuma. A implementação da nova capability reutiliza os padrões visuais
existentes; os tokens financeiros que estiverem ausentes ficam registrados em
`design.md`.

## Impacto

- **Frontend Reflex:** integração da página e dos estados com a autenticação e
  o shell compartilhado; adição de rota, serviço, formulário de lançamento e
  componentes específicos de gráfico, donut e sparkline.
- **Xano:** tabelas `finance_transaction` e `finance_transaction_revision` e
  endpoints autenticados de consulta, criação, edição e estorno, acessíveis a
  administradores e profissionais.
- **Dados:** métricas e movimentações são calculadas a partir do ledger real;
  os dados ilustrativos não são uma fonte de verdade e só podem ser usados como
  mock explícito em desenvolvimento sem API configurada.
- **Verificação:** teste do acesso autenticado, cálculos e formatação,
  interações do gráfico, estados por bloco, acessibilidade e larguras desktop e
  mobile; compilar o Reflex.
