## ADDED Requirements

### Requirement: Papéis e equipe restritos à barbearia

Cada usuário interno SHALL pertencer a uma única barbearia. O papel `admin`
SHALL permitir gerenciar usuários e consultar dados somente dessa barbearia. O
papel `professional` SHALL poder consultar a lista da equipe da própria
barbearia em modo somente leitura e SHALL NOT criar, editar, excluir ou
redefinir a senha de outros membros. O backend SHALL impedir associação de
profissionais a outra barbearia e SHALL NOT conceder acesso administrativo
global.

#### Scenario: Administrador gerencia a própria equipe

- **WHEN** um administrador cria ou consulta profissionais da sua barbearia
- **THEN** o backend permite a operação somente para contas vinculadas ao
  mesmo tenant

#### Scenario: Administrador tenta acessar equipe externa

- **WHEN** um administrador consulta ou altera um profissional de outra
  barbearia
- **THEN** o backend rejeita a operação sem revelar ou alterar os dados externos

#### Scenario: Profissional consulta a equipe da própria barbearia

- **WHEN** um profissional abre a lista da equipe
- **THEN** o backend retorna somente os membros da barbearia associada à sessão
  e a interface não oferece ações administrativas

#### Scenario: Profissional tenta alterar outro membro

- **WHEN** um profissional chama diretamente uma API de criação, alteração,
  exclusão ou redefinição de senha de outro membro
- **THEN** o backend rejeita a operação por falta de papel administrativo

#### Scenario: Signup cria o primeiro administrador

- **WHEN** uma barbearia é cadastrada pelo fluxo público
- **THEN** sua conta proprietária é o primeiro usuário `admin` daquela
  barbearia e não recebe privilégios sobre outras organizações
