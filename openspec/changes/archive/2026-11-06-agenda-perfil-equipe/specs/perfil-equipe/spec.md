# Spec Delta

## Purpose

Definir como cada usuário autenticado consulta e atualiza os próprios dados cadastrais, foto de perfil e senha.

## ADDED Requirements

### Requirement: Consulta e edição do próprio perfil
O sistema SHALL permitir que um usuário autenticado consulte e atualize o próprio nome, e-mail e telefone. A identidade do perfil SHALL ser obtida da sessão autenticada e SHALL ignorar identificadores de outros usuários enviados pelo cliente.

O diálogo de edição do perfil SHALL exibir e permitir alterar somente nome, e-mail, telefone, foto e senha. O CPF existente SHALL permanecer inalterado e não SHALL ser exibido, validado nem enviado pelo formulário de edição.

Os campos nome, e-mail e telefone SHALL iniciar preenchidos e permitir edição. O endpoint de atualização SHALL aceitar CPF omitido e preservar o valor atual do perfil.

#### Scenario: Consultar perfil
- **WHEN** um usuário autenticado abre o próprio perfil
- **THEN** o sistema retorna nome, e-mail, telefone e CPF da conta autenticada

#### Scenario: Atualizar dados válidos
- **WHEN** o usuário envia dados válidos para atualizar seu perfil
- **THEN** somente a própria conta é atualizada e a interface exibe confirmação

#### Scenario: E-mail já utilizado
- **WHEN** o usuário tenta alterar o e-mail para um endereço já associado a outra conta
- **THEN** o sistema rejeita a alteração e preserva os dados atuais

#### Scenario: Perfil inválido
- **WHEN** nome, e-mail ou telefone não passam pela validação
- **THEN** o sistema rejeita a alteração e informa o campo inválido

#### Scenario: Editar perfil sem alterar CPF
- **WHEN** o usuário atualiza os dados pelo diálogo de perfil
- **THEN** o formulário não exibe nem envia CPF e o valor cadastrado permanece inalterado

#### Scenario: Editar dados de perfil
- **WHEN** o usuário altera nome, e-mail ou telefone no diálogo e salva
- **THEN** o sistema persiste os novos valores, atualiza o nome exibido na navegação e apresenta feedback em português

### Requirement: Foto de perfil própria
O sistema SHALL permitir que o usuário autenticado consulte, envie, substitua ou remova a própria foto de perfil. A imagem SHALL ser armazenada no Xano File Storage, associada à conta autenticada e validada pelo backend. Os formatos JPEG, PNG e WebP SHALL ser aceitos até o limite de 5 MB por arquivo.

#### Scenario: Enviar foto de perfil
- **WHEN** o usuário autenticado envia uma imagem JPEG, PNG ou WebP de até 5 MB
- **THEN** o sistema armazena a imagem e a associa ao próprio perfil

#### Scenario: Substituir foto de perfil
- **WHEN** o usuário autenticado envia uma nova imagem válida
- **THEN** a foto apresentada no perfil passa a ser a imagem enviada para sua própria conta

#### Scenario: Remover foto de perfil
- **WHEN** o usuário autenticado solicita a remoção da própria foto
- **THEN** o sistema remove a associação à imagem da própria conta sem alterar a foto de outros usuários

#### Scenario: Envio inválido ou não autorizado
- **WHEN** o arquivo não é JPEG, PNG ou WebP, excede 5 MB, ou a solicitação tenta alterar a imagem de outra conta
- **THEN** o sistema rejeita a operação sem substituir a foto existente

### Requirement: Alteração segura da própria senha
O sistema SHALL permitir que cada usuário altere a própria senha informando a senha atual, uma nova senha que atenda aos requisitos vigentes e sua confirmação.

Os campos de senha no login e no diálogo de perfil SHALL iniciar ocultos e SHALL permitir mostrar ou ocultar cada valor por meio de um controle acessível por teclado, com rótulo acessível correspondente ao estado.

#### Scenario: Mostrar e ocultar senha
- **WHEN** o usuário ativa o controle de visibilidade de um campo de senha
- **THEN** somente aquele campo alterna entre texto e senha e o rótulo acessível informa a ação disponível

#### Scenario: Senha alterada com sucesso
- **WHEN** a senha atual é válida e a nova senha atende aos requisitos e coincide com a confirmação
- **THEN** o sistema atualiza a senha da conta autenticada sem retornar ou registrar o segredo

#### Scenario: Senha atual ou confirmação inválida
- **WHEN** a senha atual está incorreta, a nova senha não atende aos requisitos ou a confirmação diverge
- **THEN** o sistema rejeita a alteração e mantém a senha existente

#### Scenario: Usuário tenta alterar a senha de outra conta
- **WHEN** uma solicitação de alteração de senha contém um identificador de outra conta
- **THEN** o sistema ignora esse identificador ou rejeita a solicitação e nunca altera a conta alheia
