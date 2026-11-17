## ADDED Requirements

### Requirement: Agenda e agendamentos isolados por barbearia

Agendamentos e bloqueios de agenda SHALL pertencer à barbearia do profissional
associado. O backend SHALL limitar consultas e alterações ao tenant da sessão,
validar que profissional e contato pertencem ao mesmo tenant e aplicar as
regras de autorização e transição de status existentes dentro desse escopo.

#### Scenario: Consultar agenda do próprio tenant

- **WHEN** um usuário autorizado consulta agendamentos ou bloqueios
- **THEN** recebe somente registros da sua barbearia e de profissionais que
  pode consultar

#### Scenario: Criar agendamento com referências externas

- **WHEN** um usuário tenta criar ou editar agendamento usando profissional ou
  contato de outra barbearia
- **THEN** o backend rejeita a operação e não altera agenda, contato ou
  agendamento

#### Scenario: Tentar alterar agenda de outra barbearia

- **WHEN** um usuário envia uma alteração direta para agendamento ou bloqueio
  de outro tenant
- **THEN** o backend rejeita a operação sem revelar dados nem alterar o estado
