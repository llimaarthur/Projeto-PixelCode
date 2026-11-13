# Proposal

## Why

Os status da agenda não têm uma política única de transições, e os lançamentos
financeiros podem ser estornados sem conferir a autoria. O registro também não
reaproveita clientes e serviços cadastrados, enquanto a lista exige carregar os
lançamentos sem paginação no servidor.

## What Changes

- Definir e validar no backend transições explícitas de status dos agendamentos,
  com atualização imediata na listagem.
- Vincular lançamentos de receita de serviços a cliente, serviços e,
  opcionalmente, a um agendamento; registrar o status anterior ao pagamento
  para restaurá-lo no estorno.
- Restringir estornos ao autor do lançamento, exceto para ADM, registrar autor,
  data e motivo, e rejeitar estornos repetidos.
- Permitir selecionar clientes e múltiplos serviços cadastrados no formulário,
  calcular o total automaticamente e aceitar ajuste manual do valor.
- Paginar no backend a lista financeira em três lançamentos por página,
  preservando o filtro de estornados e a ordenação mais recente primeiro.

## Capabilities

### New Capabilities

- `agenda-agendamentos`: Transições autorizadas de status e consistência do
  status na agenda.

### Modified Capabilities

- `financeiro`: Autorização e auditoria de estornos, vínculo dos lançamentos a
  clientes, serviços e agendamentos, formulário e paginação do ledger.

## Impact

- Frontend Reflex: estado, eventos e componentes da agenda e do formulário/lista
  financeiro.
- Backend Xano: APIs de status de agendamento e financeiro; esquema de
  lançamentos e auditoria.
- APIs existentes de clientes, serviços e agenda serão reutilizadas para
  selecionar registros cadastrados. Nenhuma dependência externa será adicionada.
