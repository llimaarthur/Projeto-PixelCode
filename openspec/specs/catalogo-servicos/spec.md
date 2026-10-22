# Catálogo de serviços

## Purpose

Definir o catálogo compartilhado de serviços de uma única barbearia, suas regras de manutenção e consulta pela equipe interna.

## Requirements

### Requirement: Catálogo único da barbearia

O sistema SHALL manter um único catálogo de serviços compartilhado pelos profissionais da barbearia. O sistema SHALL atender somente uma barbearia e SHALL NOT exigir seleção de barbearia, filial, organização ou tenant para acessar o catálogo.

#### Scenario: Profissionais consultam o mesmo catálogo

- **WHEN** profissionais autenticados consultam o catálogo de serviços ativos
- **THEN** ambos recebem os serviços ativos do mesmo catálogo da barbearia

#### Scenario: Acesso sem tenant

- **WHEN** um profissional autenticado consulta ou administra serviços conforme seu papel
- **THEN** a operação não exige nem recebe um identificador de barbearia para selecionar outro catálogo

### Requirement: Cadastro e edição de serviços

O sistema SHALL permitir que o administrador cadastre e edite serviços com nome obrigatório, descrição opcional, preço decimal não negativo com até duas casas decimais, duração inteira positiva em minutos e status ativo ou inativo. Um serviço novo SHALL iniciar ativo. O backend SHALL validar os campos antes de persistir alterações.

#### Scenario: Cadastrar serviço válido

- **WHEN** o administrador envia nome, preço e duração válidos, com descrição opcional
- **THEN** o backend persiste o serviço como ativo no catálogo único e retorna seus dados atualizados

#### Scenario: Rejeitar dados inválidos

- **WHEN** o administrador envia nome vazio, preço negativo ou com mais de duas casas decimais, ou duração não inteira ou menor que um minuto
- **THEN** o backend rejeita a operação e informa os campos inválidos sem persistir o serviço

#### Scenario: Editar serviço existente

- **WHEN** o administrador altera os dados de um serviço existente com valores válidos
- **THEN** o backend atualiza o serviço e mantém o mesmo registro no catálogo

#### Scenario: Rejeitar edição por profissional

- **WHEN** um profissional tenta cadastrar ou editar um serviço
- **THEN** o backend nega a operação e não altera o catálogo

### Requirement: Consulta conforme o papel da equipe

O sistema SHALL autorizar no backend a consulta do catálogo. O administrador SHALL poder consultar serviços ativos e inativos; profissionais autenticados SHALL poder consultar somente serviços ativos.

#### Scenario: Administrador consulta serviços inativos

- **WHEN** o administrador solicita os serviços inativos
- **THEN** o backend retorna os serviços inativos do catálogo da barbearia

#### Scenario: Profissional consulta catálogo ativo

- **WHEN** um profissional autenticado consulta o catálogo
- **THEN** o backend retorna somente os serviços ativos

#### Scenario: Usuário não autenticado consulta catálogo

- **WHEN** uma pessoa sem sessão autenticada tenta consultar o catálogo
- **THEN** o backend nega a operação sem expor dados de serviços

### Requirement: Ativação e desativação sem exclusão

O sistema SHALL permitir ao administrador ativar e desativar serviços sem excluí-los permanentemente. Serviços desativados SHALL permanecer consultáveis pelo administrador e SHALL deixar de aparecer na consulta de catálogo feita por profissionais.

#### Scenario: Desativar serviço

- **WHEN** o administrador desativa um serviço ativo
- **THEN** o serviço permanece armazenado com status inativo e deixa de aparecer no catálogo consultado por profissionais

#### Scenario: Reativar serviço

- **WHEN** o administrador ativa novamente um serviço inativo
- **THEN** o serviço permanece no mesmo registro e volta a aparecer no catálogo consultado por profissionais

#### Scenario: Profissional tenta alterar status

- **WHEN** um profissional tenta ativar ou desativar um serviço
- **THEN** o backend nega a operação e mantém o status atual

### Requirement: Interface do catálogo no painel interno

O painel Reflex SHALL disponibilizar ao administrador a listagem e manutenção do catálogo e SHALL apresentar estados de carregamento, erro e lista vazia. A interface SHALL apresentar validações e feedback da API sem substituir as validações e permissões do backend. Mensagens de sucesso SHALL permanecer visíveis enquanto o usuário continuar no menu de serviços e SHALL ser limpas ao sair desse menu.

#### Scenario: Carregamento do catálogo

- **WHEN** a tela do catálogo solicita dados ao backend
- **THEN** a interface apresenta um estado de carregamento até receber uma resposta

#### Scenario: Catálogo sem serviços

- **WHEN** não existem serviços para o filtro selecionado
- **THEN** a interface apresenta uma mensagem de lista vazia e, para o administrador, uma ação para cadastrar o primeiro serviço

#### Scenario: Falha ao carregar ou salvar

- **WHEN** a API rejeita ou não conclui a solicitação
- **THEN** a interface informa a falha, mantém os dados editados ainda não confirmados e não apresenta mensagem de sucesso

#### Scenario: Profissional acessa a tela do catálogo

- **WHEN** um profissional autenticado abre o catálogo
- **THEN** a interface permite consultar os serviços ativos e não apresenta ações de cadastro, edição ou alteração de status

#### Scenario: Manter confirmação durante a navegação no menu

- **WHEN** uma operação de serviço termina com sucesso e o usuário continua no menu de serviços
- **THEN** a mensagem de sucesso permanece visível até o usuário sair desse menu
