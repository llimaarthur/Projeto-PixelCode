## ADDED Requirements

### Requirement: Isolar cache financeiro entre sessões

O frontend SHALL limpar os dados financeiros em memória derivados da sessão
autenticada ao encerrar essa sessão. Uma sessão subsequente SHALL carregar do
backend os próprios dados antes de apresentar opções de clientes, serviços ou
movimentações.

#### Scenario: Trocar de conta ou barbearia

- **WHEN** a sessão autenticada é encerrada e outra conta inicia sessão no
  mesmo cliente
- **THEN** opções e dados financeiros da sessão anterior não são apresentados
  nem enviados pela interface

#### Scenario: Recarregar o Financeiro após a troca

- **WHEN** a nova sessão abre o Financeiro
- **THEN** o painel e as opções do formulário são carregados novamente usando
  a sessão autenticada atual
