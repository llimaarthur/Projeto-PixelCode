# Proposta: Documentação base do PixelCode

## Por quê

Os documentos do projeto precisam apresentar uma visão coerente do PixelCode para pessoas e agentes que trabalham no repositório. A documentação deve explicar o propósito e o domínio do produto, orientar contribuições de forma consistente e distinguir o que está planejado do que já existe no código.

## O que muda

- Reformular `docs/domain-model.md` com a visão do negócio, entidades, responsabilidades, atributos conceituais acordados, relacionamentos, regras de integridade e ciclo de vida do atendimento.
- Ampliar `docs/project.overview.md` com problema, objetivos, público-alvo, escopo, fluxo principal, regras, arquitetura, segurança e critérios de sucesso, alinhando-o ao modelo de domínio e sem incluir duração de serviço.
- Atualizar `AGENTS.md` com orientações estáveis sobre contexto, escopo, fluxo OpenSpec, arquitetura, segurança e verificação.
- Atualizar `README.md` como ponto de entrada do repositório, com descrição do produto, tecnologias, links para documentação e instrução básica para executar o frontend.

## Limites

- Esta change trata somente dos quatro arquivos documentais citados.
- Não implementa nem altera backend, frontend, banco de dados, endpoints ou autenticação.
- Não redefine atributos de entidades; registra em mais detalhe as decisões de domínio já acordadas.