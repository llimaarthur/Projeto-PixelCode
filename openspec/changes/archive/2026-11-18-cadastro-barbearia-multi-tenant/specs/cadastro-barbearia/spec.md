## ADDED Requirements

### Requirement: Cadastro público de barbearia e proprietário

O sistema SHALL permitir que uma pessoa cadastre uma barbearia informando o
nome da barbearia, nome do proprietário, e-mail, telefone e senha. O backend
SHALL validar e normalizar os dados, aplicar a política de senha existente e
manter o e-mail único globalmente. Em uma única operação lógica, SHALL criar a
barbearia e sua primeira conta interna com papel `admin` vinculada somente a
essa barbearia. O endpoint SHALL NOT aceitar do solicitante um identificador
de tenant, papel ou status. A resposta SHALL NOT conter senha, hash ou segredo.

#### Scenario: Cadastro válido

- **WHEN** uma pessoa envia nome da barbearia e dados válidos do proprietário
- **THEN** o backend cria uma barbearia e sua conta proprietária administradora,
  sem associar o usuário ou os dados a outra barbearia
- **AND** a interface autentica a conta recém-criada e encaminha a pessoa para a
  área da aplicação
- **AND** se a autenticação automática falhar, a interface informa que a
  barbearia foi criada e encaminha a pessoa para o login

#### Scenario: Login com a senha definida no cadastro

- **WHEN** a pessoa proprietária informa a senha escolhida ao criar a conta e
  depois a utiliza no login
- **THEN** o backend armazena a senha protegida uma única vez e valida a senha
  original no login
- **AND** nenhuma senha ou hash é retornado ao cliente

#### Scenario: Cadastros independentes de barbearia

- **WHEN** pessoas diferentes enviam dados válidos e únicos para cadastrar
  barbearias
- **THEN** cada solicitação cria sua própria barbearia e conta administradora
- **AND** um cadastro válido não é rejeitado por colisão de metadados de
  migração de outra barbearia

#### Scenario: E-mail já utilizado

- **WHEN** uma pessoa tenta cadastrar uma barbearia com e-mail normalizado já
  associado a uma conta
- **THEN** o backend rejeita o cadastro sem criar barbearia nem usuário e
  informa o conflito de forma explícita

  #### Scenario: Telefone já utilizado

  - **WHEN** uma pessoa tenta cadastrar uma barbearia com telefone normalizado
    já associado a uma conta de outra barbearia
  - **THEN** o backend rejeita o cadastro sem criar barbearia nem usuário e
    informa o conflito de forma explícita

#### Scenario: Dados ou senha inválidos

- **WHEN** algum campo obrigatório é inválido ou a senha não cumpre a política
  existente
- **THEN** o backend rejeita a operação sem persistir a barbearia ou conta
  parcial e a interface mantém os dados para correção

#### Scenario: Telefone brasileiro em formatos aceitos

- **WHEN** uma pessoa envia um telefone com máscara, apenas dígitos, com DDI
  `55` ou com espaços nas pontas
- **THEN** o frontend e o backend normalizam o valor para 10 ou 11 dígitos
  sem máscara e persistem o telefone padronizado
- **AND** rejeitam letras, símbolos inválidos, DDD inexistente, menos de 10
  dígitos ou mais de 11 dígitos sem DDI

#### Scenario: Falha durante a criação

- **WHEN** ocorre uma falha ao criar a barbearia ou a conta proprietária
- **THEN** a operação não deixa registros órfãos, não informa sucesso e retorna
  um erro explícito

### Requirement: Isolamento de dados por barbearia

Cada conta interna e cada registro operacional novo SHALL ser vinculado
explicitamente a uma barbearia. Registros legados com `barbershop_id` nulo
SHALL ser tratados como pertencentes somente à barbearia inicial enquanto sua
compatibilidade legada estiver ativa. Toda API autenticada SHALL derivar o
tenant da conta autenticada no backend. Consultas, alterações, contagens,
paginação, dashboard e financeiro SHALL incluir o escopo da barbearia; valores
nulos só podem ser incluídos no escopo da barbearia inicial. O backend SHALL
validar que registros relacionados pertencem ao mesmo tenant e SHALL rejeitar
acesso a IDs de outra barbearia. O frontend SHALL NOT ser considerado uma
barreira de autorização nem escolher o tenant de uma operação.

#### Scenario: Usuários da mesma barbearia compartilham os dados autorizados

- **WHEN** membros autorizados da mesma barbearia consultam contatos, serviços,
  agenda ou financeiro
- **THEN** recebem os registros daquele tenant, respeitando os papéis e
  permissões existentes

#### Scenario: Usuário tenta consultar dados de outra barbearia

- **WHEN** uma conta autenticada solicita diretamente um registro, listagem ou
  agregado pertencente a outro tenant
- **THEN** o backend rejeita ou não retorna o registro externo e não revela
  dados da outra barbearia

#### Scenario: Referências cruzadas entre barbearias

- **WHEN** uma operação associa um agendamento, contato, serviço, profissional
  ou movimentação de outra barbearia
- **THEN** o backend rejeita a operação sem alterar nenhum registro

#### Scenario: Tenant forjado pelo cliente

- **WHEN** uma requisição autenticada envia um identificador de barbearia
  diferente daquele vinculado à conta
- **THEN** o backend ignora o valor para autorização e usa o tenant da sessão,
  sem expor nem modificar registros externos

### Requirement: Compatibilidade de registros legados

O sistema SHALL permitir inicializar uma barbearia legada sem atualizar em
massa as linhas existentes. Registros com `barbershop_id` nulo SHALL ser
visíveis e utilizáveis somente por contas resolvidas para a barbearia inicial
com compatibilidade legada ativa. Contas e registros criados depois da mudança
SHALL sempre receber um `barbershop_id` explícito. A resolução do tenant legado
SHALL ocorrer somente no backend e não SHALL permitir que o cliente selecione
ou habilite compatibilidade.

#### Scenario: Acesso aos dados legados

- **WHEN** uma conta da barbearia inicial consulta registros antigos sem
  `barbershop_id`
- **THEN** o backend os trata como pertencentes somente à barbearia inicial

#### Scenario: Outro tenant consulta um registro nulo

- **WHEN** uma conta de uma nova barbearia tenta consultar ou associar um
  registro sem `barbershop_id`
- **THEN** o backend não retorna nem associa esse registro

#### Scenario: Nova gravação na barbearia inicial

- **WHEN** um membro da barbearia inicial cria um registro
- **THEN** o backend grava o `barbershop_id` explícito da barbearia inicial
