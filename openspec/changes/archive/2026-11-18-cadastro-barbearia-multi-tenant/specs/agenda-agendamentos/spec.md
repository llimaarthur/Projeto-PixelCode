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

#### Scenario: Concluir um atendimento

- **WHEN** um profissional conclui um agendamento confirmado com valor positivo
- **THEN** o agendamento é concluído e uma receita vinculada ao cliente e ao
  agendamento é registrada no financeiro

#### Scenario: Trocar de tela ou profissional após salvar

- **WHEN** uma pessoa navega para outra tela ou entra com outra conta
- **THEN** mensagens de sucesso e dados antigos da agenda não permanecem
  visíveis

### Requirement: Expediente semanal compartilhado da barbearia

Cada barbearia SHALL ter um único expediente semanal compartilhado pela equipe,
configurável somente por um administrador do tenant e legível por todos os
profissionais da mesma barbearia. Cada dia SHALL aceitar zero, um ou vários
intervalos ordenados, sem sobreposição, em grade de 30 minutos. A criação de
agendamentos e bloqueios SHALL ser validada no backend contra esse expediente.
Uma nova barbearia SHALL iniciar sem expediente configurado; a barbearia legada
SHALL preservar seu expediente atual até que o administrador o altere.

#### Scenario: Administrador define vários intervalos no mesmo dia

- **WHEN** o administrador salva intervalos válidos e não sobrepostos para os
  dias da semana
- **THEN** o expediente fica salvo para a barbearia e os horários disponíveis,
  agendamentos e bloqueios passam a respeitá-lo

#### Scenario: Profissional consulta o expediente

- **WHEN** um profissional consulta a agenda
- **THEN** vê o expediente semanal compartilhado da própria barbearia, sem
  permissão para alterá-lo

#### Scenario: Profissional tenta alterar o expediente

- **WHEN** um profissional envia uma chamada direta para alterar o expediente
- **THEN** o backend rejeita a chamada sem modificar os horários

#### Scenario: Agendamento fora do expediente

- **WHEN** qualquer usuário tenta criar ou editar um agendamento ou bloqueio
  fora dos intervalos definidos
- **THEN** o backend rejeita a operação

#### Scenario: Horário ausente em barbearia nova

- **WHEN** a barbearia ainda não configurou expediente
- **THEN** nenhum horário é oferecido ou aceito até que o administrador salve
  pelo menos um intervalo
