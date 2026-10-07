# Spec Delta

## Purpose

Define como os profissionais da barbearia entram no PixelCode e como o sistema distingue o acesso administrativo do acesso de cada profissional.

## ADDED Requirements

### Requirement: Acesso exclusivo de usuários internos
O sistema SHALL autenticar somente contas internas provisionadas pela barbearia e SHALL impedir que clientes criem contas por autoinscrição pública.

#### Scenario: Profissional autenticado
- **WHEN** um profissional com credenciais válidas envia suas credenciais
- **THEN** o sistema inicia uma sessão autenticada associada à conta daquele profissional

#### Scenario: Tentativa de autoinscrição pública
- **WHEN** uma pessoa tenta criar uma conta por um fluxo público de cadastro
- **THEN** o sistema não cria a conta nem concede acesso

### Requirement: Conta vinculada ao profissional
Cada conta interna SHALL representar um único profissional. O cadastro de um profissional SHALL exigir nome, e-mail, telefone e CPF. A conta administradora SHALL também representar um profissional.

#### Scenario: Identificar profissional autenticado
- **WHEN** uma operação autenticada é realizada
- **THEN** o sistema consegue identificar o profissional representado pela conta

#### Scenario: Criar profissional com dados obrigatórios
- **WHEN** o administrador envia nome, e-mail, telefone e CPF válidos para cadastrar um profissional
- **THEN** o sistema cria uma conta associada ao profissional com esses dados

#### Scenario: Recusar cadastro incompleto
- **WHEN** o administrador tenta cadastrar um profissional sem qualquer um dos campos obrigatórios
- **THEN** o sistema rejeita o cadastro e informa os dados ausentes

### Requirement: Provisionamento manual de profissionais
O sistema SHALL permitir que o administrador autenticado crie contas para profissionais pela aplicação, sem abrir esse fluxo ao público.

#### Scenario: Administrador cria profissional
- **WHEN** o administrador fornece os dados necessários para criar a conta de um profissional
- **THEN** o sistema cria a conta associada ao profissional, gera uma senha temporária e a exibe ao administrador uma única vez

#### Scenario: Profissional tenta criar outra conta
- **WHEN** um profissional sem papel administrativo tenta provisionar uma conta
- **THEN** o sistema nega a operação e não cria a conta

#### Scenario: Tentar criar outro administrador
- **WHEN** o único administrador tenta criar ou promover outra conta com papel de administrador
- **THEN** o sistema rejeita a operação e mantém apenas uma conta administradora

#### Scenario: Primeiro administrador
- **WHEN** a barbearia prepara a primeira conta administradora
- **THEN** a conta é provisionada diretamente no Xano, sem endpoint público de criação do primeiro administrador

### Requirement: Troca da senha temporária
O sistema SHALL exigir que um profissional altere sua senha temporária antes de acessar as demais áreas protegidas.

#### Scenario: Segredo temporário não é persistido em logs
- **WHEN** o sistema gera e entrega a senha temporária ao administrador
- **THEN** o sistema não inclui esse segredo nos logs nem o retorna em consultas posteriores

#### Scenario: Primeiro acesso com senha temporária
- **WHEN** um profissional inicia sessão usando a senha temporária
- **THEN** o sistema permite a troca de senha e impede o acesso às demais áreas até a conclusão

#### Scenario: Acesso após troca de senha
- **WHEN** o profissional define uma nova senha válida
- **THEN** o sistema remove a exigência de troca e permite o acesso conforme seu papel

### Requirement: Permissões do administrador
O administrador SHALL poder gerenciar contas de profissionais e acessar dados operacionais de qualquer profissional.

#### Scenario: Administrador consulta agenda da equipe
- **WHEN** o administrador consulta a agenda de um profissional
- **THEN** o sistema autoriza a consulta independentemente de quem seja o profissional associado

### Requirement: Permissões do profissional
Um profissional SHALL acessar somente a própria agenda e os atendimentos associados à sua conta, e SHALL poder consultar a lista compartilhada de clientes da barbearia.

#### Scenario: Profissional consulta a própria agenda
- **WHEN** o profissional consulta sua agenda autenticado
- **THEN** o sistema apresenta os dados associados àquele profissional

#### Scenario: Profissional tenta consultar agenda alheia
- **WHEN** o profissional tenta consultar a agenda ou os atendimentos de outro profissional
- **THEN** o sistema nega o acesso

#### Scenario: Profissional consulta a lista compartilhada de clientes
- **WHEN** um profissional autenticado consulta a lista de clientes
- **THEN** o sistema permite a consulta sem exigir que os clientes tenham atendimento previamente associado àquele profissional