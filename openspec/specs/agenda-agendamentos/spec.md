# agenda-agendamentos Specification

## Purpose
Define regras confiáveis para alterar o status dos agendamentos e manter a
listagem e o financeiro coerentes com o estado persistido.

## Requirements

### Requirement: Transições válidas de status do agendamento
O backend SHALL aceitar somente as transições `pendente → confirmado`,
`pendente → cancelado`, `confirmado → concluído` e
`confirmado → cancelado`. Agendamentos concluídos ou cancelados SHALL ser
terminais na alteração manual de status. Um pagamento associado poderá
concluir explicitamente um agendamento pendente ou confirmado; seu estorno
deverá restaurar exatamente o status que existia antes do pagamento. O backend
SHALL rejeitar transições inválidas sem alterar o registro.

#### Scenario: Confirmar ou cancelar um agendamento pendente
- **WHEN** um usuário autorizado altera um agendamento pendente para confirmado
  ou cancelado
- **THEN** o backend persiste o novo status e a listagem apresenta o status
  retornado

#### Scenario: Concluir ou cancelar um agendamento confirmado
- **WHEN** um usuário autorizado altera um agendamento confirmado para
  concluído ou cancelado
- **THEN** o backend persiste o novo status e a listagem apresenta o status
  retornado

#### Scenario: Rejeitar transição inválida ou terminal
- **WHEN** um usuário tenta reabrir um agendamento concluído ou cancelado, ou
  executa qualquer outra transição não permitida
- **THEN** a API rejeita a operação com mensagem clara e mantém o status salvo

#### Scenario: Concluir e restaurar pelo ciclo de pagamento
- **WHEN** um lançamento de receita conclui um agendamento pendente ou
  confirmado e depois é estornado
- **THEN** o pagamento registra o status anterior, o estorno restaura esse
  status e as telas apresentam o valor persistido

### Requirement: Atualização de status na listagem da agenda
A listagem SHALL permitir solicitar as transições válidas de cada agendamento.
Após confirmação do backend, a interface SHALL atualizar imediatamente o status
do registro sem recarregar a página e exibir feedback de sucesso. Em caso de
erro ou transição inválida, SHALL manter o status anteriormente confirmado e
informar a falha.

#### Scenario: Atualizar status pela listagem
- **WHEN** o usuário escolhe uma transição válida na linha de um agendamento
- **THEN** a tela persiste a alteração, atualiza a linha sem recarregar a página
  e anuncia o sucesso

#### Scenario: Falha ao atualizar status
- **WHEN** o backend rejeita a alteração ou não está disponível
- **THEN** a tela mantém o status previamente salvo e apresenta uma mensagem de
  erro

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
