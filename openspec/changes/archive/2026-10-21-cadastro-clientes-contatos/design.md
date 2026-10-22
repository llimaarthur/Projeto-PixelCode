# Design

## Contexto

Consulte `proposal.md` e a capability `clientes-contatos` desta Change. O PixelCode é um painel interno operado por administrador e profissionais de uma única barbearia. O cliente é um contato externo, sem acesso ao sistema. A autenticação existente identifica o usuário interno, e o Xano permanece responsável por persistência, validação e autorização.

## Goals / Non-Goals

**Goals:**

- Criar uma base compartilhada de clientes/contatos que possa ser usada posteriormente pela agenda.
- Permitir cadastro, edição, consulta, busca, filtros e desativação lógica.
- Manter telefone normalizado e único entre contatos ativos.
- Aplicar a mesma regra de acesso em chamadas diretas à API e na interface Reflex.
- Entregar uma tela responsiva consistente com a fundação visual já existente.

**Non-Goals:**

- Login ou portal do cliente.
- Multi-tenancy, filiais, importação em massa ou integrações com canais externos.
- Agenda, agendamento, pagamento, histórico de atendimento ou relatórios.
- Deduplicação automática por nome ou outros dados além do telefone normalizado.

## Decisões

### Entidade única para cliente e contato

Será criada uma entidade única de contato externo. O termo “cliente” descreve o uso comercial do registro, enquanto “contato” deixa explícito que a pessoa não é um usuário autenticado. Não haverá tabela de credenciais ou relação de conta de acesso.

Campos previstos:

- `id`: identificador do registro;
- `name`: nome obrigatório;
- `phone`: telefone obrigatório, armazenado normalizado;
- `source`: origem controlada, inicialmente `whatsapp`, `indicacao`, `instagram`, `ligacao` ou `outra`;
- `notes`: observações opcionais;
- `status`: `active` ou `inactive`;
- `first_contact_at`: data do primeiro contato;
- `created_at` e `updated_at`: datas de auditoria.

O status “recorrente” descrito no modelo conceitual não será tratado como status persistido nesta Change: recorrência deve ser derivada de atendimentos futuros, quando o histórico existir, para evitar que a equipe precise manter manualmente um estado calculado.

### Permissões

Administrador e profissionais autenticados poderão consultar, criar, editar, ativar e desativar contatos. Essa decisão mantém a base operacional útil para toda a equipe e não concede aos profissionais nenhuma capacidade nova sobre contas internas. O Xano deverá verificar autenticação e papel em cada endpoint; a interface apenas refletirá essas permissões.

### Telefone e duplicidade

O backend deverá remover caracteres de formatação e espaços para produzir o valor usado na comparação. A validação de duplicidade será aplicada somente a contatos ativos, permitindo reativar ou cadastrar novamente um telefone após a política de negócio decidir como tratar um registro inativo. A implementação deverá evitar que duas requisições concorrentes criem o mesmo telefone ativo, usando a garantia disponível no Xano para a restrição ou uma verificação transacional equivalente.

### Consulta e paginação

O endpoint de listagem deverá aceitar busca, status, origem, página e tamanho de página, com limites definidos pelo backend. A ordenação padrão será por nome normalizado e, como desempate, identificador. O frontend não deverá carregar todos os registros para filtrar localmente, pois a base crescerá com o uso da barbearia.

### Interface

A tela reutilizará a navegação interna, tokens visuais, mensagens e padrões de formulário já usados no catálogo de serviços.

- O cabeçalho exibirá título, descrição curta e ação “Novo cliente”.
- A área de filtros terá busca por nome/telefone, status e origem.
- A listagem exibirá nome, telefone, origem, data do primeiro contato e status.
- As ações de edição e ativação/desativação ficarão associadas ao próprio registro e serão operáveis por teclado.
- Em telas estreitas, filtros e ações serão reorganizados sem rolagem horizontal.
- Erros de API não serão convertidos em sucesso; o formulário manterá os valores não confirmados para correção ou nova tentativa.

### Integração futura com agenda

Esta Change deverá expor um identificador estável e dados básicos suficientes para uma futura Change de agendamentos. Ela não criará vínculo com serviços ou profissionais e não permitirá que um cliente inativo seja selecionado para um novo agendamento até que a regra da agenda seja especificada.

## Riscos / Trade-offs

- **Todos os usuários internos podem editar contatos**: reduz atrito operacional, mas exige auditoria futura caso a barbearia precise restringir alterações.
- **Unicidade apenas entre contatos ativos**: preserva registros históricos inativos, mas requer uma decisão explícita na reativação quando o telefone estiver ocupado por outro contato ativo.
- **Origem controlada por enumeração**: facilita filtros e relatórios, mas uma nova origem exigirá alteração coordenada no backend e no frontend.
- **Busca paginada no backend**: evita crescimento descontrolado no navegador, mas requer estados de paginação e tratamento de parâmetros inválidos.

## Plano de migração

1. Criar a estrutura de contatos no Xano sem alterar a tabela de usuários ou o catálogo de serviços.
2. Publicar endpoints autenticados para consulta, criação, edição e mudança de status.
3. Validar a matriz de permissões, normalização e duplicidade com chamadas diretas à API.
4. Integrar a tela Reflex à navegação existente e validar os estados de interação.
5. Em rollback, remover o acesso à tela e desabilitar os endpoints novos sem apagar contatos já cadastrados.
