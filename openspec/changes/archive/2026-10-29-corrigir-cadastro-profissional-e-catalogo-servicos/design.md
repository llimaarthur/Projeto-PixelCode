# Design

## Contexto

Consulte `proposal.md` para a motivação e os limites. O frontend seleciona uma URL de API por grupo Xano; a URL do grupo `Services` deve coincidir com seu identificador canônico. O provisionamento de profissionais é protegido no Xano e a tabela `user` mantém índice único para e-mail.

## Goals / Non-Goals

**Goals:**
- Tornar a consulta de duplicidade explícita usando o e-mail normalizado.
- Manter os dados do formulário durante erros e limpar somente após sucesso confirmado.
- Alinhar a declaração do grupo `Services` à configuração do frontend.

**Non-Goals:**
- Tornar endpoints de serviços públicos ou alterar a autorização por papel.
- Remover a unicidade de e-mail ou permitir contas com e-mails repetidos.
- Alterar as URLs de API ou implantar alterações diretamente no ambiente remoto do Xano.

## Decisions

- Consultar a tabela `user` por igualdade do e-mail normalizado e retornar um único resultado; manter a verificação de duplicidade e o índice único como defesa contra cadastros concorrentes.
- Desabilitar a limpeza automática do formulário no envio e disparar a limpeza no fluxo de sucesso, sem descartar dados quando a API rejeitar a operação.
- Declarar no grupo `Services` o mesmo identificador canônico referenciado por `XANO_SERVICES_API_URL`. As rotas continuam com autenticação Xano e as funções de escrita continuam verificando o papel administrativo.

## Risks / Trade-offs

- **A URL configurada pode pertencer a outro grupo no ambiente remoto** → comparar a configuração do frontend e o grupo `Services` no Xano antes de publicar; não alterar permissões para contornar erros de rota.
- **O banco pode realmente conter os e-mails testados** → a verificação exata e a restrição única continuarão rejeitando esses endereços, agora sem apagar o formulário e facilitando a confirmação do valor enviado.

## Migration Plan

1. Aplicar a verificação de e-mail e o ajuste de formulário localmente.
2. Sincronizar/publicar a declaração do grupo `Services` e confirmar que seu identificador corresponde à configuração do frontend.
3. Testar com um e-mail comprovadamente inexistente e outro já cadastrado; testar listagem e criação de serviço com usuário administrador.
4. Em rollback, reverter apenas essas alterações sem modificar registros existentes ou permissões.
