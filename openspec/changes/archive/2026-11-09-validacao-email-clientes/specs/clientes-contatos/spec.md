## Requisitos adicionados

### Requirement: Cadastro de cliente aceita e-mail válido

Os formulários de cadastro e edição de clientes SHALL encaminhar e-mails válidos
para a validação da aplicação, sem rejeitá-los previamente por uma validação
nativa do navegador. A validação da aplicação e do backend SHALL continuar ativa.

#### Scenario: Salvar cliente com e-mail válido

- **WHEN** o usuário cadastra ou edita um cliente com um e-mail válido, como
  `arthurgoes@gmail.com`
- **THEN** o formulário não bloqueia o envio antes da validação da aplicação
