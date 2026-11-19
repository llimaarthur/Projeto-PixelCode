# Design

## Context

O Xano contém uma tabela `user` com papéis `admin` e `professional`, mas não há
entidade de barbearia nem vínculo de tenant. As tabelas `contact`, `service`,
`appointment`, `schedule_block` e `finance_transaction` são compartilhadas.
O endpoint público de signup está desativado. Consulte `proposal.md` e as
capabilities atuais para os contratos de domínio que devem ser preservados.

## Goals / Non-Goals

**Goals:**

- Permitir que uma barbearia e sua conta proprietária sejam criadas sem
  provisionamento manual.
- Impedir que usuários de uma barbearia leiam ou alterem dados de outra,
  inclusive por chamadas diretas às APIs.
- Preservar todos os dados e relacionamentos já existentes sem exigir uma
  atualização em massa antes de habilitar o cadastro.
- Restringir a carteira de clientes por profissional e permitir expediente
  semanal compartilhado configurado pelo administrador.

**Non-Goals:**

- Implementar filiais ou hierarquia de organizações.
- Criar cobrança, planos, aprovação manual ou portal para clientes.
- Alterar as regras do catálogo de serviços ou o comportamento dos relatórios
  financeiros compartilhados.
- Permitir que o frontend escolha o identificador da barbearia que autoriza
  uma operação.

## Decisions

### A barbearia é a raiz de isolamento

Criar uma entidade `barbershop` com identificador e nome. A inscrição recebe
nome da barbearia e dados do proprietário (nome, e-mail, telefone e senha).
Não adicionar dados de filial ou informações comerciais opcionais sem requisito
aprovado. Cada usuário interno passa a pertencer a exatamente uma barbearia.

As tabelas operacionais `contact`, `service`, `appointment`, `schedule_block`
e `finance_transaction` recebem uma referência opcional à barbearia, assim como
`finance_transaction_revision` e `event_log`. Todos os registros novos são
gravados com vínculo explícito. Registros existentes sem vínculo permanecem
inalterados e são tratados como dados da barbearia inicial somente.

### Compatibilidade lógica para dados legados

A barbearia inicial é identificada por `migration_key = "legacy-default"` e
`legacy_compatibility = true`. Uma conta autenticada dessa barbearia pode
consultar registros com `barbershop_id` igual ao seu tenant e registros com
`barbershop_id` nulo. Nenhuma outra barbearia pode consultar ou usar registros
nulos. O backend deriva esse sinalizador da barbearia associada à conta; o
cliente não pode ativá-lo. Toda gravação nova deve definir `barbershop_id`
explicitamente, inclusive para membros novos da barbearia inicial.

No primeiro login de uma conta administradora legada sem barbearia, o backend
cria a entidade inicial se ela ainda não existir. Esse bootstrap cria somente
um registro `barbershop`; não altera contas nem dados operacionais existentes.

### O tenant é derivado da sessão autenticada

Cada API protegida obtém a barbearia da conta autenticada no Xano. Parâmetros
de tenant enviados pelo cliente não selecionam nem ampliam o escopo. Toda
consulta, mutação, paginação, contagem, exportação interna existente e agregado
deve filtrar pela barbearia da sessão. Referências entre registros (por
exemplo, agendamento, contato, profissional e movimentação) só são válidas
quando pertencem à mesma barbearia. Uma tentativa com ID de outro tenant é
rejeitada sem revelar seus dados.

O papel `admin` concede gestão da equipe e dados somente dentro da própria
barbearia. Profissionais podem consultar a lista da equipe da própria
barbearia em modo somente leitura; operações de criação e manutenção de membros
continuam restritas a `admin`. As demais permissões profissionais continuam
limitadas ao tenant. A restrição atual de um administrador global é substituída
por administradores locais; não existe papel de suporte global nesta Change.

### Carteira de clientes por profissional

Adicionar `professional_id` opcional aos contatos. O administrador pode manter
contatos sem responsável ou atribuí-los a um profissional ativo da mesma
barbearia. A listagem padrão e as mutações de contato de um profissional são
restritas aos registros atribuídos ao próprio usuário; novos contatos criados
por profissionais recebem essa atribuição no backend. Contatos legados e
criados por administradores sem atribuição permanecem administrativos.

O fluxo de agendamento permanece mais amplo: administradores e profissionais
podem selecionar contatos ativos do próprio tenant para compromissos de agendas
que podem gerir, sem que isso permita alterar o cadastro do contato. Movimentações
vinculadas a um contato são criadas, editadas ou estornadas por profissionais
somente quando o contato pertence à carteira deles; o administrador mantém o
escopo financeiro existente dentro do tenant.

### Expediente semanal por barbearia

Persistir `weekly_hours` no registro da barbearia como sete dias, cada um com
zero ou mais pares de minutos desde a meia-noite. O administrador gerencia a
configuração em Agenda; todos os membros leem o mesmo expediente. Os intervalos
devem usar grade de 30 minutos, estar ordenados e não se sobrepor. APIs de
agendamento e bloqueio obtêm os horários do tenant autenticado e validam a
operação no backend. A barbearia legada mantém o expediente codificado atual
enquanto não houver configuração salva; novos cadastros começam sem intervalos.

### Signup cria organização e proprietário

Reativar o signup público para receber nome da barbearia, nome do proprietário,
e-mail, telefone e senha. Normalizar e validar os dados no backend, mantendo a
política existente de senha e unicidade global de e-mail e telefone. A criação da
barbearia e do primeiro usuário com papel `admin` é uma única operação lógica:
falha em qualquer etapa não pode deixar organização ou conta órfã. A resposta
não inclui senha, hash, CPF ou outros segredos. Após sucesso, a interface
confirma o cadastro e encaminha para o login existente.

O endpoint não aceita papel, status ou identificador de barbearia fornecido
pelo solicitante. O usuário inicial não ganha acesso a nenhuma outra
barbearia. Este fluxo não depende de aprovação manual; o cadastro concluído
permite o login com as credenciais escolhidas.

### Dados existentes sem vínculo explícito

Antes de habilitar o signup, inicializar a barbearia legada sem modificar as
linhas existentes. As APIs tratam valores nulos como pertencentes somente à
barbearia inicial e gravam todas as linhas novas com tenant explícito. O
backfill físico pode ser feito mais tarde, mas não é pré-requisito para o
cadastro e não pode ampliar o acesso a registros de outros tenants.

### Frontend sem autoridade de tenant

O formulário público coleta apenas os dados de cadastro definidos e apresenta
erros do backend sem limpar valores em falhas. Após sucesso, usa o login
existente; não armazena um `barbershop_id` escolhido pelo usuário nem adiciona
filtros de tenant como mecanismo de segurança. As telas internas continuam
consumindo os contratos existentes, agora escopados no backend.

## Risks / Trade-offs

- **A compatibilidade aceita registros sem vínculo explícito** → permitir
  valores nulos somente para o tenant legado, revisar todas as APIs e garantir
  que gravações novas sempre persistam o tenant.
- **Uma consulta esquecida pode expor dados de outra barbearia** → aplicar
  autorização centralizada e filtros em cada endpoint, e testar chamadas
  diretas com dois tenants e referências cruzadas.
- **A criação envolve duas entidades** → garantir atomicidade no backend ou
  compensação segura e testada; nunca retornar sucesso com criação parcial.
- **O signup passa a ser público** → validar todos os campos no servidor,
  manter unicidade global de e-mail e telefone e impedir que a requisição
  escolha papel ou tenant.
- **E-mail globalmente único impede compartilhar login entre barbearias** →
  manter essa regra por simplicidade; permitir associação de um usuário a várias
  barbearias requer decisão e modelo de associação próprios.

## Migration Plan

1. Criar a entidade de barbearia e campos opcionais de tenant, preservando os
   registros legados sem atualizá-los.
2. Inicializar a barbearia legada no primeiro login administrativo e habilitar
   o escopo de compatibilidade apenas para essa organização.
3. Atualizar e testar todas as APIs para derivar o escopo da sessão, permitir
   valores legados nulos somente no tenant inicial e validar
   relações entre registros dentro da mesma barbearia.
4. Publicar o signup público e o formulário Reflex depois que compatibilidade e
   isolamento estiverem ativos.
5. Em rollback, desabilitar o signup e reverter frontend/APIs sem apagar dados;
   manter a entidade inicial para que as contas legadas continuem resolvíveis.

## Open Questions

Nenhuma. O formulário inicial usa nome da barbearia e dados do proprietário;
aprovação, verificação de e-mail, cobrança e dados comerciais adicionais ficam
fora desta Change.
