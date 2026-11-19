## MODIFIED Requirements

### Requirement: Cadastro compartilhado de clientes e contatos

O sistema SHALL manter clientes isolados por barbearia e permitir que
administradores consultem e atribuam contatos a profissionais ativos do mesmo
tenant. A API padrão de clientes SHALL retornar a um profissional somente os
contatos atribuídos a ele. Contatos sem responsável, inclusive os existentes
antes desta regra e os criados por administradores sem atribuição, SHALL
permanecer sob controle administrativo até serem atribuídos. Um contato SHALL
representar uma pessoa externa sem credencial de acesso ao sistema.

#### Scenario: Equipe consulta a mesma base

- **WHEN** administrador e profissional autenticados consultam contatos da
  mesma barbearia
- **THEN** cada um recebe os registros permitidos para seu papel e carteira,
  sem acesso a dados de outra barbearia

#### Scenario: Administrador consulta e atribui contatos

- **WHEN** o administrador consulta a carteira ou atribui um contato
- **THEN** ele recebe os contatos da própria barbearia e pode atribuir ou
  transferir o responsável somente para um profissional ativo do mesmo tenant

#### Scenario: Profissional consulta somente sua carteira

- **WHEN** um profissional consulta clientes e contatos
- **THEN** recebe somente os contatos cujo responsável é seu usuário autenticado;
  contatos sem responsável ou atribuídos a outros membros não são retornados

#### Scenario: Profissional cria e atualiza seu próprio cliente

- **WHEN** um profissional cria um contato ou altera o cadastro/status de um
  contato atribuído a ele
- **THEN** o backend atribui o novo contato ao profissional autenticado e
  permite alterar somente os contatos da carteira dele

#### Scenario: Profissional não interfere em carteira alheia

- **WHEN** um profissional tenta consultar, editar, transferir ou alterar o
  status de um contato de outro responsável por chamada direta à API
- **THEN** a consulta não retorna o contato e a mutação é rejeitada

#### Scenario: Uso de contato em agendamento

- **WHEN** um profissional agenda um cliente ativo atribuído a ele, ou um
  administrador agenda qualquer cliente ativo da própria barbearia
- **THEN** o backend permite o agendamento na agenda autorizada sem conceder
  permissão para o profissional editar contatos de outra carteira

#### Scenario: Profissional tenta agendar cliente de outra carteira

- **WHEN** um profissional tenta criar ou editar um agendamento com contato
  atribuído a outro profissional ou sem responsável
- **THEN** o backend rejeita a operação mesmo em uma chamada direta à API

#### Scenario: Uso financeiro de contato

- **WHEN** um profissional cria, edita ou estorna uma movimentação vinculada a
  um cliente
- **THEN** o cliente deve estar atribuído a esse profissional; administradores
  podem gerir movimentações vinculadas a qualquer cliente do tenant

#### Scenario: Contato não possui acesso

- **WHEN** um contato é criado ou atualizado
- **THEN** o sistema não cria login, senha, sessão ou qualquer credencial para
  essa pessoa

#### Scenario: Cliente de outra barbearia não é exposto

- **WHEN** um usuário autenticado consulta ou tenta usar um contato vinculado a
  outra barbearia
- **THEN** o backend não retorna seus dados nem permite associá-lo a uma
  operação do tenant atual
