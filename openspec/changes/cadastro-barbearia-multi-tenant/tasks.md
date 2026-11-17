# Tasks

## 1. Modelo de dados e migração

- [x] 1.1 Criar a entidade de barbearia e adicionar vínculos de tenant às contas,
  contatos, serviços, agendamentos, bloqueios, movimentações e revisões,
  preservando índices e relacionamentos existentes.
- [x] 1.2 Implementar a compatibilidade legada: registros nulos ficam acessíveis
  somente à barbearia inicial, sem atualizar as linhas existentes; gravações
  novas sempre recebem o tenant explícito.
- [ ] 1.3 Verificar a integridade de referências e totais antes/depois da
  migração e documentar o procedimento de rollback sem apagar dados.
- [x] 1.4 Atualizar a visão geral e o modelo de domínio para remover a premissa
  de barbearia única e registrar o isolamento por organização.

## 2. Cadastro da barbearia e proprietário

- [x] 2.1 Reativar o signup no Xano para validar nome da barbearia, nome do
  proprietário, e-mail, telefone e senha, normalizar campos e rejeitar e-mail
  e telefone globalmente duplicados.
- [x] 2.2 Criar barbearia e primeira conta `admin` no mesmo fluxo lógico,
  impedindo criação parcial e sem aceitar tenant, papel ou status do cliente;
  verificar que a resposta não expõe segredos.
- [x] 2.3 Implementar o formulário público Reflex com validação acessível,
  preservação dos dados em falhas, confirmação de sucesso e encaminhamento ao
  login existente.

## 3. Isolamento e autorização no backend

- [x] 3.1 Atualizar autenticação, perfil e autorização para associar cada
  usuário a exatamente uma barbearia e aplicar papéis administrativos somente
  dentro desse tenant.
- [x] 3.2 Revisar todas as APIs existentes de equipe, clientes, serviços,
  agenda, bloqueios, financeiro, auditoria e dashboard; derivar o tenant da
  sessão e aplicar o filtro em consultas, gravações, listagens e agregados.
- [x] 3.3 Validar que referências usadas em agendamentos e movimentações
  pertencem à mesma barbearia; rejeitar IDs de outro tenant em leitura e
  escrita sem revelar dados externos.

## 4. Verificação integrada

- [ ] 4.1 Testar signup válido, campos inválidos, e-mail duplicado, falha
  parcial, criação do primeiro administrador e login após o cadastro.
  - [x] Regressão do telefone: formatos mascarados, dígitos locais e DDI 55
    aceitos; símbolos, DDD inexistente e comprimentos inválidos rejeitados.
  - [x] Regressão do contrato Xano: senha bruta marcada como sensível para ser
    hasheada uma vez pelo campo `password`, e `migration_key` único no signup.
  - [x] Fluxo live sintético: cadastro e login aceitos com a mesma senha; a
    resposta do cadastro não expôs senha nem hash.
- [ ] 4.2 Testar isolamento entre duas barbearias em cada recurso, incluindo
  listagem paginada, dashboard/financeiro, equipe e referências cruzadas; testar
  chamadas diretas às APIs fora do Reflex.
- [ ] 4.3 Executar validação OpenSpec, testes direcionados e compilação do
  frontend; verificar a migração no Xano ou registrar explicitamente a
  indisponibilidade desse ambiente.

OpenSpec strict, 35 testes `unittest` e `compileall` passaram. O signup foi
publicado isoladamente no workspace 153819, branch live `v1`, e validado com
cadastro/login sintéticos; o cadastro não retornou senha nem hash. Permanecem
pendentes a integridade completa da migração, os demais cenários de signup e os
testes abrangentes de isolamento nas tarefas 1.3, 4.1, 4.2 e 4.3.
