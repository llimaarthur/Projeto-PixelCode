## MODIFIED Requirements

### Requirement: Criar e editar contato

O sistema SHALL permitir que administrador e profissionais autenticados criem
e editem contatos com nome obrigatório, telefone obrigatório, origem do
contato obrigatória, e-mail opcional, observações opcionais e status ativo ou
inativo. Um contato novo SHALL iniciar ativo. O backend SHALL validar os
campos antes de persistir alterações. Quando informado, o e-mail SHALL ser
recebido como texto, normalizado com espaços externos removidos e letras
minúsculas, e limitado a 254 caracteres. Os formulários de cliente SHALL usar
validação nativa de campo de e-mail do navegador para impedir o envio de
endereços malformados; o campo vazio SHALL continuar permitido. Os campos de
CPF e e-mail SHALL exibir exemplos de formato como placeholders, em alinhamento
com o formulário de profissionais.

#### Scenario: Criar contato válido

- **WHEN** um usuário interno envia nome, telefone e origem válidos, com
  observações opcionais
- **THEN** o backend persiste o contato como ativo e retorna seus dados
  atualizados

#### Scenario: Contato aparece após criação

- **WHEN** um contato é criado com sucesso e a listagem é atualizada sem filtros
  restritivos
- **THEN** o contato recém-criado aparece na base de clientes

#### Scenario: Data retornada pela API

- **WHEN** a API retorna a data do primeiro contato como data ISO ou timestamp
  Unix em segundos ou milissegundos
- **THEN** a interface interpreta a data e exibe o contato sem rejeitar os
  demais campos retornados

#### Scenario: Rejeitar dados inválidos

- **WHEN** um usuário envia nome vazio, telefone vazio ou inválido, origem não
  permitida ou texto fora dos limites definidos
- **THEN** o backend rejeita a operação, informa os campos inválidos e não
  persiste o contato

#### Scenario: Criar contato com e-mail válido

- **WHEN** um usuário autenticado envia um e-mail válido, como
  `kaiquelemes@gmail.com`
- **THEN** o backend aceita o e-mail e persiste o contato

#### Scenario: Impedir envio de e-mail inválido pelo formulário

- **WHEN** um usuário informa um e-mail não vazio com formato inválido no
  formulário de cliente
- **THEN** o navegador impede o envio do formulário e nenhum contato é
  persistido

#### Scenario: Editar contato existente

- **WHEN** um usuário interno altera os dados de um contato existente com
  valores válidos
- **THEN** o backend atualiza o mesmo registro sem criar um novo contato

#### Scenario: Usuário não autenticado tenta alterar

- **WHEN** uma pessoa sem sessão autenticada tenta criar ou editar um contato
- **THEN** o backend nega a operação sem persistir dados
