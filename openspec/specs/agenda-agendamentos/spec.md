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
