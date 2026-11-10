# Corrigir validação de e-mail na API de clientes

## Problema

Endereços comuns de e-mail são rejeitados ao criar ou atualizar clientes,
embora passem pela validação do formulário.

## Objetivo

Validar o formato do e-mail explicitamente nos endpoints de clientes, sem
depender da validação implícita do tipo de entrada de e-mail do Xano.

## Escopo

- Atualizar a validação de e-mail nos endpoints de criação e edição de contatos.
- Preservar e-mails opcionais, normalização e validação no frontend.
- Manter inalterado o esquema da tabela de contatos.

## Fora de escopo

- Remover o campo de e-mail da interface ou do banco.
- Alterar endpoints de autenticação ou perfil.
