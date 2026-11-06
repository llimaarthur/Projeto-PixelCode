# Design

## Contexto

O PixelCode é um painel interno Reflex apoiado por APIs Xano. A autenticação usa `auth/me`, clientes e serviços são cadastros compartilhados e as regras de negócio devem continuar sendo aplicadas pelo backend. A agenda deve atender os papéis existentes (`admin` e `professional`) sem mudar o modelo de uma única barbearia.

## Goals / Non-Goals

**Goals:**
- Disponibilizar calendário mensal, disponibilidade diária e gestão de atendimentos para a equipe.
- Aplicar o mesmo expediente a todos os profissionais: segunda a sexta, 09:00–19:00, intervalo 12:00–13:00; sábado, 09:00–14:00; domingo fechado.
- Calcular horários de 30 minutos considerando a duração dos serviços, atendimentos ativos e bloqueios manuais.
- Permitir cadastro rápido de clientes sem abandonar nem limpar o formulário de agendamento.
- Preservar snapshots dos serviços e o histórico de cancelamentos.
- Permitir que cada usuário mantenha os próprios dados de conta sem conceder acesso administrativo a outros perfis.
- Cobrir carregamento, vazio, validação, falhas de API e submissão em andamento.

**Non-Goals:**
- Calendário semanal, feriados automáticos, recorrência de agendamentos ou múltiplas filiais.
- Criar acesso ou autoatendimento para clientes.
- Implementar cobrança, pagamento, lembretes ou relatórios.
- Alterar permissões de cadastro de clientes/serviços ou criar novos papéis.

## Decisões

### Agenda diária e escopo por papel

O calendário mostrará um mês por vez e marcará as datas com agendamentos. A disponibilidade e a listagem serão filtradas pela data selecionada. Administradores poderão escolher qualquer profissional ativo ou visualizar a equipe; um profissional verá e gerenciará somente a própria agenda. O backend determinará a identidade do profissional autenticado e rejeitará IDs de outros profissionais enviados por um usuário profissional.

O expediente semanal será o informado pela barbearia e igual para todos os profissionais. Os horários serão oferecidos em incrementos de 30 minutos; um início só estará disponível quando o serviço selecionado couber no expediente e não se sobrepuser a um atendimento não cancelado nem a um bloqueio. Sem serviço selecionado, a grade indicará disponibilidade de 30 minutos; a validação final considerará a duração real dos serviços.

Bloqueios manuais terão data, início, fim, profissional (ou toda a equipe, para administradores) e motivo opcional. Bloqueios e atendimentos serão retornados por endpoints autenticados; a criação/remoção de bloqueios e a gravação de atendimentos serão validadas no backend. Profissionais só poderão bloquear e consultar a própria agenda.

A mesma função de disponibilidade será usada pelo calendário e pelo formulário de agendamento. No formulário, a escolha de data, profissional e serviços atualiza os horários oferecidos pela duração total, atendimentos ativos e bloqueios. O calendário continuará indicando opções disponíveis, ocupadas e bloqueadas.

### Cadastro rápido e fluxo de agendamento

O cadastro rápido criará um contato ativo pela API existente e pedirá somente nome e telefone. O fluxo não exibirá, buscará, validará nem enviará CPF; os demais dados de contato continuam sendo opcionais nas telas próprias de clientes. Após a criação, o contato será selecionado e os dados já preenchidos no agendamento, inclusive data e horário, serão mantidos.

Após salvar com sucesso, a tela exibirá um resumo do atendimento. A listagem diária apresentará horário, cliente, serviço, profissional, status e ações; os detalhes serão apresentados em modal. O cancelamento exigirá confirmação e manterá o registro no histórico.

### Integridade e histórico

Um agendamento terá cliente, profissional, início, fim calculado, status e observações. Ele deverá conter pelo menos um serviço ativo. Os itens associados serão persistidos como uma lista JSON no registro do agendamento e guardarão o identificador e um snapshot do nome, preço e duração de cada serviço, além dos totais do agendamento. Alterações futuras no catálogo não mudarão atendimentos existentes.

O Xano verificará a sobreposição de intervalos `[início, fim)` para o mesmo profissional ao criar ou editar um agendamento. Apenas agendamentos cancelados não bloquearão horários. Cancelamentos serão alterações de status, nunca exclusões. Os status operacionais serão `pending`, `confirmed`, `completed` e `cancelled`.

### Perfil próprio e senha

Os campos editáveis serão nome, e-mail e telefone. O CPF existente permanecerá armazenado, mas não será exibido, editado nem enviado pelo formulário; a API aceitará sua omissão e preservará o valor atual. Cada usuário também poderá enviar, substituir ou remover a própria foto de perfil. O arquivo ficará no armazenamento do Xano e será associado ao usuário autenticado, nunca a um ID de usuário confiado ao navegador. Serão aceitas imagens JPEG, PNG e WebP de até 5 MB, validadas pelo backend. O Xano também validará os campos cadastrais e a unicidade do e-mail antes de salvar.

A senha terá um fluxo separado do formulário cadastral, exigindo senha atual, nova senha e confirmação; o backend validará a senha atual e os requisitos da nova senha. O formulário não exibirá nem preencherá qualquer senha existente.

### Integração e erros

O grupo de APIs de agendamentos usará `XANO_APPOINTMENTS_API_URL` e recorrerá a `XANO_API_URL` quando não houver URL específica. Erros retornados pelo backend serão apresentados junto ao fluxo correspondente; falhas não devem ser tratadas como operações bem-sucedidas.

### Interface

A navegação existente receberá a entrada “Agenda”; “Meu perfil” não será um item ou uma rota. O bloco do usuário no rodapé da sidebar abrirá um diálogo compacto e acessível para edição do perfil, reutilizando os formulários existentes de dados, foto e senha. A agenda terá seletor de data, seletor de profissional somente para administradores, lista cronológica, formulário de criação/edição e ações de status/cancelamento. Os identificadores permanecerão nos valores internos dos selects, mas os rótulos mostrarão somente nomes e descrições.

## Riscos / Trade-offs

- **Agenda somente diária** → entrega o fluxo essencial sem introduzir calendário complexo; a navegação semanal poderá ser uma change posterior.
- **Snapshots de serviços** → preservam valores históricos, mas armazenam dados repetidos de propósito.
- **E-mail editável** → exige validação de unicidade e atualização segura da credencial no mesmo registro de autenticação.
- **Foto de perfil** → armazenamento de arquivos do Xano, formatos JPEG/PNG/WebP, limite de 5 MB e remoção permitida, conforme definido na revisão.
- **Verificação de conflito no backend** → protege as operações normais; a implantação deve validar que a lógica de consulta e gravação do Xano evita conflitos no fluxo de criação e edição.

## Plano de migração

1. Criar as estruturas de agendamento e itens/snapshots no Xano sem alterar registros existentes.
2. Publicar endpoints autenticados de consulta, criação, edição, status e perfil.
3. Integrar as telas Reflex e validar as permissões usando os papéis existentes.
4. Em rollback, remover a navegação das telas novas e manter os registros já criados para preservar o histórico.
