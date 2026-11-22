# Proposta: Limpar cache financeiro ao trocar de barbearia

## Why

Ao encerrar a sessão, o frontend não limpa as opções de clientes e serviços do
formulário financeiro nem os dados do painel financeiro. Uma sessão reutilizada
por outra conta/barbearia pode exibir dados antigos; a API rejeita vínculos que
não pertencem ao tenant autenticado, mas a interface já apresentou opções
incorretas.

## What Changes

- Limpar dados, seleção e estado de carregamento do Financeiro no reset da
  sessão.
- Garantir que o próximo carregamento do painel e do formulário busque dados
  novamente da API autenticada.
- Adicionar teste para impedir que opções financeiras sobrevivam à troca de
  sessão.

## Non-Goals

- Alterar a autorização ou o isolamento de tenant nos endpoints Xano.
- Reatribuir ou apagar registros já persistidos.
- Alterar os dados de outras telas nesta mudança.
