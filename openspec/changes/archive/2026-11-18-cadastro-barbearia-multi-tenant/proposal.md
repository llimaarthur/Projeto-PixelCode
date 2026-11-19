# Proposta: Cadastro de barbearia e isolamento multi-tenant

## Why

O PixelCode atualmente atende uma única barbearia: clientes, serviços,
agendamentos e dados financeiros são compartilhados no mesmo conjunto de
registros, e o cadastro público está desativado. Isso impede que uma nova
barbearia comece a usar o produto sem provisionamento manual e não oferece
isolamento para operar mais de uma organização.

## What Changes

- Permitir o cadastro público de uma barbearia e de sua primeira conta
  proprietária/administradora em um único fluxo.
- Associar cada conta interna e cada registro operacional a uma barbearia.
- Aplicar isolamento no backend a consultas, alterações, relações entre
  registros, listagens e agregados financeiros e de dashboard.
- Restringir o papel de administrador à própria barbearia; nenhum usuário de
  uma organização terá acesso administrativo global.
- Tratar os registros atuais sem vínculo explícito como pertencentes apenas à
  barbearia inicial, sem reescrever os dados; novos registros recebem o vínculo
  explícito da barbearia.

## Capabilities

### New Capabilities

- `cadastro-barbearia`: cadastro da organização, criação da conta proprietária
  e isolamento multi-tenant dos dados.

### Modified Capabilities

- `acesso-interno-profissionais`: papéis e equipe vinculados à barbearia.
- `clientes-contatos`: contatos isolados por barbearia.
- `catalogo-servicos`: catálogo isolado por barbearia.
- `agenda-agendamentos`: agendamentos e bloqueios restritos à barbearia.
- `financeiro`: ledger e referências financeiras restritos à barbearia.
- `visao-geral`: agregados restritos à barbearia da sessão.

## Impact

- Backend Xano: nova entidade de barbearia, vínculos e validações de autorização
  em todas as APIs de domínio, autenticação e agregação.
- Frontend Reflex: fluxo público de cadastro e tratamento do resultado; a
  interface não escolhe nem autoriza o tenant.
- Dados: compatibilidade lógica dos registros legados com a barbearia inicial,
  sem backfill em massa; e-mail de usuário continua único globalmente.
- Documentação do domínio e da visão geral do projeto: atualizar as premissas de
  barbearia única após a implementação.
- Fora do escopo: filiais, assinaturas/cobrança, portal do cliente, aprovação
  manual de novas barbearias e edição de dados cadastrais da barbearia após o
  cadastro.
