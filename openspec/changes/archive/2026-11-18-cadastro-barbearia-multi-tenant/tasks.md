# Tasks

## 1. Modelo de dados e migração

- [x] 1.1 Criar a entidade de barbearia e adicionar vínculos de tenant às contas,
  contatos, serviços, agendamentos, bloqueios, movimentações e revisões,
  preservando índices e relacionamentos existentes.
- [x] 1.2 Implementar a compatibilidade legada: registros nulos ficam acessíveis
  somente à barbearia inicial, sem atualizar as linhas existentes; gravações
  novas sempre recebem o tenant explícito.
- [x] 1.3 Verificar a integridade de referências e totais antes/depois da
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
  preservação dos dados em falhas, autenticação automática após o cadastro e
  encaminhamento à área da aplicação.

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

- [x] 4.1 Testar signup válido, campos inválidos, e-mail duplicado, falha
  parcial, criação do primeiro administrador e login após o cadastro.
  - [x] Regressão do telefone: formatos mascarados, dígitos locais e DDI 55
    aceitos; símbolos, DDD inexistente e comprimentos inválidos rejeitados.
  - [x] Regressão do contrato Xano: senha bruta marcada como sensível para ser
    hasheada uma vez pelo campo `password`, e `migration_key` único no signup.
  - [x] Fluxo live sintético: cadastro e login aceitos com a mesma senha; a
    resposta do cadastro não expôs senha nem hash.
- [x] 4.2 Testar isolamento entre duas barbearias em cada recurso, incluindo
  listagem paginada, dashboard/financeiro, equipe e referências cruzadas; testar
  chamadas diretas às APIs fora do Reflex.
  - [x] Validar manualmente que dois profissionais de barbearias diferentes
    veem somente a equipe do próprio tenant.
- [x] 4.3 Executar validação OpenSpec, testes direcionados e compilação do
  frontend; verificar a migração no Xano ou registrar explicitamente a
  indisponibilidade desse ambiente.
  - [x] Liberar leitura da equipe para profissionais mantendo a listagem
    limitada ao tenant e as mutações protegidas para `admin`.
  - [x] Reutilizar o campo de senha com alternância acessível de visibilidade.
  - [x] Limpar a mensagem de cadastro ao navegar para fora da tela de login.
  - [x] Carregar e exibir o nome do tenant no shell e no título da página.
  - [x] Executar os testes automatizados da suíte e `compileall`.
  - [x] Executar `reflex compile --dry` após reparar o frontend gerado pelo Bun.
  - [x] Publicar as alterações de permissão e do nome legado no Xano live;
    pull da branch `v1` confirmou os documentos e o dry-run seguinte não mostrou
    mudanças pendentes.
  - [x] Limpar avisos antigos da agenda e descartar opções da sessão anterior
    antes de carregar os dados do profissional atual.
  - [x] Reutilizar o endpoint da equipe para carregar profissionais no
    agendamento e limitar a seleção do profissional à conta autenticada.
  - [x] Exibir agendamentos futuros confirmados na Visão geral e atualizar a
    lista após mudanças de status.
  - [x] Registrar no financeiro a receita vinculada ao cliente e ao agendamento
    ao concluir um atendimento com valor positivo.
  - [x] Adicionar testes direcionados para mensagens, agenda confirmada e
    conclusão com receita; validar a suíte completa e `compileall`.
  - [x] Revalidar `reflex compile --dry` após substituir o executável React
    Router bloqueado em `.web`; compilação concluída com sucesso.

OpenSpec strict, 73 testes `unittest`, `compileall` e `reflex compile --dry`
passaram. O signup foi
publicado isoladamente no workspace 153819, branch live `v1`, e validado com
cadastro/login sintéticos; o cadastro não retornou senha nem hash.
O usuário confirmou em 18/11/2026 que a aplicação está funcionando e solicitou
o encerramento das tasks restantes; os itens de integração e isolamento foram
marcados como concluídos com base nessa confirmação.

## 5. Carteira de clientes e expediente

- [x] 5.1 Atribuir contatos a profissionais no backend, restringir consultas,
  mutações e uso em agendamentos à carteira própria e permitir atribuição
  administrativa dentro do tenant.
- [x] 5.2 Configurar expediente semanal compartilhado por barbearia, com
  múltiplos intervalos por dia, leitura pela equipe e validação no backend para
  agendamentos e bloqueios.
- [x] 5.3 Validar o funcionamento integrado com usuários de duas barbearias.
  - [x] Adicionar cobertura automatizada para ownership, permissões e
    configuração semanal do expediente.
  - [x] Evitar logout em falhas temporárias ao validar a sessão e reconciliar
    cadastros de profissionais cuja resposta da API não chegou ao frontend.
  - [x] Permitir configurar expediente ainda não inicializado e ler horários
    serializados como JSON; manter a edição disponível com uma semana fechada
    quando a API devolver uma configuração inválida e limpar avisos antigos
    depois de salvar com sucesso.
  - [x] Validar novos agendamentos contra o expediente configurado pela
    barbearia, removendo a referência ao expediente estático inexistente.
  - [x] Adicionar ação explícita de pausa por dia, com padrão 12:00–13:00
    editável; salvar a pausa como intervalo sem atendimento no expediente.
  - [x] Inicializar novas barbearias com a semana fechada e permitir dias sem
    intervalos (folgas) ao salvar o expediente.
  - [x] Tratar expediente ausente ou vazio como semana fechada e atualizar a
    agenda imediatamente após salvar os horários.
  - [x] Publicar as alterações no workspace 153819, branch live `v1`, e
    confirmar que não há mudanças locais pendentes para push.
  - [x] Publicar os filtros de carteira da agenda no workspace 153819, branch
    live `v1`; o pull confirmou os cinco documentos e o dry-run não apontou
    mudanças pendentes.
  - [x] Testar manualmente com usuários de duas barbearias e confirmar o
    isolamento dos clientes e o expediente compartilhado.
