# Design: Limpar cache financeiro ao trocar de barbearia

O reset central de sessão (`_clear_session`) será responsável por descartar
todo o estado financeiro derivado do usuário autenticado: dashboard, lista de
movimentações, opções de formulário, cliente/serviço/agendamento selecionados,
erros e estados de carregamento. Os próximos acessos iniciam sem dados em cache
e usam as requisições existentes, cujo escopo é definido pela autenticação na
API.

O backend continua sendo a autoridade de isolamento e validação. Esta mudança
evita que a interface apresente opções de uma sessão anterior; não modifica nem
reatribui dados persistidos.
