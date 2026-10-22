# Spec Delta

## ADDED Requirements

### Requirement: Identidade disponível após o login

O backend SHALL incluir o identificador, nome, papel e sinalizador de troca obrigatória de senha na resposta de login. O frontend SHALL usar esses dados para renderizar imediatamente o menu autorizado, sem aguardar a consulta subsequente de identidade.

#### Scenario: Administradora entra no painel

- **WHEN** uma administradora autentica com credenciais válidas
- **THEN** a resposta do login informa seu papel e a interface exibe imediatamente a opção de equipe

#### Scenario: Profissional entra no painel

- **WHEN** um profissional autentica com credenciais válidas
- **THEN** a resposta do login informa seu papel e a interface exibe apenas as opções autorizadas para esse papel

#### Scenario: Usuário precisa trocar a senha

- **WHEN** o login informa que a senha deve ser trocada
- **THEN** o frontend redireciona o usuário para a troca de senha em vez de abrir o painel

### Requirement: Máscaras do cadastro de profissionais

O formulário de cadastro de profissionais SHALL aplicar a mesma máscara progressiva de telefone usada no cadastro de clientes, limitar o número a no máximo 11 dígitos nacionais e exigir telefone válido antes do envio. O campo CPF SHALL aceitar somente até 11 dígitos, exibir os pontos e o hífen conforme o padrão `000.000.000-00` e exigir os 11 dígitos antes do envio.

#### Scenario: Digitação do telefone profissional

- **WHEN** a administradora digita um telefone no cadastro do profissional
- **THEN** o campo formata o DDD e o número progressivamente e não permite mais de 11 dígitos nacionais

#### Scenario: Digitação do CPF profissional

- **WHEN** a administradora digita o CPF no cadastro do profissional
- **THEN** o campo insere os pontos e o hífen progressivamente e não permite mais de 11 dígitos

#### Scenario: Cadastro profissional com CPF incompleto

- **WHEN** a administradora tenta enviar um CPF com menos de 11 dígitos
- **THEN** o frontend apresenta uma mensagem de validação e não envia a requisição
