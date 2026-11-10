# Corrigir validação de e-mail no cadastro de clientes

## Problema

Ao salvar o cadastro de um cliente, um endereço de e-mail válido pode ser
rejeitado pelo formulário antes de a validação da aplicação processar o envio.

## Objetivo

Fazer com que os formulários de cadastro de clientes usem a validação explícita
já existente na aplicação, sem bloquear o envio por uma validação nativa
inconsistente do navegador.

## Escopo

- Ajustar o campo de e-mail do cadastro de clientes e do cadastro rápido de
  cliente durante a criação de agendamento.
- Preservar a validação da aplicação e a validação do backend.

## Fora de escopo

- Alterar as regras de validação ou persistência do backend.
- Alterar os formulários de login, perfil ou cadastro de profissionais.
