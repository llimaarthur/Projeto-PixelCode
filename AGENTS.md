# AGENTS.md

# Instruções para agentes

## Contexto
- Antes de mudanças funcionais, consulte `docs/project.overview.md` e `docs/domain-model.md`.
- Esses documentos descrevem o objetivo do sistema; não presuma que as funcionalidades já estejam implementadas.

## Escopo e fluxo
- Respeite o escopo autorizado e não avance para etapas adjacentes sem confirmação.
- Sessões Explore são apenas para análise e recomendações: não altere arquivos, não implemente e não crie uma Change.
- Mudanças funcionais devem seguir o OpenSpec: Propose, Review, Apply, Verify e Archive.
- Mudanças apenas documentais não autorizam alterações no backend ou frontend.

## Arquitetura e segurança
- Respeite Xano no backend e Reflex no frontend.
- Regras de negócio, persistência e autorização pertencem ao backend; o frontend não é uma barreira de segurança.

## Verificação
- Defina uma estratégia de verificação para mudanças funcionais.
- Informe claramente quais verificações foram executadas e quais não foram possíveis.
- Preserve alterações existentes que não façam parte da tarefa.