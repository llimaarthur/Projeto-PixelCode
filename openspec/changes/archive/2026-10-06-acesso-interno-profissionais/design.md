# Design

## Context

Consulte `proposal.md` para a motivação e os limites do escopo. O workspace Xano contém artefatos iniciais gerados pelo provisionamento do workspace; eles não são considerados regras de negócio aprovadas. A aplicação Reflex ainda é um template sem telas de produto.

## Goals / Non-Goals

**Goals:**
- Estabelecer identidade autenticada para cada profissional e distinguir administrador de profissional.
- Manter autenticação e autorização no backend.
- Entregar um fluxo inicial utilizável de login, provisionamento administrativo e troca obrigatória de senha temporária.

**Non-Goals:**
- Implementar CRUD de clientes, serviços, agenda ou pagamentos nesta Change.
- Criar cadastro público, convite por e-mail ou autenticação para clientes.
- Criar uma entidade de funcionário separada da conta profissional nesta primeira etapa.
- Definir permissões de escrita de clientes, além da consulta compartilhada acordada.

## Decisions

### Uma conta representa um profissional

A identidade autenticável será também a identidade profissional nas operações. Uma entidade separada de funcionário foi considerada, mas adicionaria uma relação e uma etapa de sincronização sem uma necessidade aprovada. Se surgirem perfis de equipe sem login ou mais de uma conta por profissional, essa decisão poderá ser revista em uma Change específica.

### O papel administrativo é adicional ao papel profissional

O administrador também é um profissional e tem agenda própria. Haverá exatamente uma conta administradora; esse papel concede permissões ampliadas para gerenciar a equipe e consultar dados de todos. Os demais profissionais ficam limitados aos próprios atendimentos e agenda. A autorização deve ser decidida pelo backend, não por controles de interface.

### Dados obrigatórios do profissional

O cadastro pela aplicação exige nome, e-mail, telefone e CPF. Embora o CPF aumente a quantidade de dados pessoais armazenados, sua obrigatoriedade foi aprovada para o domínio; o backend deve limitar sua exposição às permissões autorizadas e não incluí-lo em logs de autenticação.

### Provisionamento manual pela aplicação, com bootstrap inicial no Xano

Para evitar autoinscrição pública, a única conta administradora é criada diretamente no Xano. Depois disso, o administrador cria contas de profissionais pela área autenticada. O sistema gera uma senha temporária aleatória, apresenta-a uma única vez na resposta de criação e exige sua troca no primeiro acesso. O endpoint não aceita senhas fornecidas pelo cliente, e a senha gerada não deve ser incluída em logs. A aplicação não oferece criação ou promoção de outras contas administradoras. Convites por e-mail foram considerados, mas ficam fora do escopo inicial e evitam introduzir uma dependência externa.

### Diretório de clientes compartilhado

Todos os profissionais poderão consultar a lista de clientes, mesmo sem atendimento anterior associado. A edição dos registros de clientes não foi decidida e permanece fora desta Change; a Change de contatos deverá fechar essa autorização antes de implementar escrita.

### Entrega vertical mínima

Esta Change entrega autenticação, provisionamento e proteção no backend junto com os fluxos mínimos do Reflex. As APIs de domínio e suas telas serão adicionadas nas Changes próprias, consumindo a política de autorização definida aqui.

## Risks / Trade-offs

- **Conta diretamente representa profissional** → reduz complexidade inicial, mas dificulta suportar funcionários sem login ou várias contas por profissional; reavaliar se esses casos forem aprovados.
- **CPF obrigatório** → aumenta a quantidade de dados pessoais armazenados; restringir sua exposição e mantê-lo fora de logs e respostas que não precisam do dado.
- **Administrador único** → simplifica a matriz inicial de permissões, mas cria dependência operacional de uma única conta; recuperação dessa conta deve seguir o procedimento administrativo do Xano.
- **Senha temporária exibida uma vez** → o administrador precisa entregá-la por um canal seguro; restringir a resposta ao administrador autenticado, exigir troca no primeiro acesso e não persistir o valor em logs ou consultas posteriores.
- **Bootstrap no Xano** → depende de procedimento operacional seguro; documentar e limitar o provisionamento inicial, sem rota pública de bootstrap.
- **Diretório compartilhado** → todos os profissionais podem consultar os contatos; limitar a autorização no backend e decidir separadamente as permissões de escrita.

## Migration Plan

1. Preparar a primeira conta administradora diretamente no Xano.
2. Publicar o backend com autenticação, papéis, provisionamento administrativo e troca obrigatória da senha temporária.
3. Publicar a área Reflex protegida e validar os fluxos com contas de teste de administrador e profissional.
4. Em caso de rollback, desabilitar o provisionamento administrativo e o acesso à nova área; não apagar contas nem dados existentes automaticamente.
