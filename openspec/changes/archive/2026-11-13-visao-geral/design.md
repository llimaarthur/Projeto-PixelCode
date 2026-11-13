# Design: Visão geral

## Contexto encontrado

- `/app` já é uma rota protegida por sessão, mas `app_page()` em
  `frontend/frontend/auth_state.py` ainda renderiza um painel de boas-vindas
  placeholder. A sidebar já contém “Visão geral” apontando para `/app`.
- O shell compartilhado `_app_shell()` já apresenta breadcrumb, perfil e ação
  “Sair”. `_app_sidebar()` já marca o item `/app` como ativo.
- Financeiro já tem indicadores, sparklines, gráfico de fluxo de caixa,
  resumo em rosca, movimentações e estados visuais próprios. A camada
  `finance_service.py` normaliza os dados do ledger, calcula períodos e
  variações, formata BRL e prepara os caminhos dos gráficos.
- Agenda já consulta `/appointments` para intervalos de datas e prepara
  horário, cliente e snapshots dos serviços. Clientes já consulta `/contacts`
  com paginação, filtros de status e total correspondente ao filtro.
- A API de contatos aceita consultas paginadas e retorna `total`; portanto,
  contagens e percentuais não podem ser calculados apenas sobre a página
  visível. O endpoint atual não oferece filtro por data de cadastro.
- Não foi encontrado campo de foto no contrato de clientes/agendamentos. Fotos
  de perfil disponíveis no frontend referem-se ao usuário ou à equipe, não aos
  clientes.
- O tema escuro, variáveis de cor, shell/sidebar e breakpoints já estão em
  `frontend/assets/styles.css`. Financeiro já usa `Intl.NumberFormat` para BRL,
  `format_brl()` e `percentage_change()` para formatação/cálculo, e Agenda e
  Clientes já dispõem de normalização de data e horário.
- Não foi encontrado componente de barra de progresso existente.

## Decisões técnicas

1. **Usar `/app` como rota da Visão geral.** Substituir o placeholder, sem
   criar rota paralela. A rota usa uma verificação de sessão que reutiliza o
   carregamento de identidade e mantém o shell, breadcrumb, botão Sair, perfil
   e sidebar compartilhados.
2. **Consumir as consultas atuais.** Usar o estado/provider e o endpoint
   `finance/dashboard` para os dados financeiros, `/appointments` para os
   atendimentos e `/contacts` para as contagens de clientes. Não criar
   agregação no backend, tabela, endpoint nem lógica de escrita.
3. **Manter uma única lógica financeira.** Reutilizar os cálculos de
   `finance_service.py` para totais, variações, BRL e dados do gráfico. A
   agregação da Visão geral recebe os registros normalizados pelo dashboard
   financeiro existente; a lista paginada de movimentações continua sendo
   usada somente na tela Financeiro. No formato normalizado, o instante da
   movimentação fica em `input_datetime`; a agregação o adapta para a entrada
   temporal esperada por `finance_total()`. O
   seletor do cabeçalho terá “Últimos 7 dias”, “Últimos 30 dias” (padrão),
   “Últimos 90 dias” e “Ano atual”. Os quatro cartões mudam seus rótulos e
   valores conforme o período: Entradas, Saídas, Lucro Líquido e Novos
   Clientes. Cada valor é comparado com a janela anterior de mesma duração; em
   “Ano atual”, a comparação usa o intervalo equivalente do ano anterior. O
   filtro próprio do fluxo de caixa permanece independente e conserva 6 meses,
   12 meses e ano atual.
4. **Extrair apresentação reutilizável sem alterar a UX atual.**
   - Generalizar o cartão de KPI e o sparkline para valor monetário ou
     contagem, ícone, tendência, comparação e acessibilidade. Manter os
     ícones, dados e apresentação dos KPIs de Financeiro. Na Visão geral, o
     CSS do grid reorganiza ícone, texto e sparkline em duas linhas para caber
     nos quatro cartões sem comprimir os valores.
   - Reutilizar diretamente a rosca e o fluxo de caixa da página Financeiro,
     incluindo seu estado existente, para evitar duplicar SVG, filtros e
     cálculos.
   - Compartilhar skeleton, erro, vazio e a linha de movimentação somente
     leitura, sem os controles de edição/estorno da tela Financeiro. A
     tabela/lista interativa do Financeiro continua com suas ações e permissões
     atuais.
5. **Criar somente o que não existe.** Criar o layout responsivo da Visão geral,
   seletor de período do cabeçalho, cartão e linha de próximos agendamentos,
   resumo de clientes, barra de progresso de clientes ativos e links de
   navegação. O cartão de resumo de clientes mostra total de registros e
   percentual de ativos sobre o total, usando contagens retornadas pela API;
   não calcula o percentual com a página corrente. O cartão “Novos Clientes”
   conta registros por `first_contact_at` dentro do período escolhido, que é a
   única data relevante disponibilizada no contrato atual; não a apresenta como
   data de criação técnica do cadastro.
6. **Limitar a lista de agendamentos ao que pode ser exibido com segurança.**
   Consultar a API existente para o intervalo necessário, manter a ordenação
   cronológica, omitir atendimentos passados e estados terminais e apresentar
   o horário, cliente e serviços já disponíveis. Se uma foto não estiver
   disponível, exibir avatar com iniciais; não adicionar cadastro ou upload de
   imagens de clientes nesta change.
7. **Deixar os blocos isolados.** Cada bloco mantém estado visual de loading,
   vazio e erro e pode ser renderizado sem os demais. As consultas de clientes
   e agenda não dependem da consulta financeira. Se uma origem compartilhada
   por mais de um bloco falhar, os blocos dependentes dela apresentam erro sem
   impedir a exibição das outras origens.
8. **Somente leitura.** A Visão geral não contém formulário, botão de mutação,
   edição, estorno, confirmação nem chamada HTTP de escrita. Links “Ver mais”,
   “Ver todos” e “Ver todas” apenas navegam às áreas existentes.

## Componentes e recursos

### Reaproveitar

| Recurso | Localização | Uso na Visão geral |
| --- | --- | --- |
| Sessão, nome autenticado e controle de acesso | `frontend/frontend/auth_state.py` (`AuthState`, `require_session`) | Proteger `/app` e personalizar a saudação com o nome disponível. |
| Shell, breadcrumb, botão Sair e sidebar | `frontend/frontend/auth_state.py` (`_app_shell`, `_app_sidebar`) | Usar o layout já existente e manter “Visão geral” ativo. |
| Estado e consulta do dashboard financeiro | `frontend/frontend/auth_state.py` (`_load_finance_dashboard`) | Consumir o payload real/mocks de desenvolvimento pelas regras já existentes. |
| Normalização, cálculos e formato financeiro | `frontend/frontend/finance_service.py` (`finance_dashboard_from_transactions`, `percentage_change`, `format_brl`, `prepare_cashflow_chart`) | Reutilizar ledger, variações, BRL e séries de fluxo. |
| KPI, sparkline, erro, vazio, skeleton e apresentação de movimentação | `frontend/frontend/dashboard_components.py` | Compartilhar apresentação acessível e somente leitura; os KPIs de Financeiro mantêm ícones estáticos e comportamento existente. |
| Rosca, resumo e gráfico de linha/área | `frontend/frontend/finance_page.py` (`_summary_section`, `_summary_donut`, `_cashflow_section`, `_cashflow_chart`) | Reutilizar os mesmos componentes e estados do Financeiro, generalizando apenas título/link/rótulo do saldo no resumo. |
| Cálculos financeiros | `frontend/frontend/finance_service.py` (`finance_total`, `percentage_change`, `prepare_sparkline`, `prepare_cashflow_chart`) | Usar os mesmos registros normalizados e funções financeiras para agregar os períodos dinâmicos. |
| Consultas e normalização de agenda | `frontend/frontend/auth_state.py` (`_load_appointments`, `_parse_appointment_datetime`); `xano/api/appointments/appointments_GET.xs` | Consultar atendimentos e exibir dados/snapshots existentes. |
| Consultas e contagens de clientes | `frontend/frontend/auth_state.py` (`_load_contacts`, paginação) e `xano/api/contacts/contacts_GET.xs` | Consultar totais e status; usar `total` do contrato, não a página atual. |
| Tema, tokens, shell e breakpoints | `frontend/assets/styles.css` | Preservar tema escuro, identidade visual e adaptação a viewport menor. |
| Formatação de datas, horários e moeda | Helpers atuais de Agenda, Financeiro e Clientes | Reutilizar a localidade e os formatos existentes. |

### Extrair para componentes compartilhados

- Cartão de métrica e sparkline, com valor monetário ou numérico e ícone
  configurável; o Financeiro permanece visual e funcionalmente equivalente.
- Componentes genéricos de loading, erro e vazio.
- Apresentação somente leitura de uma movimentação, sem os controles de editar,
  estornar ou alterar status da tela Financeiro.

O resumo em rosca e o fluxo de caixa são reutilizados diretamente da página
Financeiro; não são copiados nem extraídos para outra camada.

### Criar

- Conteúdo da Visão geral em `/app`, grid dos quatro KPIs e composição dos
  blocos.
- Seletor global de período, independente do filtro do gráfico de fluxo.
- Lista compacta de próximos atendimentos, cartão de total/ativos de clientes
  e barra de progresso.
- CSS do grid da tela e regras responsivas específicas para os blocos novos.
- Estado de apresentação/consulta da Visão geral que orquestra dados já
  disponíveis sem duplicar regras de domínio ou alterar outras rotas.

## Fontes de dados e limites

| Bloco | Fonte existente | Observações |
| --- | --- | --- |
| Entradas, saídas e lucro no período; rosca; saldo; fluxo | `GET finance/dashboard`, via `_load_finance_dashboard()` | O dashboard já fornece os registros normalizados usados para os cálculos e gráficos financeiros. A agregação por janela usa `finance_total()`, adapta `input_datetime` e exclui estornadas dos totais. |
| Movimentações recentes | Registros normalizados de `GET finance/dashboard`, via `_load_finance_dashboard()` | Reutiliza a mesma lista cronológica do ledger para mostrar os lançamentos mais recentes, sem depender da página selecionada na tela Financeiro nem apresentar suas ações de escrita. |
| Total de clientes e ativos | `GET contacts` | Percorrer todas as páginas retornadas para contar os status; `total` informa a soma geral, mas não quantos registros são ativos. Percentual = ativos / total, com zero tratado sem divisão inválida. |
| Novos Clientes por período | `GET contacts` e `first_contact_at` | O endpoint não filtra por data de primeiro contato; percorrer páginas existentes para contar os registros do período atual e do anterior. Esse campo indica primeiro contato, não a data de criação do registro. |
| Próximos atendimentos | `GET appointments` com intervalo atual/futuro | A API já retorna horários, contato e snapshots de serviços. Itens sem foto usam iniciais; dados não retornados não serão inventados. |
| Saudação | `AuthState.display_name` | Usar o nome da sessão carregada; manter fallback visual consistente se o nome estiver vazio. |

## Riscos e mitigação

- **Custo da contagem histórica de clientes:** `/contacts` pagina os registros,
  mas não consulta um período de primeiro contato. Para contar “Novos
  Clientes”, percorrer as páginas pode custar mais em bases grandes. Não usar
  apenas a página visível; medir a quantidade de chamadas e manter o resultado
  separado dos demais blocos. Um endpoint agregado seria uma change de backend
  futura, fora do escopo atual.
- **Fotos de clientes ausentes:** não há campo de foto no contrato encontrado.
  Usar iniciais sem bloquear os atendimentos; qualquer suporte a imagens fica
  fora desta change.
- **Falha da fonte financeira compartilhada:** KPIs, fluxo, rosca e
  movimentações dependem da consulta financeira existente. Exibir estado de
  erro nos blocos dependentes e continuar exibindo Agenda e Clientes.
- **Preservação do Financeiro:** extrair componentes sem mudar seletores,
  permissões, ações de escrita, filtros, conteúdo nem responsividade da tela
  existente; cobrir a equivalência com testes.
- **Séries vazias ou base zero:** não calcular percentuais por divisão por zero
  nem representar falta de dados como sucesso; usar estados vazios e
  comparações indisponíveis.
- **Escopo visual:** não implementar nem reservar espaço para “Serviços Mais
  Procurados”.
