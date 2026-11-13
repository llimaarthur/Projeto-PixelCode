# Design

## Context

Consulte `proposal.md` e as especificações em `specs/`. A aplicação mantém
estado de navegação no `AuthState`; Xano concentra persistência e autorização.
O endpoint do dashboard atualmente retorna o ledger completo, do qual o
frontend deriva os indicadores.

## Goals / Non-Goals

**Goals:**
- Aplicar as transições e autorizações no backend e refletir respostas
  persistidas no estado Reflex.
- Manter os indicadores calculados sobre o ledger completo, sem limitar os
  dados usados nos agregados quando a lista visível for paginada.
- Preservar dados existentes e associar snapshots de cliente/serviços e status
  anterior ao pagamento sem depender dos preços futuros do catálogo.

**Non-Goals:**
- Migrar dados antigos para clientes, serviços ou agendamentos retroativos.
- Criar conciliação bancária, pagamentos parciais ou exclusão física.
- Alterar a política de edição de lançamentos além de preservar seus vínculos.

## Decisions

### Transições da agenda

O endpoint de status validará, em cada requisição, a origem e o destino:
pendente pode ir para confirmado ou cancelado; confirmado pode ir para
concluído ou cancelado; concluído e cancelado são terminais para alterações
manuais. A exceção de negócio é o endpoint de criação de receita vinculada:
um pagamento explícito pode levar pendente ou confirmado a concluído e salvar
o estado original no lançamento. O cancelamento desse lançamento restaura o
estado registrado. A interface mantém as ações existentes na linha e atualiza
seu estado a partir da resposta/consulta confirmada, sem mutação otimista em
caso de falha.

### Registro vinculado

`finance_transaction` receberá campos opcionais `contact_id`, `services_snapshot`,
`appointment_id` e `appointment_status_before_payment`; os campos permanecem
opcionais para compatibilidade com despesas, lançamentos antigos e receitas
sem serviço. O endpoint POST validará clientes e serviços ativos e criará
snapshots de preço/nome. Um agendamento associado deve pertencer ao cliente
selecionado e estar pendente ou confirmado; um pagamento ativo já associado ao
mesmo agendamento será rejeitado para evitar dois pagamentos que disputem a
restauração do status. O total enviado continua editável e é validado como
positivo e com até duas casas decimais.

O formulário carregará clientes por páginas da API de contatos, serviços
ativos pelo catálogo e, quando houver cliente selecionado, opções de agenda
pendentes/confirmadas por um endpoint financeiro próprio. Um campo de busca
filtrará clientes carregados; o seletor de serviços adicionará/removerá
serviços e atualizará o valor. A vinculação a agendamento é opcional para
preservar receitas sem agendamento. As opções e alterações vinculadas respeitam
o escopo profissional existente: profissionais acessam a própria agenda e
administradores podem acessar qualquer profissional.

### Autorização e trilha de estorno

O endpoint de estorno continuará exigindo perfil profissional ou superior,
buscará o autor e o papel autenticado no backend e só prosseguirá se o papel
for `admin` ou `created_by` corresponder ao usuário autenticado. O status ativo
e o motivo válido serão verificados antes de gravar revisão e cancelamento.
Quando houver agendamento, a mesma operação restaurará o status anterior
salvo. `finance_transaction_revision` registrará o vínculo revertido junto
com autor, data, motivo e dados anteriores; as colunas existentes de
cancelamento também manterão esses metadados. O endpoint já rejeita lançamentos
cancelados; a validação de estado continuará sendo a defesa contra repetição
sequencial.

### Paginação e agregados

Um GET de movimentações separado aceitará página, tamanho fixo de três e
inclusão de estornadas. Ordenará por data decrescente e id decrescente,
aplicará filtro e offset no Xano antes de responder itens e total. A tela
preservará o filtro ao avançar/voltar e exibirá total e página. A consulta
completa do dashboard continuará alimentando os agregados, enquanto o novo GET
alimentará somente a lista; assim a paginação não distorce KPIs, fluxo de
caixa ou saldo.

### Contratos e compatibilidade

O formulário antigo continuará criando despesas e movimentações genéricas.
Vínculos e snapshots serão opcionais no esquema, então registros existentes
continuam legíveis. As APIs novas e alteradas reutilizarão autenticação,
autorização de profissional, `_request` e os grupos Xano já configurados; não
serão adicionadas dependências.

## Risks / Trade-offs

- [O Xano pode não oferecer transação atômica entre revisão, lançamento e
  agendamento] → manter validações antes das escritas, atualizar os registros
  no mesmo endpoint e verificar a ordem/contrato dos blocos no artefato Xano;
  implantação deverá ser testada na API antes de liberar o fluxo.
- [O endpoint do dashboard ainda carrega todos os lançamentos para calcular
  indicadores] → a paginação reduz a lista renderizada, mas não o payload de
  agregação; mover agregados para o backend fica fora desta mudança.
- [Listas grandes aumentam consultas de clientes no formulário] → usar páginas
  de até 50 itens e interromper com erro explícito se uma página falhar.
- [Um estorno simultâneo pode competir com outra requisição] → validar estado
  ativo no servidor antes da escrita e rejeitar qualquer requisição posterior
  ao primeiro estorno; testar repetição e autorização na API.

## Migration Plan

1. Importar os campos opcionais nas tabelas Xano e publicar os endpoints de
   status, registro, opções, listagem paginada e estorno.
2. Atualizar o frontend e verificar com APIs configuradas: registro, paginação,
   permissões, estorno e restauração de status.
3. Rollback: reverter o frontend e os endpoints para os contratos anteriores;
   manter as novas colunas opcionais, que não afetam lançamentos existentes.

## Open Questions

Nenhuma.
