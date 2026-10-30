# Spec Delta

## ADDED Requirements

### Requirement: Cadastro profissional verifica e-mail normalizado
O backend SHALL verificar a existência de uma conta usando o e-mail normalizado enviado no cadastro. SHALL rejeitar somente e-mails já associados a uma conta e SHALL permitir a criação quando não houver correspondência; a restrição de unicidade do e-mail no banco SHALL continuar ativa.

#### Scenario: E-mail ainda não cadastrado
- **WHEN** a administradora envia um e-mail válido que não pertence a nenhuma conta
- **THEN** o backend cria o profissional e retorna os dados de acesso inicial

#### Scenario: E-mail já cadastrado
- **WHEN** a administradora envia um e-mail que, após normalização, pertence a uma conta existente
- **THEN** o backend rejeita o cadastro com uma mensagem explícita de e-mail já utilizado e não cria outra conta

### Requirement: Formulário de profissional preserva dados em falhas
O formulário de cadastro profissional SHALL preservar os valores digitados quando uma validação local ou a API rejeitar a criação e SHALL limpar os campos somente após a criação ser confirmada com sucesso.

#### Scenario: API rejeita o cadastro
- **WHEN** a API rejeita a criação do profissional
- **THEN** a mensagem de erro é apresentada e os campos preenchidos permanecem disponíveis para correção ou nova tentativa

#### Scenario: Cadastro concluído
- **WHEN** a API confirma a criação do profissional
- **THEN** o formulário é limpo e a senha temporária retornada é apresentada à administradora
