# Spec Delta

## MODIFIED Requirements

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
