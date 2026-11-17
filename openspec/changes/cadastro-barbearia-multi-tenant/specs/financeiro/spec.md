## ADDED Requirements

### Requirement: Ledger financeiro isolado por barbearia

Cada movimentação financeira e sua trilha de revisões SHALL pertencer à
barbearia autenticada. Consultas, filtros, paginação, saldo acumulado,
indicadores e fluxos SHALL considerar somente lançamentos daquele tenant. O
backend SHALL validar que autor, contato, serviços e agendamento associados
pertencem à mesma barbearia.

#### Scenario: Consultar indicadores financeiros

- **WHEN** um usuário autorizado consulta o dashboard ou o ledger financeiro
- **THEN** totais, listagens e saldo incluem somente registros da sua
  barbearia

#### Scenario: Registrar movimentação com referência externa

- **WHEN** uma movimentação referencia contato, serviço ou agendamento de outra
  barbearia
- **THEN** o backend rejeita a escrita sem criar lançamento ou revisão

#### Scenario: Acessar lançamento externo

- **WHEN** uma pessoa tenta consultar, editar ou estornar lançamento de outro
  tenant
- **THEN** o backend rejeita a operação sem revelar valores, autor ou histórico
