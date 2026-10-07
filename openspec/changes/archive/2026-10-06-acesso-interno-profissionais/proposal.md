# Proposta: Acesso interno dos profissionais

## Why

O PixelCode será usado por vários profissionais da barbearia, mas o domínio define o cliente como contato externo sem acesso ao sistema. É necessário estabelecer uma identidade e permissões internas antes de expor as funcionalidades de gestão, evitando cadastro público e acesso indevido a dados da equipe.

## What Changes

- Disponibilizar autenticação apenas para contas internas provisionadas pela barbearia.
- Fazer cada conta representar um profissional, inclusive a conta administradora.
- Permitir que o único administrador crie contas de profissionais pela aplicação, exigindo nome, e-mail, telefone e CPF e usando uma senha temporária gerada pelo sistema, exibida uma única vez e com troca obrigatória no primeiro acesso.
- Exigir que a primeira conta administradora seja provisionada diretamente no Xano, sem fluxo público de bootstrap.
- Aplicar autorização no backend: o administrador pode gerenciar a equipe e consultar dados operacionais de todos os profissionais; cada profissional acessa a própria agenda e os atendimentos associados.
- Permitir que todos os profissionais consultem a lista compartilhada de clientes da barbearia.
- Fornecer no Reflex a entrada autenticada e uma área protegida mínima para os usuários internos.

## Capabilities

### New Capabilities

- `acesso-interno-profissionais`: autenticação, provisionamento de contas profissionais, papéis e limites de autorização para a equipe.

### Modified Capabilities

Nenhuma. `openspec/specs/` não contém capabilities existentes.

## Impact

- Backend Xano: identidade da equipe, credenciais, papéis, provisionamento e autorização das operações protegidas.
- Frontend Reflex: formulário de acesso, troca da senha temporária e área interna protegida.
- Dados: a identidade autenticável também representa o profissional; não se propõe uma entidade de funcionário separada nesta primeira Change.
- Há exatamente uma conta com papel de administrador; ela também possui agenda própria como profissional.
- Ficam fora desta Change as APIs e telas funcionais de clientes, catálogo, agenda e pagamentos. As regras de autorização definidas aqui deverão ser aplicadas quando essas capabilities forem implementadas.