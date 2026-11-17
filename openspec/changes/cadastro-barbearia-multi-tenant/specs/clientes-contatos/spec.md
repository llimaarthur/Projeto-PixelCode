## MODIFIED Requirements

### Requirement: Cadastro compartilhado de clientes e contatos

O sistema SHALL manter um cadastro de clientes/contatos compartilhado entre os
usuários autorizados da mesma barbearia e isolado dos demais tenants. Um
contato SHALL representar uma pessoa externa sem credencial de acesso ao
sistema. Cada contato SHALL estar vinculado a exatamente uma barbearia, e a
estrutura e as APIs SHALL impedir consulta ou associação cruzada entre
barbearias.

#### Scenario: Equipe consulta a mesma base

- **WHEN** administrador e profissional autorizados da mesma barbearia
  consultam contatos
- **THEN** ambos recebem registros daquele tenant, respeitando os filtros e
  permissões definidos

#### Scenario: Contato não possui acesso

- **WHEN** um contato é criado ou atualizado
- **THEN** o sistema não cria login, senha, sessão ou qualquer credencial para
  essa pessoa

#### Scenario: Cliente de outra barbearia não é exposto

- **WHEN** um usuário autenticado consulta ou tenta usar um contato vinculado a
  outra barbearia
- **THEN** o backend não retorna seus dados nem permite associá-lo a uma
  operação do tenant atual
