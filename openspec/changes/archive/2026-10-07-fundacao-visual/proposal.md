# Proposta: Fundação visual do PixelCode

## Por quê

O frontend possui fluxos de acesso e uma área interna mínima, mas ainda não tem uma identidade visual compartilhada. Sem uma base comum, as próximas telas podem adotar cores, espaçamentos e padrões de interação diferentes, aumentando o retrabalho e dificultando o uso diário.

## O que muda

- Definir tokens reutilizáveis para cores, tipografia, espaçamento, bordas, elevação e estados de interação.
- Aplicar a identidade aprovada nas prévias: fundo carvão, superfícies grafite, tipografia clara, azul como acento principal e vermelho em detalhes pontuais.
- Usar “Lotus Barber” como nome hipotético da barbearia exibido nas telas; isso não renomeia o projeto ou seus componentes técnicos PixelCode.
- Repetir a faixa azul, branca e vermelha animada em todas as telas que a exibirem, respeitando a preferência de movimento reduzido.
- Estabelecer estruturas distintas para telas de acesso e telas internas, com comportamento responsivo.
- Padronizar componentes e estados comuns, incluindo botões, campos, mensagens, cartões, navegação, foco e feedback de validação.
- Aplicar a fundação visual às telas Reflex existentes: login, troca de senha, área interna e cadastro de profissional.
- Registrar orientações para que as futuras telas de clientes, serviços, agenda e pagamentos reutilizem o mesmo sistema visual.
- Manter a prévia do painel como referência visual apenas; ela não implementa nem autoriza os módulos ilustrados de agenda, clientes, serviços ou financeiro.

## Limites

- Esta change não implementa funcionalidades de clientes, serviços, agenda, pagamentos ou relatórios.
- Não altera autenticação, regras de autorização, endpoints, persistência ou modelo de dados.
- Não cria navegação para rotas de funcionalidades ainda inexistentes.
- A paleta e os padrões descritos em `design.md` são a proposta visual para revisão antes da implementação.
