## ADDED Requirements

### Requirement: Papéis e equipe restritos à barbearia

Cada usuário interno SHALL pertencer a uma única barbearia. O papel `admin`
SHALL permitir gerenciar usuários e consultar dados somente dessa barbearia; o
papel `professional` SHALL manter suas permissões atuais dentro da mesma
barbearia. O backend SHALL impedir associação de profissionais a outra
barbearia e SHALL NOT conceder acesso administrativo global.

#### Scenario: Administrador gerencia a própria equipe

- **WHEN** um administrador cria ou consulta profissionais da sua barbearia
- **THEN** o backend permite a operação somente para contas vinculadas ao
  mesmo tenant

#### Scenario: Administrador tenta acessar equipe externa

- **WHEN** um administrador consulta ou altera um profissional de outra
  barbearia
- **THEN** o backend rejeita a operação sem revelar ou alterar os dados externos

#### Scenario: Signup cria o primeiro administrador

- **WHEN** uma barbearia é cadastrada pelo fluxo público
- **THEN** sua conta proprietária é o primeiro usuário `admin` daquela
  barbearia e não recebe privilégios sobre outras organizações
