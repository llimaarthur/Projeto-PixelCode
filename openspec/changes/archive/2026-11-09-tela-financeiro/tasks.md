# Tarefas

## 1. Especificação e contratos

- [x] 1.1 Definir tipos de leitura para KPIs, comparativos, série por período,
      resumo mensal e movimentações, sem acoplar componentes aos mocks.
- [x] 1.2 Definir configuração explícita de mock apenas para desenvolvimento e
      comportamento de erro quando a API real não estiver configurada.
- [x] 1.3 Definir ledger compartilhado de entradas e saídas, escopo do saldo
      acumulado e contratos autenticados de leitura e gravação no Xano.

## 2. Rota e navegação autenticadas

- [x] 2.1 Adicionar `/financeiro` à aplicação com proteção pela sessão existente.
- [x] 2.2 Adicionar Financeiro à sidebar e propagar estado ativo e breadcrumb no
      shell compartilhado.
- [x] 2.3 Verificar redirecionamento sem sessão e navegação para a tela com
      sessão válida, sem alterar acessos de outras páginas.

## 3. Serviço e dados de demonstração

- [x] 3.1 Criar o serviço/provider financeiro e reutilizar autenticação,
      configuração de API e tratamento de erros existentes.
- [x] 3.2 Implementar mocks de KPIs e períodos anterior para permitir cálculo de
      variação percentual.
- [x] 3.3 Implementar mocks dos períodos 6 meses, 12 meses e ano atual, resumo e
      movimentações, incluindo valores da referência apenas em desenvolvimento.
- [x] 3.4 Testar que erro/ausência da API em produção nunca usa o mock como
      fallback.
- [x] 3.5 Testar BRL, data "Hoje, HH:mm", lucro líquido e variação com período
      anterior zero ou ausente.
- [x] 3.6 Criar as tabelas `finance_transaction` e
      `finance_transaction_revision` e endpoints autenticados de dashboard,
      registro, edição e estorno para administradores e profissionais.
- [x] 3.7 Derivar KPIs, séries de 6/12 meses e ano atual, resumo e saldo
      acumulado a partir dos lançamentos persistidos.
- [x] 3.8 Priorizar API configurada sobre mocks e exibir erros financeiros sem
      mensagens técnicas do provedor.
- [x] 3.9 Implementar edição autenticada com validação e histórico dos valores
      anteriores, usuário responsável e horário da alteração.
- [x] 3.10 Implementar estorno autenticado com motivo, mantendo o registro no
      histórico e removendo-o dos totais financeiros.

## 4. Componentes do painel

- [x] 4.1 Implementar os três cards KPI com ícone, valor, comparação e sparkline.
- [x] 4.2 Implementar o seletor acessível 6 meses/12 meses/Ano atual e o gráfico
      de área/linhas com eixos, tooltip e atualização de série/subtítulo.
- [x] 4.3 Implementar o donut de resumo mensal, lucro líquido, entradas, saídas
      e saldo acumulado.
- [x] 4.4 Implementar a lista de movimentações recentes com valores e horários.
- [x] 4.5 Reutilizar tokens e shell atuais; criar e documentar somente tokens ou
      componentes financeiros inexistentes, após validar contraste.
- [x] 4.6 Adicionar formulário autenticado para registrar entradas e saídas e
      atualizar a tela após persistir o lançamento.
- [x] 4.7 Reutilizar o formulário para editar lançamentos e adicionar
      confirmação de estorno com motivo obrigatório.
- [x] 4.8 Identificar lançamentos estornados no histórico e impedir ações
      repetidas pela interface.
- [x] 4.9 Ocultar movimentações estornadas por padrão e oferecer controle para
      exibi-las na lista sem afetar totais.

## 5. Estados, acessibilidade e responsividade

- [x] 5.1 Implementar loading skeleton, vazio e erro independentes em KPIs,
      fluxo de caixa, resumo e movimentações.
- [x] 5.2 Verificar teclado, foco visível, nomes acessíveis, descrição textual dos
      gráficos e tooltip acessível sem hover.
- [x] 5.3 Verificar contraste dos textos, séries e estados no tema escuro.
- [x] 5.4 Verificar desktop e mobile: KPIs empilhados e coluna lateral abaixo do
      gráfico, sem rolagem horizontal.

## 6. Verificação

- [x] 6.1 Executar testes direcionados de cálculos, ledger real, formatação,
      mock/API, dados de referência e estados vazios (14 testes passaram).
- [x] 6.2 Executar `reflex compile --dry` após as alterações da navegação e do
      formulário.
- [x] 6.7 Executar testes direcionados e `reflex compile --dry` após
      implementar edição e estorno.
- [x] 6.8 Sincronizar os quatro documentos Xano atualizados no workspace
      `Projeto PixelCode` (153819, branch `v1`) e confirmar sua presença via
      pull.
- [x] 6.4 Sincronizar os quatro documentos financeiros no workspace Xano
      `Projeto PixelCode` (153819) e confirmar sua presença via pull.
- [x] 6.5 Configurar `XANO_FINANCE_API_URL` para a base do grupo Finance
      (`/api:PCFin01`) e verificar que os endpoints respondem no grupo correto.
- [x] 6.3 Validar visualmente a rota, navegação ativa, gráficos, estados e
      breakpoints no navegador.
