# Tasks

## 1. Status da agenda

- [x] 1.1 Definir no endpoint Xano as transições manuais permitidas, rejeitar estados terminais e devolver erro legível; verificar cada par permitido e rejeitado no artefato da API.
- [x] 1.2 Atualizar ações e estado da linha de agendamento após resposta confirmada, preservando o status salvo em falhas; executar os testes de agenda e compilar o Reflex.

## 2. Integridade e autorização financeira

- [x] 2.1 Adicionar campos opcionais de cliente, serviços, agendamento e status anterior às tabelas financeiras; verificar referências e compatibilidade com registros existentes.
- [x] 2.2 Validar autoria do estorno no Xano, permitir ADM em qualquer lançamento, gravar auditoria e restaurar o status do agendamento; validar os três cenários de autorização, o motivo obrigatório e a rejeição de duplicidade no endpoint.
- [x] 2.3 Implementar o registro financeiro com snapshots de cliente/serviços e vínculo opcional ao agendamento, concluindo o status no pagamento e restaurando-o no estorno; verificar referências inválidas e evitar pagamentos ativos duplicados por agendamento.

## 3. Formulário financeiro

- [x] 3.1 Carregar clientes cadastrados e serviços ativos, disponibilizar a lista de clientes para seleção, adicionar seleção múltipla de serviços e total calculado editável; verificar seleção de clientes e serviços, atualização do total e mensagens de validação.
- [x] 3.2 Persistir a movimentação com o usuário autenticado e vínculos selecionados, exibir erros da API e atualizar agenda/financeiro após sucesso; executar os testes financeiros e compilar o Reflex.

## 4. Lista financeira paginada

- [x] 4.1 Implementar endpoint Xano com filtro, ordenação e paginação de três registros, retornando total e página; verificar ordenação, filtro, offsets e última página incompleta.
- [x] 4.2 Conectar controles de página ao endpoint, preservar o filtro de estornadas e apresentar total, vazio e limites de navegação; executar os testes financeiros e compilar o Reflex.

## 5. Verificação integrada

- [x] 5.1 Validar a mudança OpenSpec e verificar o diff final; testar agenda, autoria de estorno, vínculo pagamento/estorno, seleção de clientes/serviços e paginação com a API Xano publicada ou registrar explicitamente a indisponibilidade desse ambiente. A API Xano publicada não estava disponível para testes integrados.
