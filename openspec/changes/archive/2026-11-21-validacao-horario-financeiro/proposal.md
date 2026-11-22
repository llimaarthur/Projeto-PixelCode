# Proposta: Validar horário financeiro pela API

## Why

O formulário de movimentações compara a data informada com o relógio do
processo Reflex antes de chamar a API. Como esse relógio pode divergir do
relógio do Xano, uma movimentação válida pode ser bloqueada no frontend como
se estivesse no futuro.

## What Changes

- Remover a validação de data futura feita pelo relógio local do frontend.
- Preservar a validação da API e o tratamento amigável de seus erros.
- Adicionar teste para garantir que uma data rejeitada pela API chega ao
  backend e que a mensagem é exibida sem indicar sucesso.

## Non-Goals

- Alterar a regra de negócio que proíbe datas futuras.
- Alterar os endpoints Xano ou o formato ou fuso horário enviado no payload.
- Alterar o relógio ou a configuração de fuso horário do servidor.
