# Tarefas

## 1. Modelo, validação e autorização no backend

- [x] 1.1 Criar no Xano a estrutura compartilhada de clientes/contatos com nome, telefone, origem, observações, status, primeiro contato e datas de auditoria, sem identificador de barbearia ou tenant.
- [x] 1.2 Implementar normalização de telefone e textos, com validação de campos obrigatórios, origem permitida, limites de tamanho e data do primeiro contato.
- [x] 1.3 Implementar unicidade de telefone normalizado entre contatos ativos, incluindo o caso de edição do próprio registro e concorrência conforme as garantias disponíveis no Xano. Validado pela usuária, inclusive para tentativas simultâneas.
- [x] 1.4 Implementar consulta autenticada com busca por nome/telefone, filtros de status/origem, ordenação estável e paginação limitada.
- [x] 1.5 Implementar criação e edição autenticadas para administrador e profissionais, com mensagens de validação sem persistir entradas inválidas.
- [x] 1.6 Implementar ativação e desativação lógica, rejeitar exclusão física e garantir que chamadas não autenticadas sejam negadas.

## 2. Gestão de clientes e contatos no painel

- [x] 2.1 Adicionar a rota e o acesso de clientes/contatos à navegação interna existente, preservando as proteções de sessão.
- [x] 2.2 Implementar listagem Reflex com busca, filtros, paginação e apresentação de nome, telefone, origem, primeiro contato e status.
- [x] 2.3 Implementar formulário de criação e edição com rótulos visíveis, validação de entrada, indicação de campos obrigatórios e prevenção de envios duplicados.
- [x] 2.4 Implementar ações de ativação e desativação lógica com confirmação e feedback explícito de sucesso ou falha.
- [x] 2.5 Implementar estados de carregamento, erro, lista vazia, formulário inválido, submissão em andamento e preservação dos dados não confirmados.
- [x] 2.6 Verificar responsividade em telas estreitas e amplas, foco visível, operação por teclado, contraste e ausência de rolagem horizontal.
- [x] 2.7 Validar telefone brasileiro e campos do formulário, normalizando o telefone e apresentando mensagens específicas.
- [x] 2.8 Publicar a resposta atualizada de login no Xano para a navegação autorizada aparecer imediatamente.
- [x] 2.9 Corrigir a validação do telefone celular no formulário e remover a regex redundante da validação Xano após normalizar os dígitos.
- [x] 2.10 Aplicar formatação progressiva do DDD e do hífen no campo de telefone durante a digitação.
- [x] 2.11 Limitar telefones a 11 dígitos, aplicar a máscara compartilhada no cadastro de profissionais, formatar CPF e exigir os 11 dígitos no envio.
- [x] 2.12 Corrigir a listagem de contatos para aplicar filtros opcionais após a consulta geral, sem ocultar contatos recém-criados.
- [x] 2.13 Interpretar data de contato em formatos ISO e timestamp Unix para evitar rejeição dos itens na listagem.
- [x] 2.14 Manter as mensagens de sucesso de serviços e clientes enquanto o usuário permanecer no respectivo menu e limpá-las ao sair.

## 3. Verificação integrada

- [x] 3.1 Testar endpoints com administrador, profissional e usuário não autenticado, cobrindo consulta, criação, edição, filtros, paginação e mudança de status. Cenários confirmados pela usuária.
- [x] 3.2 Testar rejeição de nome/telefone/origem inválidos, telefone duplicado, exclusão física e parâmetros de consulta inválidos. Cenários confirmados pela usuária.
- [x] 3.3 Validar que nenhum contato recebe credencial ou pode acessar a plataforma como usuário. Cenário confirmado pela usuária.
- [x] 3.4 Validar o fluxo integrado no Reflex com dados reais de teste, incluindo falhas de API, nova tentativa e atualização da listagem. Cenários confirmados pela usuária.
- [x] 3.5 Executar compilação e verificações disponíveis do frontend e registrar limitações de acesso ao ambiente Xano. Backend publicado no workspace Xano; rota protegida validada com resposta 401 sem autenticação. Testes autenticados e validação visual com dados reais confirmados pela usuária.
- [x] 3.6 Testar a normalização e rejeição de telefones válidos e inválidos e compilar o frontend após a alteração.
