# Proposta: Corrigir cadastro profissional e catálogo de serviços

## Por quê

O cadastro de profissionais rejeita endereços de e-mail que deveriam ser aceitos, e o catálogo de serviços não carrega nem permite salvar serviços. A investigação local identificou uma consulta de duplicidade no provisionamento que precisa ser explícita e uma divergência entre a URL configurada no frontend e a declaração do grupo `Services` no Xano.

## O que muda

- Consultar explicitamente a existência do e-mail normalizado antes de criar a conta, mantendo a restrição de unicidade no backend.
- Preservar os dados digitados quando o cadastro falhar e limpar o formulário somente depois de uma criação bem-sucedida.
- Alinhar o identificador canônico do grupo `Services` com a URL da API de serviços configurada para o frontend.
- Validar que as operações de listagem e cadastro do catálogo continuam protegidas por autenticação e autorização de administrador para escrita.

## Capacidades

### Novas capabilities

Nenhuma.

### Capabilities modificadas

- `acesso-interno-profissionais`: assegurar que a verificação de duplicidade compare o e-mail normalizado e que falhas no cadastro preservem os dados preenchidos.
- `catalogo-servicos`: assegurar que o frontend alcance o grupo correto do Xano para consultar e cadastrar serviços.

## Impacto

- Backend Xano: endpoint de criação de profissionais e declaração do grupo de APIs `Services`.
- Frontend Reflex: formulário de cadastro de profissionais, preservação dos dados em falhas e limpeza após sucesso.
- Integração: a URL `XANO_SERVICES_API_URL` deve identificar o mesmo grupo `Services` declarado no Xano; as rotas permanecem autenticadas.
