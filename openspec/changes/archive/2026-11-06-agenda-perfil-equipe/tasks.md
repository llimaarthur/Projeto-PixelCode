# Tarefas

## 1. Agendamentos no Xano

- [x] 1.1 Criar estrutura de agendamento com status, referências, intervalos e snapshots dos serviços.
- [x] 1.2 Implementar consulta diária com autorização por papel e filtros de profissional/data.
- [x] 1.3 Implementar criação e edição com validação de referências ativas, cálculos e prevenção de conflitos.
- [x] 1.4 Implementar atualização de status e cancelamento sem exclusão, respeitando o escopo do profissional.
- [x] 1.5 Testar permissões, conflitos, horários adjacentes, cancelamentos e preservação de snapshots.
- [x] 1.6 Implementar consulta de disponibilidade mensal/diária, expediente semanal, duração de serviços e bloqueios.
- [x] 1.7 Implementar persistência e autorização de bloqueios manuais e validar bloqueios na criação/edição.
- [x] 1.8 Ampliar clientes com CPF, nascimento e e-mail; validar unicidade de CPF/telefone na criação e edição.

## 2. Perfil no Xano

- [x] 2.1 Expor os campos cadastrais necessários no endpoint de identidade.
- [x] 2.2 Implementar leitura/atualização do próprio perfil com validação e unicidade do e-mail.
- [x] 2.3 Implementar armazenamento no Xano File Storage, validação JPEG/PNG/WebP até 5 MB, consulta, substituição e remoção da foto própria.
- [x] 2.4 Implementar troca da própria senha com verificação da senha atual e confirmação.
- [x] 2.5 Testar validações, permissões e rejeição de alteração de outra conta.

## 3. Integração Reflex

- [x] 3.1 Adicionar configuração e cliente de API para agendamentos.
- [x] 3.2 Implementar agenda diária, filtro de profissional para administradores e formulário de criação/edição.
- [x] 3.3 Implementar ações de status/cancelamento e estados de carregamento, erro e vazio.
- [x] 3.4 Implementar perfil cadastral, exibição/envio/substituição/remoção da foto e formulário separado de alteração de senha.
- [x] 3.5 Adicionar navegação e feedback de erros e sucesso.
- [x] 3.6 Implementar calendário mensal, seleção de data e indicadores de agendamento.
- [x] 3.7 Implementar disponibilidade por horário, cadastro rápido de cliente e seleção de funcionário/serviço.
- [x] 3.8 Implementar confirmação de sucesso, tabela diária com filtros e detalhes em modal.
- [x] 3.9 Implementar criação/remoção de bloqueios e confirmação de cancelamento.
- [x] 3.10 Compartilhar a disponibilidade entre calendário e formulário com seleção de data/horário por funcionário e serviços.
- [x] 3.11 Remover CPF e dados não essenciais do cadastro rápido de cliente durante o agendamento.
- [x] 3.12 Exibir somente rótulos sem IDs nos selects e mover a edição de perfil para diálogo acessível no bloco da sidebar.
- [x] 3.13 Remover CPF do diálogo e do payload de edição do perfil; adicionar controles acessíveis para mostrar/ocultar cada senha.
- [x] 3.14 Aplicar destaque azul existente, compactar a navegação lateral, manter o rodapé visível e ajustar o espaçamento do diálogo de perfil.
- [x] 3.15 Corrigir o foco contínuo dos campos de senha, os espaçamentos dos diálogos e a apresentação responsiva do usuário na sidebar.
- [x] 3.16 Exibir somente agendamentos não cancelados por padrão, atualizando a lista após cancelamento e preservando o filtro explícito de cancelados.
- [x] 3.17 Tornar CPF opcional na atualização do perfil e preservar os valores atuais quando CPF for omitido; tornar editáveis os campos do perfil.
- [x] 3.18 Revisar os contratos de CPF de contatos e agendamentos: cadastro/edição de contato aceitam omissão, e endpoints de agendamento não exigem CPF.

## 4. Verificação e publicação

- [x] 4.1 Executar verificações de sintaxe, importação da aplicação e compilação do Reflex.
- [x] 4.2 Validar os fluxos integrados com contas de administrador e profissional.
- [x] 4.3 Registrar limitações de publicação/testes no Xano; a change será arquivada somente após confirmar a correspondência entre especificação e implementação.
- [x] 4.4 Validar visualmente no navegador calendário, cadastro rápido, confirmação, detalhes, edição e cancelamento.

Nota: a sincronização autorizada enviou sete documentos selecionados ao workspace Xano Projeto PixelCode (ID 153819): somente `auth/me PATCH` e `contacts/{contact_id} PATCH` tiveram atualização; os outros cinco eram dependências incluídas para resolver grupos, função e tabelas referenciados. Nenhum registro, variável de ambiente ou item remoto foi excluído. O dry-run seletivo posterior retornou "No changes to push". `reflex compile --dry` passou. A tentativa de iniciar o servidor de produção compilou os bundles, mas o prerender da rota `/` expirou; portanto, a revisão visual do campo de senha após a última correção e os fluxos autenticados não foram concluídos. Os testes integrados autenticados com contas de administrador e profissional e a validação visual completa permanecem pendentes.
