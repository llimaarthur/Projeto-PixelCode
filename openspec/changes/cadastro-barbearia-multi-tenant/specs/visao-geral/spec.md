## ADDED Requirements

### Requirement: Visão geral restrita à barbearia autenticada

A Visão geral SHALL agregar somente dados da barbearia vinculada à sessão
autenticada. As consultas de contatos, agendamentos e financeiro usadas pelos
blocos SHALL ser escopadas no backend; contagens e comparações SHALL NOT
combinar dados de tenants diferentes.

#### Scenario: Exibir resumo de uma barbearia

- **WHEN** um usuário autenticado abre a Visão geral
- **THEN** cartões, gráficos, contagens e listas apresentam somente dados da
  própria barbearia

#### Scenario: Usuários de barbearias distintas

- **WHEN** usuários de duas barbearias consultam a Visão geral
- **THEN** cada usuário recebe métricas independentes, sem dados ou totais do
  outro tenant
