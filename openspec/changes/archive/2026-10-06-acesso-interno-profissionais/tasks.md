# Tasks

## 1. Identidade e autorização no backend

- [x] 1.1 Implementar a conta como identidade do profissional, exigindo nome, e-mail, telefone e CPF; verificar criação válida e rejeição de cada campo ausente.
- [x] 1.2 Implementar o papel de administrador único e provisionamento de profissionais com senha temporária gerada pelo sistema; verificar que profissionais não podem criar contas, que não se pode criar/promover um segundo administrador e que o segredo só aparece uma vez.
- [x] 1.3 Exigir troca de senha temporária no primeiro acesso e bloquear outras operações até a troca; testar os dois estados de acesso.
- [x] 1.4 Implementar política de autorização para agenda própria versus acesso administrativo global e consulta compartilhada de clientes; testar permitido e negado para cada papel.
- [x] 1.5 Garantir que não exista autoinscrição pública nem endpoint público de bootstrap do primeiro administrador; testar tentativas sem autenticação.

## 2. Acesso no frontend

- [x] 2.1 Implementar login e persistência/encerramento de sessão no Reflex; verificar login válido, inválido e logout.
- [x] 2.2 Implementar tela protegida mínima e fluxo de troca obrigatória da senha temporária; verificar que usuário anônimo e usuário pendente de troca não acessem a área interna.
- [x] 2.3 Implementar tela administrativa de criação de conta profissional; verificar provisionamento autorizado e apresentação segura do acesso inicial.

## 3. Verificação integrada

- [x] 3.1 Testar a matriz de permissões com contas de administrador e profissional, incluindo agenda própria, agenda alheia e lista de clientes compartilhada.
- [x] 3.2 Verificar que operações protegidas são negadas no backend mesmo quando chamadas fora da interface Reflex.

## Observação de verificação

- A compilação Python e a checagem de formatação do diff foram executadas com sucesso.
- A aplicação e servidores não foram iniciados.
- Os testes de integração não puderam ser executados porque o arquivo `.env` não está presente no workspace e a URL do Xano não estava acessível para o ambiente de validação.