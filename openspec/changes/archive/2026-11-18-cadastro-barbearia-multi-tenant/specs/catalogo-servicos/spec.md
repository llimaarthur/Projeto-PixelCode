## MODIFIED Requirements

### Requirement: Catálogo único da barbearia

O sistema SHALL manter um catálogo de serviços compartilhado pelos
profissionais de cada barbearia e isolado dos catálogos de outros tenants. Cada
serviço SHALL pertencer a exatamente uma barbearia. O backend SHALL derivar o
escopo da conta autenticada e SHALL NOT exigir nem confiar em um identificador
de barbearia enviado pelo frontend.

#### Scenario: Profissionais consultam o mesmo catálogo

- **WHEN** profissionais autenticados consultam o catálogo de serviços ativos
- **THEN** recebem somente os serviços ativos da barbearia à qual pertencem

#### Scenario: Acesso sem tenant

- **WHEN** um profissional autenticado consulta ou administra serviços conforme
  seu papel sem selecionar uma barbearia
- **THEN** a operação usa o tenant da sessão e não retorna nem altera serviços
  de outra barbearia

#### Scenario: Acesso cruzado ao catálogo

- **WHEN** uma pessoa tenta consultar, editar ou alterar o status de um serviço
  de outra barbearia
- **THEN** o backend rejeita a operação sem revelar ou alterar o serviço externo
