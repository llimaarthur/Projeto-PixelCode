# Proposta: Documentação do modelo de domínio e visão geral

## Por quê

Os documentos `docs/domain-model.md` e `docs/project.overview.md` precisam descrever com mais clareza e detalhe o propósito do PixelCode, o modelo de operação da barbearia e os conceitos centrais do negócio. A documentação deve deixar explícito que a plataforma é interna e que o cliente permanece como contato externo, sem acesso próprio ao sistema.

## O que muda

- Detalhar o modelo de domínio, incluindo visão do negócio, entidades, responsabilidades, atributos conceituais já acordados, relacionamentos, regras de integridade e ciclo de vida do atendimento.
- Ampliar a visão geral do projeto com problema, objetivos, público-alvo, escopo e itens fora do escopo, fluxo principal, regras de negócio, arquitetura, segurança e critérios de sucesso.
- Alinhar a terminologia e as decisões de negócio entre os dois documentos.

## Limites

- Esta change trata somente da documentação nos dois arquivos citados.
- Não implementa nem altera backend, frontend, banco de dados, endpoints ou autenticação.
- Não redefine atributos de entidades; registra em mais detalhe as decisões de domínio já acordadas.