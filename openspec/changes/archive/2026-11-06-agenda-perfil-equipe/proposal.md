# Proposta: Agenda e perfil da equipe

## Por quê

O painel já oferece autenticação, cadastro de clientes e catálogo de serviços, mas a agenda ainda não oferece uma visão mensal de disponibilidade nem um fluxo completo para criar, consultar e acompanhar atendimentos. A equipe também precisa cadastrar clientes sem interromper o agendamento e manter os próprios dados atualizados.

## O que muda

- Criar um calendário mensal com navegação por mês, seleção de data e indicação dos dias com agendamentos.
- Exibir horários de 30 minutos para a data selecionada, diferenciando horários disponíveis, ocupados e bloqueados.
- Respeitar o expediente da barbearia: segunda a sexta das 09:00 às 19:00, com pausa das 12:00 às 13:00; sábado das 09:00 às 14:00; domingo fechado. O expediente é igual para todos os profissionais.
- Permitir criar e editar agendamentos com cliente, profissional, um ou mais serviços, data, horário e observações, considerando a duração total dos serviços.
- Permitir cadastrar um cliente rapidamente durante o agendamento, solicitando somente nome e telefone e sem perder os dados já preenchidos.
- Apresentar confirmação com resumo do atendimento após salvar o agendamento.
- Criar a listagem diária de agendamentos com filtros, detalhes, edição e cancelamento confirmado, preservando o histórico.
- Permitir registrar bloqueios manuais de horário para a agenda e respeitá-los na consulta e gravação de agendamentos.
- Rejeitar conflitos de horário para o mesmo profissional e preservar preço e duração dos serviços no momento do agendamento.
- Aplicar no Xano as permissões de administrador e profissional, incluindo o limite de acesso do profissional à própria agenda.
- Permitir que cada usuário atualize o próprio nome, e-mail, telefone, senha e foto de perfil em um diálogo aberto pelo bloco de usuário da sidebar, sem exibir ou alterar o CPF já armazenado.
- Validar os dados e proteger as operações de perfil no Xano, sem permitir que um usuário altere a conta de outra pessoa.

## Limites

- O calendário é mensal para navegação; a consulta, os horários e a listagem de atendimentos continuam sendo de uma data por vez.
- A disponibilidade é baseada no expediente semanal informado, nos serviços, nos agendamentos ativos e nos bloqueios manuais; não inclui feriados nacionais automáticos, recorrência de agendamentos ou múltiplas filiais.
- O cliente continua sem acesso ao sistema; clientes e profissionais são selecionados pela equipe.
- Não inclui pagamentos, notificações ou relatórios.
- O profissional não poderá administrar o perfil de outra pessoa.
- A alteração de senha exigirá a senha atual e confirmação da nova senha.
- O sistema continua atendendo uma única barbearia, sem introduzir tenants ou filiais.

## Capabilities

### Novas capabilities

- `agenda-agendamentos`: calendário mensal, consulta de disponibilidade, bloqueios, criação rápida de cliente e gestão de agendamentos, com validação e preservação do histórico.
- `perfil-equipe`: manutenção dos dados e da senha da própria conta da equipe.

### Capabilities modificadas

Nenhuma. As regras de agenda e de perfil serão publicadas nas capabilities novas desta change.

## Impacto

- **Backend Xano:** novas estruturas e endpoints para agendamentos e perfil; validações e autorização permanecem no backend.
- **Frontend Reflex:** calendário e formulário de agendamentos, diálogo de perfil aberto pela sidebar, formulários e estados de carregamento/erro.
- **Foto de perfil:** requer armazenamento e validação de imagens autorizados para o usuário da sessão.
- **Configuração:** variável opcional para a URL do grupo de APIs de agendamentos, usando a URL geral como fallback.
