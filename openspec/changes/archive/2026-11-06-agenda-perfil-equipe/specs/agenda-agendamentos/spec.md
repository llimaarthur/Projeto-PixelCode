# Spec Delta

## Purpose

Definir o calendário mensal, a disponibilidade diária e a gestão de agendamentos internos, preservando a integridade de horários, os dados históricos dos serviços e o escopo de acesso de cada papel.

## ADDED Requirements

### Requirement: Consulta da agenda diária
O sistema SHALL permitir consultar os agendamentos de uma data em ordem cronológica. Administradores SHALL poder escolher um profissional ativo; profissionais SHALL consultar somente a própria agenda.

#### Scenario: Administrador consulta a agenda
- **WHEN** um administrador autenticado consulta uma data e um profissional
- **THEN** o sistema retorna os agendamentos daquele profissional e data em ordem de início

#### Scenario: Profissional consulta a própria agenda
- **WHEN** um profissional autenticado consulta uma data
- **THEN** o sistema retorna apenas os agendamentos associados à sua própria conta

#### Scenario: Profissional tenta consultar agenda alheia
- **WHEN** um profissional envia o identificador de outro profissional na consulta
- **THEN** o sistema rejeita o acesso ou ignora o identificador e limita o resultado à própria agenda

### Requirement: Calendário mensal e disponibilidade
O sistema SHALL permitir navegar entre meses e selecionar uma data. O calendário SHALL indicar as datas que possuem agendamentos. Para a data selecionada, o sistema SHALL apresentar horários em intervalos de 30 minutos e indicar cada horário como disponível, ocupado ou bloqueado.

#### Scenario: Navegar no calendário
- **WHEN** a equipe avança ou retorna um mês e seleciona uma data
- **THEN** o calendário atualiza o mês, destaca a data selecionada e carrega a disponibilidade dessa data

#### Scenario: Indicar dias com agendamentos
- **WHEN** um mês é exibido
- **THEN** as datas que possuem agendamentos registrados são identificadas no calendário

#### Scenario: Gerar horários dentro do expediente
- **WHEN** a disponibilidade de uma data é consultada
- **THEN** são exibidos inícios em intervalos de 30 minutos dentro do expediente de segunda a sexta das 09:00 às 19:00, exceto 12:00–13:00, e sábado das 09:00 às 14:00; domingo não oferece horários

#### Scenario: Calcular disponibilidade pela duração do serviço
- **WHEN** um serviço está selecionado
- **THEN** um horário só é oferecido como disponível se a duração do serviço couber no expediente e não houver sobreposição com atendimento ativo ou bloqueio do profissional

#### Scenario: Selecionar data e horário no formulário
- **WHEN** o usuário escolhe data, profissional e serviços no formulário de agendamento
- **THEN** o formulário usa a mesma lógica da agenda para oferecer somente horários disponíveis que comportem a duração total dos serviços

#### Scenario: Bloquear horário manualmente
- **WHEN** um usuário autorizado cria um bloqueio para um profissional e intervalo válidos
- **THEN** o horário passa a ser indicado como bloqueado e nenhuma criação ou edição de agendamento pode ocupá-lo

### Requirement: Criação e edição de agendamentos
Todo agendamento SHALL conter um cliente ativo, um profissional ativo, pelo menos um serviço ativo, início e status. O fim e os totais SHALL ser calculados a partir da soma das durações e preços vigentes dos serviços no momento da gravação.

#### Scenario: Criar agendamento válido
- **WHEN** um usuário autorizado envia cliente, profissional, serviços ativos e horário sem conflito
- **THEN** o sistema grava o agendamento e os snapshots de nome, preço e duração dos serviços

#### Scenario: Rejeitar dados incompletos ou inativos
- **WHEN** a criação ou edição não contém cliente, profissional ou serviço válido e ativo
- **THEN** o sistema rejeita a operação e informa o motivo

#### Scenario: Editar agendamento
- **WHEN** um usuário com acesso ao agendamento altera seus dados
- **THEN** o sistema valida novamente as referências e o horário e atualiza os snapshots e totais

#### Scenario: Preservar histórico do catálogo
- **WHEN** o preço ou a duração de um serviço é alterado após um agendamento
- **THEN** os snapshots do agendamento existente permanecem inalterados

#### Scenario: Criar cliente durante o agendamento
- **WHEN** o usuário cadastra um cliente com nome e telefone válidos, sem duplicar o telefone existente
- **THEN** o cliente é persistido, selecionado no agendamento e os demais dados já preenchidos permanecem

#### Scenario: Rejeitar cliente duplicado
- **WHEN** o telefone informado já identifica outro cliente
- **THEN** o backend rejeita o cadastro e informa o conflito sem perder o formulário de agendamento

### Requirement: Prevenção de conflitos
O sistema SHALL rejeitar a criação ou edição de um agendamento cujo intervalo se sobreponha ao de outro agendamento não cancelado do mesmo profissional.

#### Scenario: Horário sobreposto
- **WHEN** o intervalo solicitado se sobrepõe parcialmente ou totalmente a outro atendimento não cancelado do profissional
- **THEN** o sistema rejeita a operação e informa o conflito

#### Scenario: Horário adjacente
- **WHEN** um agendamento começa exatamente no horário de término de outro
- **THEN** o sistema permite a operação

#### Scenario: Horário liberado por cancelamento
- **WHEN** um atendimento conflitante está cancelado
- **THEN** o sistema permite ocupar o horário liberado

### Requirement: Atualização e cancelamento
O sistema SHALL permitir alterar o status entre pendente, confirmado, concluído e cancelado, sem apagar registros. Profissionais SHALL alterar somente os próprios agendamentos; administradores SHALL poder alterar qualquer agendamento.

#### Scenario: Cancelar agendamento
- **WHEN** um usuário autorizado cancela um agendamento
- **THEN** o registro permanece consultável com status cancelado e deixa de bloquear o horário

#### Scenario: Profissional tenta alterar agendamento alheio
- **WHEN** um profissional tenta editar, alterar status ou cancelar um agendamento de outro profissional
- **THEN** o sistema nega a operação sem modificar os dados

### Requirement: Listagem e detalhes de agendamentos
O sistema SHALL apresentar os atendimentos da data selecionada em uma tabela com horário, cliente, serviço, profissional, status e ações. SHALL permitir filtrar a lista e consultar os detalhes de cada atendimento.

A visualização padrão SHALL omitir atendimentos cancelados; o usuário SHALL poder consultá-los selecionando explicitamente o filtro "Cancelado". Após confirmar um cancelamento, a lista e a disponibilidade SHALL ser atualizadas sem recarregar a página.

#### Scenario: Consultar e filtrar agendamentos
- **WHEN** um usuário seleciona uma data e aplica um filtro disponível
- **THEN** a tabela exibe somente os registros correspondentes, em ordem cronológica

#### Scenario: Omitir cancelamentos na visualização padrão
- **WHEN** a lista de agendamentos é exibida sem filtro de cancelados
- **THEN** os agendamentos cancelados não são exibidos, mas permanecem armazenados e podem ser consultados pelo filtro "Cancelado"

#### Scenario: Abrir detalhes
- **WHEN** um usuário seleciona um agendamento
- **THEN** o sistema apresenta em uma janela modal os dados do cliente, data, horário, serviços, valor, profissional, status e observações

#### Scenario: Confirmar cancelamento
- **WHEN** o usuário solicita cancelar um agendamento e confirma a ação
- **THEN** o status é alterado para cancelado, o horário é liberado e o registro permanece no histórico

### Requirement: Confirmação do agendamento
Após criar um agendamento válido, o sistema SHALL apresentar uma confirmação com cliente e telefone, data, horário, serviço, valor e profissional, com ações para abrir a listagem e iniciar outro agendamento.

#### Scenario: Agendamento criado
- **WHEN** o backend confirma a criação do agendamento
- **THEN** o sistema exibe a confirmação verde com todos os dados registrados e as ações de continuidade

#### Scenario: Backend rejeita a gravação
- **WHEN** a disponibilidade mudou ou os dados são rejeitados pelo backend
- **THEN** o sistema mantém o formulário e apresenta o erro sem exibir confirmação de sucesso
