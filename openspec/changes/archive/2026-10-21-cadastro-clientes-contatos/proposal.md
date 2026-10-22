# Proposta: Cadastro de clientes e contatos

## Por quê

O PixelCode já possui autenticação da equipe e catálogo de serviços, mas ainda não tem uma base centralizada para registrar as pessoas atendidas pela barbearia. Sem esse cadastro, a equipe não consegue preparar agendamentos de forma confiável nem consultar o relacionamento anterior com um cliente.

## O que muda

- Criar um cadastro compartilhado de clientes/contatos para uma única barbearia.
- Permitir que administrador e profissionais autenticados consultem, criem e editem contatos conforme a política de acesso da equipe.
- Registrar nome, telefone, origem do contato, observações, status e data do primeiro contato.
- Permitir busca por nome e telefone e filtros por status e origem.
- Preservar contatos por desativação lógica, sem exclusão permanente.
- Adicionar ao painel Reflex uma tela de listagem, formulário de cadastro/edição e estados de carregamento, erro e lista vazia.
- Validar no formulário o telefone brasileiro e os campos obrigatórios, exibindo mensagens específicas sem perder os dados preenchidos.
- Retornar os dados de identidade no login para que o menu da equipe apareça imediatamente após a autenticação.
- Aplicar máscara e limite de dígitos nos campos de telefone e CPF do cadastro de profissionais.
- Validar os dados e aplicar as permissões no backend Xano, independentemente dos controles da interface.

## Limites

- O sistema continua atendendo uma única barbearia; esta Change não cria suporte a filiais, organizações, tenants ou seleção de barbearia.
- Clientes continuam sendo contatos externos e não recebem login, senha ou acesso ao painel.
- Esta Change não implementa agenda, agendamentos, pagamentos ou histórico de atendimentos; ela apenas prepara a entidade cliente para esses fluxos.
- Não haverá exclusão física de contatos.
- Não haverá importação em massa, integração com WhatsApp/Instagram ou deduplicação automática avançada.
- Profissionais não poderão administrar usuários internos nem alterar as regras de autorização existentes.

## Capabilities

### Novas capabilities

- `clientes-contatos`: cadastro, consulta, edição, busca e desativação de clientes/contatos da barbearia.

### Capabilities modificadas

- `catalogo-servicos`: nenhuma alteração funcional.
- `acesso-interno-profissionais`: retornar papel e nome no login para renderizar imediatamente a navegação autorizada.

## Impacto

- **Backend Xano:** nova estrutura de clientes/contatos, endpoints protegidos, validações e autorização por papel.
- **Frontend Reflex:** nova tela interna integrada à navegação existente, formulário e estados de feedback.
- **Dados:** novos contatos serão compartilhados pela equipe da única barbearia e ficarão disponíveis como referência para uma futura Change de agendamentos.
