# acesso-interno-profissionais Specification

## Purpose
Definir como a identidade e o papel da equipe são apresentados após o login e como os dados de cadastro de profissionais são validados.

## Requirements

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
- **THEN** o formulário é limpo e a senha definitiva não é exibida nem retornada novamente

### Requirement: Senha definitiva no cadastro de profissionais

O formulário SHALL exigir uma senha para o novo profissional. O backend SHALL validar que ela contém pelo menos oito caracteres, uma letra e um dígito, armazená-la usando o campo de senha do usuário e criar a conta sem exigir troca no primeiro acesso. A senha SHALL NOT ser retornada na resposta da API.

#### Scenario: Cadastro com senha válida

- **WHEN** a administradora cadastra um profissional com uma senha que atende aos requisitos mínimos
- **THEN** a conta é criada com essa senha definitiva, sem troca obrigatória no primeiro acesso, e a senha não é exibida nem retornada novamente

#### Scenario: Cadastro com senha inválida ou ausente

- **WHEN** a administradora envia uma senha ausente ou que não atende aos requisitos mínimos
- **THEN** o backend rejeita o cadastro sem criar a conta e a interface mantém os dados para correção

### Requisito: Confirmação persistente e paginação da equipe

Após cadastrar um profissional com sucesso, a interface SHALL mostrar uma confirmação até a administradora sair da seção de equipe. A lista SHALL mostrar no máximo quatro profissionais por página.

#### Cenário: Cadastro concluído na seção de equipe

- **WHEN** o cadastro do profissional é concluído com sucesso
- **THEN** a confirmação permanece visível enquanto a administradora permanecer na seção de equipe e desaparece ao navegar para outra seção

#### Cenário: Lista da equipe paginada

- **WHEN** houver mais de quatro profissionais cadastrados
- **THEN** a lista exibe até quatro profissionais por página e permite navegar pelas demais páginas

### Requisito: Persistência de CPF e senha no cadastro

O endpoint de cadastro SHALL gravar o CPF e a senha enviados pela administradora nos campos correspondentes da conta Xano. Os nomes das entradas usadas para esses dados SHALL ser distintos dos nomes das colunas para evitar conflitos com campos ocultos do Xano.

#### Cenário: Cadastro de novo profissional

- **WHEN** a administradora envia um CPF e uma senha válidos
- **THEN** o CPF fica registrado na conta e a senha permite autenticar o profissional

### Requisito: Edição de perfil e foto

O perfil SHALL permitir que usuários autenticados atualizem nome, e-mail e telefone na própria conta. O upload da foto SHALL usar a configuração do Cloudinary disponível no ambiente do projeto ou no arquivo `.env`, validar o formato e limitar o arquivo a 5 MB. A foto SHALL ser persistida na conta autenticada.

#### Cenário: Salvar dados pessoais

- **WHEN** o usuário informa nome, e-mail e telefone válidos
- **THEN** os dados são atualizados na própria conta e refletidos na interface
- **AND** uma mensagem de sucesso aparece junto ao formulário de dados pessoais

#### Cenário: Enviar foto de perfil

- **WHEN** o usuário envia uma imagem JPEG, PNG ou WebP válida de até 5 MB com o Cloudinary configurado
- **THEN** a foto é armazenada e exibida no perfil
- **AND** uma mensagem de sucesso aparece junto aos controles da foto

#### Cenário: Foto de perfil mantém o layout do editor

- **WHEN** a foto de perfil é exibida no editor
- **THEN** a imagem permanece limitada ao tamanho do avatar e não encobre os demais controles ou seções

#### Cenário: Remover foto de perfil

- **WHEN** o usuário remove a foto de perfil
- **THEN** a foto deixa de ser exibida e uma mensagem de sucesso aparece junto aos controles da foto
- **AND** a remoção permanece após navegar para outra seção ou entrar novamente na conta

### Requisito: Alteração de senha no perfil

O perfil SHALL permitir que usuários autenticados alterem a própria senha após informar a senha atual e confirmar uma nova senha com ao menos oito caracteres, uma letra e um número. O backend SHALL validar esses requisitos, comparar os campos de senha nova e confirmação e atualizar a senha somente quando forem iguais.

#### Cenário: Confirmação de senha nova

- **WHEN** o usuário informa duas vezes a mesma senha nova válida e a senha atual correta
- **THEN** a senha é atualizada com sucesso

- **WHEN** as senhas novas informadas forem diferentes
- **THEN** a alteração é rejeitada e a senha existente permanece inalterada
