# Design

## Contexto

Consulte `proposal.md` para a motivação e os limites. O PixelCode é um painel interno operado pelo administrador e pelos profissionais de uma única barbearia. A autenticação e as regras de negócio existentes ficam no Xano; a interface Reflex não é uma barreira de segurança.

A prévia conceitual da tela do catálogo está em `mockups/catalogo-servicos.svg`. Ela demonstra a aplicação da fundação visual existente e usa dados ilustrativos; não substitui os requisitos desta Change nem define conteúdo real do catálogo.

## Goals / Non-Goals

**Goals:**
- Entregar um catálogo compartilhado com operações de consulta, cadastro, edição, ativação e desativação.
- Validar os dados e autorizar cada operação no backend.
- Permitir ao administrador gerir serviços e aos profissionais consultar os serviços ativos.
- Expor o fluxo no painel Reflex com estados compreensíveis e feedback de validação.

**Non-Goals:**
- Suportar múltiplas barbearias, filiais, tenants ou catálogos independentes.
- Implementar agenda, clientes, agendamentos, pagamentos ou um portal para clientes.
- Apagar serviços permanentemente ou alterar dados de agendamentos existentes.
- Criar papéis ou alterar a matriz de permissões da equipe já estabelecida.

## Decisões

### Catálogo único, sem multi-tenancy

O sistema atende uma única barbearia. Todos os profissionais autenticados pertencem à mesma operação e consultam o mesmo catálogo. Esta Change não adiciona `barbearia_id`, seleção de organização, separação de dados por empresa ou qualquer fluxo de gestão de tenants. Uma eventual expansão para múltiplas barbearias exigirá uma decisão e uma Change próprias.

### Permissões por papel

O administrador pode consultar serviços ativos e inativos, cadastrar, editar, ativar e desativar serviços. Profissionais autenticados podem consultar serviços ativos, mas não podem alterá-los. O Xano deve verificar o papel em cada endpoint, independentemente da tela Reflex utilizada.

### Campos e validações

Cada serviço terá nome obrigatório, descrição opcional, preço decimal não negativo com até duas casas decimais, duração inteira positiva em minutos e status ativo/inativo. Textos devem ser normalizados sem espaços excedentes; valores inválidos devem ser rejeitados pelo Xano com erro explícito. Nomes não precisam ser únicos, permitindo variações de serviço com o mesmo nome.

### Desativação em vez de exclusão

Remover o serviço do catálogo será uma mudança de status, não uma exclusão permanente. Serviços inativos ficam fora da consulta de catálogo feita pelos profissionais, mas continuam consultáveis pelo administrador e poderão ser reativados. Isso evita eliminar registros que funcionalidades futuras possam referenciar.

### Interface de gestão

A tela Reflex será integrada à navegação interna existente e seguirá a fundação visual do projeto, reutilizando seus tokens e padrões de componentes em vez de criar uma identidade paralela.

- No desktop, manter a navegação lateral existente e apresentar título, breve descrição e ação primária “Novo serviço” na área de conteúdo. O botão deve permanecer dentro dos limites dessa área, com texto integralmente visível.
- Apresentar os serviços em uma superfície de catálogo com nome, descrição, preço, duração e status claramente associados. As ações de edição e mudança de status ficam disponíveis apenas ao administrador.
- Usar o padrão de formulário interno já adotado pelo painel para cadastro e edição, com rótulos visíveis, indicação de campos obrigatórios, erros junto aos campos e prevenção de envios duplicados.
- Em telas estreitas, reorganizar o cabeçalho e as informações do catálogo para caber na viewport, sem que botões ou textos transbordem e sem rolagem horizontal da página. Manter leitura e operação das ações sem depender de hover.
- Preservar foco visível, contraste, semântica dos controles e feedback de sucesso ou erro conforme os padrões existentes.
- Distinguir carregamento, erro, lista vazia, validação e submissão em andamento, sem apresentar sucesso quando a API falhar.

A imagem em `mockups/catalogo-servicos.svg` é uma referência visual conceitual, não um contrato de conteúdo. Os nomes, descrições, preços e contagens nela exibidos são dados ilustrativos e não devem ser codificados como dados reais ou métricas fixas. A busca deve filtrar por nome e descrição, o filtro de status deve funcionar conforme o papel e os controles de paginação devem navegar pelos resultados; não exibir controles decorativos ou sem ação.

## Riscos / Trade-offs

- **Uma única barbearia** → simplifica o domínio atual e corresponde ao escopo aprovado; uma expansão futura exigirá planejar isolamento de dados antes de atender outra empresa.
- **Profissionais com consulta somente de serviços ativos** → mantém o catálogo útil para operações futuras sem conceder escrita; qualquer mudança de permissão deve ser revista em uma Change própria.
- **Desativação em vez de exclusão** → mantém referências futuras íntegras, mas exige que a listagem administrativa diferencie serviços inativos.
- **Descrição opcional e nomes não únicos** → reduz atrito de cadastro e permite variações; a equipe poderá rever essas regras se surgir uma necessidade real de padronização.

## Plano de migração

1. Criar a estrutura de serviços no Xano sem alterar a tabela de usuários nem introduzir dados de tenant.
2. Publicar e validar os endpoints com contas de administrador e profissional.
3. Integrar a tela Reflex e testar os estados de consulta e submissão.
4. Em rollback, ocultar/desabilitar o acesso à tela e aos endpoints novos sem apagar serviços já cadastrados.
