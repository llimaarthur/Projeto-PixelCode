# Spec Delta

## Purpose

Definir o cadastro compartilhado de clientes/contatos externos da única barbearia e seu uso pela equipe interna.

## ADDED Requirements

### Requirement: Cadastro compartilhado de clientes e contatos

O sistema SHALL manter um cadastro único e compartilhado de clientes/contatos da barbearia. Um contato SHALL representar uma pessoa externa sem credencial de acesso ao sistema. A estrutura SHALL NOT exigir identificador de barbearia, filial, organização ou tenant.

#### Scenario: Equipe consulta a mesma base

- **WHEN** administrador e profissional autenticados consultam os contatos
- **THEN** ambos recebem registros da mesma base compartilhada da barbearia, respeitando os filtros e permissões definidos

#### Scenario: Contato não possui acesso

- **WHEN** um contato é criado ou atualizado
- **THEN** o sistema não cria login, senha, sessão ou qualquer credencial para essa pessoa

### Requirement: Criar e editar contato

O sistema SHALL permitir que administrador e profissionais autenticados criem e editem contatos com nome obrigatório, telefone obrigatório, origem do contato obrigatória, observações opcionais e status ativo ou inativo. Um contato novo SHALL iniciar ativo. O backend SHALL validar os campos antes de persistir alterações.

#### Scenario: Criar contato válido

- **WHEN** um usuário interno envia nome, telefone e origem válidos, com observações opcionais
- **THEN** o backend persiste o contato como ativo e retorna seus dados atualizados

#### Scenario: Contato aparece após criação

- **WHEN** um contato é criado com sucesso e a listagem é atualizada sem filtros restritivos
- **THEN** o contato recém-criado aparece na base de clientes

#### Scenario: Data retornada pela API

- **WHEN** a API retorna a data do primeiro contato como data ISO ou timestamp Unix em segundos ou milissegundos
- **THEN** a interface interpreta a data e exibe o contato sem rejeitar os demais campos retornados

#### Scenario: Rejeitar dados inválidos

- **WHEN** um usuário envia nome vazio, telefone vazio ou inválido, origem não permitida ou texto fora dos limites definidos
- **THEN** o backend rejeita a operação, informa os campos inválidos e não persiste o contato

#### Scenario: Editar contato existente

- **WHEN** um usuário interno altera os dados de um contato existente com valores válidos
- **THEN** o backend atualiza o mesmo registro sem criar um novo contato

#### Scenario: Usuário não autenticado tenta alterar

- **WHEN** uma pessoa sem sessão autenticada tenta criar ou editar um contato
- **THEN** o backend nega a operação sem persistir dados

### Requirement: Normalização e identificação por telefone

O sistema SHALL normalizar espaços excedentes dos campos textuais e SHALL armazenar o telefone em formato consistente para consulta. O backend SHALL impedir a criação de dois contatos ativos com o mesmo telefone normalizado.

O formulário SHALL aplicar máscara progressiva ao telefone durante a digitação: DDD entre parênteses, hífen após o quinto dígito do número celular ou após o quarto dígito do número fixo, e prefixo opcional `+55`. O formulário SHALL validar DDD e quantidade de dígitos e enviar o telefone normalizado. O sistema SHALL rejeitar entradas inválidas com mensagem explícita e SHALL preservar os demais dados preenchidos.

O frontend SHALL enviar o telefone já normalizado como apenas dígitos. O backend SHALL validar que o valor recebido possui 10 ou 11 caracteres, sem depender de filtros regex na validação do tamanho.

#### Scenario: Telefone repetido

- **WHEN** um usuário tenta criar ou editar um contato usando telefone já associado a outro contato ativo
- **THEN** o backend rejeita a operação e informa que o telefone já está cadastrado

#### Scenario: Telefone brasileiro formatado

- **WHEN** um usuário informa um telefone brasileiro válido com pontuação ou com o prefixo `+55`
- **THEN** o sistema normaliza o valor para DDD e número com 10 ou 11 dígitos antes de salvar

#### Scenario: Telefone inválido no formulário

- **WHEN** um usuário informa telefone sem DDD válido ou com quantidade de dígitos incorreta
- **THEN** o formulário apresenta uma mensagem específica, não envia a requisição e mantém os dados preenchidos

#### Scenario: Atualização do próprio telefone

- **WHEN** um usuário edita um contato mantendo o telefone normalizado que já pertence ao próprio registro
- **THEN** o backend aceita a operação sem criar conflito consigo mesmo

### Requirement: Consulta, busca e filtros

O sistema SHALL permitir que usuários internos autenticados consultem contatos ativos e inativos conforme sua autorização. A consulta SHALL permitir busca por nome ou telefone e filtro por status e origem. A resposta SHALL apresentar os dados necessários para distinguir cada contato e seu status atual.

#### Scenario: Buscar por nome

- **WHEN** um usuário autenticado informa parte do nome
- **THEN** o sistema retorna contatos cujo nome corresponda à busca, sem exigir correspondência exata

#### Scenario: Buscar por telefone

- **WHEN** um usuário autenticado informa parte do telefone
- **THEN** o sistema retorna contatos cujo telefone normalizado corresponda à busca

#### Scenario: Filtrar contatos inativos

- **WHEN** um usuário autenticado solicita contatos inativos
- **THEN** o sistema retorna somente contatos desativados que o usuário está autorizado a consultar

### Requirement: Desativação sem exclusão

O sistema SHALL permitir a desativação lógica de um contato sem apagar permanentemente seu registro. Contatos inativos SHALL permanecer consultáveis pela equipe autorizada e SHALL deixar de aparecer na consulta padrão de contatos ativos. A reativação SHALL preservar o mesmo identificador.

#### Scenario: Desativar contato

- **WHEN** um usuário autorizado desativa um contato
- **THEN** o registro permanece armazenado com status inativo e não aparece na listagem ativa padrão

#### Scenario: Reativar contato

- **WHEN** um usuário autorizado reativa um contato inativo
- **THEN** o mesmo registro volta a aparecer na consulta de contatos ativos

#### Scenario: Tentar apagar contato

- **WHEN** a interface ou uma chamada direta tenta excluir permanentemente um contato
- **THEN** o backend rejeita a operação, pois a remoção física não faz parte do cadastro

### Requirement: Interface de clientes e contatos

O painel Reflex SHALL disponibilizar a usuários internos autorizados uma tela de clientes/contatos com listagem, busca, filtros e formulário de cadastro/edição. A interface SHALL apresentar estados de carregamento, erro, lista vazia, validação e submissão em andamento, sem substituir as validações e permissões do backend.

#### Scenario: Carregamento da listagem

- **WHEN** a tela solicita contatos ao backend
- **THEN** a interface apresenta estado de carregamento até receber uma resposta

#### Scenario: Nenhum contato encontrado

- **WHEN** não existem contatos para a busca ou filtro selecionado
- **THEN** a interface apresenta mensagem de lista vazia e uma ação para cadastrar o primeiro contato quando o usuário puder criar registros

#### Scenario: Falha ao carregar ou salvar

- **WHEN** a API rejeita ou não conclui uma solicitação
- **THEN** a interface informa a falha, preserva os dados editados ainda não confirmados e não exibe mensagem de sucesso

#### Scenario: Manter confirmação durante a navegação no menu

- **WHEN** uma operação de contato termina com sucesso e o usuário continua no menu de clientes e contatos
- **THEN** a mensagem de sucesso permanece visível até o usuário sair desse menu

#### Scenario: Acesso de usuário não autenticado

- **WHEN** uma pessoa sem sessão abre a rota de clientes/contatos
- **THEN** a interface redireciona para o login e não exibe dados da base
