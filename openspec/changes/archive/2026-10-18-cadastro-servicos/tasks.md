# Tarefas

## 1. Catálogo e autorização no backend

- [x] 1.1 Criar a estrutura de serviços no Xano com nome, descrição, preço, duração e status, sem identificador de barbearia ou tenant.
- [x] 1.2 Implementar consulta do catálogo para administrador e profissionais, aplicando os filtros de status autorizados para cada papel.
- [x] 1.3 Implementar cadastro e edição de serviços exclusivos ao administrador, com validações de nome, preço e duração no backend.
- [x] 1.4 Implementar ativação e desativação sem exclusão permanente; rejeitar alterações de status feitas por profissionais.
- [x] 1.5 Testar endpoints com chamadas autenticadas e não autenticadas, cobrindo permissões, dados válidos e rejeição de dados inválidos.

## 2. Gestão do catálogo no painel

- [x] 2.1 Adicionar acesso ao catálogo na navegação interna e implementar a listagem seguindo os padrões visuais existentes.
- [x] 2.2 Implementar formulário Reflex para cadastrar e editar serviços, exibindo validações retornadas pelo backend.
- [x] 2.3 Implementar ações de ativação e desativação para o administrador e consulta somente leitura para profissionais.
- [x] 2.4 Implementar estados de carregamento, erro, lista vazia, validação e submissão em andamento.
- [x] 2.5 Verificar a aplicação da fundação visual em telas amplas e estreitas, incluindo foco visível, leitura das ações sem hover e ausência de transbordamento de texto ou rolagem horizontal da página.

## 3. Verificação integrada

- [x] 3.1 Validar o fluxo de consulta, cadastro, edição e mudança de status com contas de administrador e profissional.
- [x] 3.2 Verificar que chamadas diretas à API respeitam as mesmas permissões, sem depender dos controles da interface.
- [x] 3.3 Executar as verificações disponíveis do frontend e registrar limitações de acesso ao ambiente Xano.

## Observações de verificação

- A sintaxe Python do estado Reflex foi validada com `py_compile`.
- `reflex export --frontend-only --no-ssr --no-zip` compilou o frontend; em uma execução posterior os bundles client/server também foram compilados, mas o prerender falhou por timeout ao solicitar a rota `/`.
- Os endpoints do Xano foram publicados e testados com chamadas autenticadas e não autenticadas, incluindo permissões de administrador e profissional, dados válidos e rejeição de dados inválidos.
- O fluxo integrado foi validado com contas reais de administrador e profissional: consulta, cadastro, edição, ativação/desativação e visualização somente leitura de serviços.
- A correção da comunicação entre Reflex e Xano foi validada após alinhar a URL do grupo Services e reiniciar a aplicação com uma instância atualizada.
