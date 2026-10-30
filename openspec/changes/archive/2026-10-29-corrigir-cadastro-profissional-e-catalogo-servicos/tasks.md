# Tarefas

## 1. Corrigir cadastro de profissionais

- [x] 1.1 Consultar explicitamente o e-mail normalizado no Xano antes de criar a conta, mantendo a restrição única no banco.
- [x] 1.2 Preservar os campos em caso de falha e limpar o formulário apenas após confirmação de sucesso.
- [x] 1.3 Validar o cenário de e-mail inexistente e o cenário de e-mail duplicado.

## 2. Restaurar integração do catálogo de serviços

- [x] 2.1 Alinhar o identificador canônico do grupo `Services` ao `XANO_SERVICES_API_URL` sem alterar a autenticação dos endpoints.
- [x] 2.2 Validar listagem e cadastro de serviços com uma conta administradora.

## 3. Verificação

- [x] 3.1 Executar verificações de sintaxe e de OpenSpec e inspecionar o diff para confirmar que as alterações são restritas aos dois problemas.
- [x] 3.2 Registrar que a publicação e os testes autenticados do Xano remoto dependem de sincronização no ambiente da barbearia.
