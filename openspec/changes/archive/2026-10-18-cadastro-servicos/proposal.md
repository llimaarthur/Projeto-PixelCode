# Proposta: Cadastro de serviços

## Por quê

O PixelCode já estabelece a autenticação da equipe e a fundação visual do painel, mas ainda não possui um catálogo operacional de serviços. A equipe precisa manter em um só lugar os serviços oferecidos, seus preços e suas durações para preparar as próximas etapas de clientes e agendamentos.

## O que muda

- Criar um catálogo compartilhado de serviços para uma única barbearia, utilizado pelos profissionais da mesma equipe.
- Permitir que o administrador liste, cadastre, edite, ative e desative serviços.
- Registrar nome, descrição, preço, duração em minutos e status ativo/inativo, com validações no backend.
- Permitir que profissionais autenticados consultem apenas serviços ativos; aplicar todas as permissões no Xano.
- Adicionar ao painel Reflex a tela do catálogo, o formulário de cadastro/edição e os estados de carregamento, erro e lista vazia.
- Desativar serviços sem apagá-los, para preservar sua referência caso sejam usados por funcionalidades futuras.

## Limites

- O sistema atende uma única barbearia. Esta Change não cria suporte a várias barbearias, filiais, organizações, seleção de tenant ou isolamento multi-tenant.
- Clientes não acessam o sistema nem gerenciam o catálogo.
- Agenda, clientes, agendamentos, pagamentos e histórico de atendimentos permanecem fora desta Change.
- Esta Change não altera a regra já definida de preservar o preço de um serviço nos agendamentos existentes; a implementação de agendamentos continua em uma Change futura.

## Capabilities

### Novas capabilities

- `catalogo-servicos`: cadastro, consulta, edição, ativação e desativação do catálogo único de serviços da barbearia.

### Capabilities modificadas

Nenhuma. `openspec/specs/` ainda não contém capabilities publicadas.

## Impacto

- **Backend Xano:** persistência do catálogo, endpoints de consulta e gestão, validações e autorização por papel.
- **Frontend Reflex:** navegação e telas internas para listar e manter serviços, seguindo a fundação visual existente.
- **Dados:** um único catálogo compartilhado pela barbearia; não será adicionado identificador de barbearia ou mecanismo de isolamento entre tenants.
