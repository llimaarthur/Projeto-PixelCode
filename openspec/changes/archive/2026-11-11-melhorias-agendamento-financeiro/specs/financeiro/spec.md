# Spec Delta

## MODIFIED Requirements

### Requirement: Registro de movimentações
O sistema SHALL permitir que administradores e profissionais autenticados
registrem entradas e saídas com valor positivo, descrição, detalhe opcional e
data/hora. Ao registrar uma receita de serviço, a interface SHALL permitir
selecionar um cliente existente e um ou mais serviços ativos, apresentar os
preços cadastrados e calcular o total automaticamente, permitindo ajuste
manual. Ao selecionar um agendamento relacionado, o cliente SHALL ser o mesmo
do agendamento, o agendamento SHALL estar pendente ou confirmado, e o pagamento
SHALL concluir o atendimento registrando o status anterior para eventual
restauração no estorno. O backend SHALL persistir autor, cliente, serviços e
agendamento associados quando informados, e SHALL validar as referências e os
campos obrigatórios.

Lançamentos ativos SHALL poder ser editados; cada edição SHALL preservar os
valores anteriores, o usuário responsável e o horário da alteração em um
histórico de auditoria. Um profissional SHALL estornar somente os lançamentos
que registrou; um administrador SHALL poder estornar qualquer lançamento. O
backend SHALL validar essa autorização, registrar no histórico o autor, a data,
o motivo e os dados revertidos, restaurar o status anterior do agendamento
relacionado quando houver e atualizar o valor considerado nos totais. Um
lançamento estornado SHALL permanecer no histórico, não participar dos totais
financeiros e não poder ser estornado novamente. Lançamentos SHALL ser
imutáveis após estorno.

#### Scenario: Selecionar cliente e múltiplos serviços
- **WHEN** o usuário registra uma receita de serviços
- **THEN** pode selecionar um cliente cadastrado, adicionar serviços
  ativos, ver o total calculado a partir dos preços e editar o valor final

#### Scenario: Validar registro e referências
- **WHEN** o usuário envia um lançamento sem os campos obrigatórios, com valor
  inválido ou com cliente, serviço ou agendamento inexistente/incompatível
- **THEN** o backend rejeita o registro e a interface exibe orientação clara
  sem indicar sucesso

#### Scenario: Associar pagamento a um agendamento
- **WHEN** o usuário registra uma receita vinculada a um agendamento pendente
  ou confirmado do cliente selecionado
- **THEN** o lançamento guarda o vínculo e o status anterior, e o backend
  conclui o agendamento

#### Scenario: Profissional estorna lançamento próprio
- **WHEN** um profissional autenticado estorna um lançamento ativo que ele
  mesmo registrou, informando motivo válido
- **THEN** o backend aceita o estorno, registra autor/data/motivo no histórico e
  atualiza os totais e o agendamento relacionado

#### Scenario: Profissional tenta estornar lançamento alheio
- **WHEN** um profissional autenticado tenta estornar um lançamento de outro
  usuário
- **THEN** o backend rejeita a operação com mensagem clara e não altera o
  lançamento, o histórico ou o agendamento

#### Scenario: Administrador estorna lançamento de qualquer autor
- **WHEN** um administrador autenticado estorna um lançamento ativo de qualquer
  usuário, com motivo válido
- **THEN** o backend aceita a operação e registra o administrador, a data e o
  motivo no histórico

#### Scenario: Estornar movimentação
- **WHEN** um usuário autorizado confirma o estorno com um motivo válido
- **THEN** o backend marca o lançamento como estornado, registra o motivo e o
  usuário no histórico, mantém o lançamento visível e remove seu valor dos
  indicadores e do saldo acumulado

#### Scenario: Rejeitar estorno duplicado
- **WHEN** um usuário tenta estornar um lançamento já estornado
- **THEN** o backend rejeita a operação sem criar outro histórico nem alterar
  novamente os totais ou o agendamento

#### Scenario: Registrar entrada ou saída
- **WHEN** um usuário autorizado envia uma movimentação válida
- **THEN** o backend persiste os dados e o usuário responsável, e o painel
  atualiza os indicadores e a lista

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

#### Scenario: Preservar lançamentos estornados
- **WHEN** um usuário consulta ou tenta editar um lançamento estornado
- **THEN** o lançamento permanece identificado como estornado no histórico e o
  backend rejeita novas edições ou estornos

### Requirement: Movimentações recentes
A tela SHALL apresentar uma lista de movimentações de entrada e saída com tipo,
descrição, detalhe, valor em BRL e data/hora. Entradas e saídas SHALL ter
indicações semânticas distintas além da cor. A API SHALL devolver a lista
ordenada da mais recente para a mais antiga, paginada no backend com três itens
por página, total de registros e página corrente. O controle para ocultar ou
exibir estornadas SHALL ser aplicado no backend e preservado ao navegar entre
páginas.

#### Scenario: Exibir movimentações registradas
- **WHEN** o provider retorna movimentações recentes
- **THEN** cada item mostra natureza, título, detalhe, valor e horário relativo
  em pt-BR, incluindo "Hoje, HH:mm" para itens do dia

#### Scenario: Navegar por páginas
- **WHEN** há mais de três movimentações e o usuário avança ou volta uma página
- **THEN** a interface solicita a página ao backend, mostra no máximo três itens
  ordenados e preserva o filtro de estornadas

#### Scenario: Exibir totais e última página incompleta
- **WHEN** o usuário consulta a lista, inclusive uma última página com menos de
  três itens
- **THEN** a interface indica total de registros e páginas e desabilita a
  navegação além dos limites

#### Scenario: Lista sem movimentações no filtro
- **WHEN** não há movimentações para a página ou filtro selecionado
- **THEN** a interface apresenta o estado vazio correto e mantém a contagem e a
  navegação consistentes

#### Scenario: Lista sem movimentações
- **WHEN** não há movimentações recentes
- **THEN** a lista apresenta estado vazio sem exibir itens de exemplo

#### Scenario: Falha ao consultar movimentações
- **WHEN** a consulta de movimentações falha
- **THEN** a lista apresenta erro explícito e mantém os demais blocos
  independentes

#### Scenario: Filtrar movimentações estornadas
- **WHEN** a lista contém movimentações estornadas e o usuário altera sua
  visibilidade
- **THEN** a lista reinicia na primeira página e aplica o filtro no backend sem
  alterar os totais financeiros

#### Scenario: Exibir lista mock de referência
- **WHEN** o provider mock está explicitamente habilitado em desenvolvimento
- **THEN** a lista inclui Pagamento de Serviço (Cliente: João Silva,
  +R$ 120,00, Hoje às 16:20), Pagamento de Fornecedor (Produtos, −R$ 450,00,
  Hoje às 14:32) e Serviço Realizado (Cliente: Lucas Souza, +R$ 100,00,
  Hoje às 13:10)

#### Scenario: Atualizar ao entrar na seção
- **WHEN** um usuário navega para Financeiro sem recarregar a aplicação
- **THEN** a seção consulta o endpoint de dashboard, atualiza os dados e mantém
  o shell e o item ativo da sidebar
