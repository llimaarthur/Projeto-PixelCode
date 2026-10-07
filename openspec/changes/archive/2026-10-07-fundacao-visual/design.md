# Design

## Contexto

O PixelCode é um painel interno usado pela equipe de uma barbearia. As telas atuais são funcionais e simples, enquanto as telas operacionais ainda serão implementadas em mudanças futuras. A fundação visual deve funcionar tanto para os fluxos existentes quanto para essas próximas áreas, sem introduzir dependências ou funcionalidades de domínio.

## Objetivos

- Criar uma aparência profissional, calma e legível para uso frequente.
- Manter consistência entre telas, formulários, navegação e estados de feedback.
- Dar destaque às ações e informações relevantes sem depender de cores saturadas.
- Garantir adaptação a telas menores e uso por teclado.

## Não objetivos

- Definir a marca final, logotipo ou materiais de marketing.
- Redesenhar regras ou fluxos de negócio.
- Criar páginas ou links para funcionalidades que ainda não existem.
- Introduzir uma biblioteca visual nova sem necessidade demonstrada.

## Direção visual proposta

Preservar a composição leve e espaçosa das prévias aprovadas usando fundo carvão e superfícies grafite, sem preto absoluto nos cartões. Texto branco e cinzas frios cuidam da leitura. Azul é o acento principal para ações e seleção. Vermelho aparece em detalhes pequenos e em feedback de erro, não como segunda cor de ação. As cores semânticas de sucesso e atenção continuam reservadas a seus estados.

Em todas as telas que exibirem a faixa azul, branca e vermelha, a faixa deve usar a mesma animação contínua e discreta inspirada nas faixas diagonais de uma barbearia. A animação deve respeitar a preferência de movimento reduzido do dispositivo e manter uma versão estática equivalente. O login usa a faixa na borda superior do cartão; o painel interno usa a faixa no topo da navegação lateral. O emblema azul contém a marca branca Lotus, confinada ao emblema. O restante do lado esquerdo do login permanece limpo, sem marcas d'água ou ilustrações grandes.

“Lotus Barber” é o nome hipotético do estabelecimento e deve aparecer na identidade das telas. Isso não renomeia o projeto ou seus componentes técnicos PixelCode. Os dados, navegação e métricas visíveis na prévia do painel são conteúdo fictício para demonstrar a composição; não indicam que esses módulos façam parte desta implementação visual.

### Tokens iniciais propostos

| Token | Valor proposto | Uso |
|---|---|---|
| `background` | `#101216` | Fundo geral das páginas |
| `surface` | `#191C22` | Formulários, cartões e áreas de conteúdo |
| `surface-muted` | `#22262E` | Realces neutros e superfícies secundárias |
| `text-primary` | `#F4F5F7` | Títulos e texto principal |
| `text-secondary` | `#A7ABB4` | Instruções e metadados |
| `border` | `#343943` | Divisores e contornos |
| `accent` | `#2864D9` | Ações principais e seleção ativa |
| `accent-foreground` | `#FFFFFF` | Texto/ícone sobre a ação de acento |
| `detail` | `#D94B54` | Pequenos detalhes visuais e alertas |
| `success` | `#70C69B` | Confirmações |
| `warning` | `#E2B45D` | Atenções |
| `danger` | `#F07178` | Erros e ações destrutivas |

Os valores são ponto de partida, não uma afirmação de contraste já validado. A implementação deve testar as combinações efetivamente usadas e ajustar os valores para atender WCAG 2.1 AA, especialmente texto normal, texto de botão, bordas de controles e foco visível. Evitar usar azul e vermelho simultaneamente em ações equivalentes; o vermelho é reservado a detalhes e estados semânticos.

## Pré-visualizações

As imagens abaixo ilustram a direção visual e não representam telas implementadas. O painel é um conceito de destino; seus módulos e dados dependem de mudanças funcionais próprias. A navegação de módulos na imagem serve apenas para demonstrar o layout futuro; no produto, só devem aparecer destinos com rotas implementadas.

O painel reutiliza a identidade visual apresentada no login: carvão/grafite, tipografia sem serifa, superfícies escuras, acento azul, detalhes vermelhos pontuais, emblema Lotus do mockup e faixa tricolor animada. A navegação ilustrada é apenas referência e não deve introduzir links para rotas ainda inexistentes.

- [Conceito de acesso](./mockups/login.svg)
- [Conceito de painel interno](./mockups/painel-interno.svg)

## Tipografia e espaçamento

- Usar a família sem serifa padrão já disponível no navegador; não carregar fontes externas nesta change.
- Manter hierarquia curta e consistente: título de página, título de seção, texto base e metadados.
- Usar escala de espaçamento baseada em múltiplos de 4 px, priorizando intervalos de 8 px para composição.
- Preservar largura confortável para formulários e permitir que conteúdo operacional use a largura disponível.

## Estrutura das telas

### Acesso e troca de senha

- Composição focada, sem navegação do painel.
- Formulário centralizado em superfície grafite, com largura limitada, título e instrução objetiva.
- Erros e validações próximos ao formulário e associados semanticamente aos campos correspondentes.

### Área interna

- Cabeçalho consistente com identificação do produto/usuário e ação de sair.
- Navegação interna preparada para crescer, mas mostrando somente destinos implementados.
- Conteúdo principal com hierarquia clara, superfícies grafite e adaptação a viewport estreita.
- Em telas pequenas, navegação compacta sem exigir rolagem horizontal.

### Formulários de equipe

- Campos com rótulos visíveis, instruções quando necessárias e estados consistentes de foco, erro e desabilitado.
- Ações principais e secundárias distinguíveis sem depender somente de cor.
- Senha temporária apresentada como conteúdo sensível, preservando a interação existente de ocultar após a exibição.

## Componentes e estados

Padronizar estilos para botão primário, secundário e destrutivo; campo de texto; mensagem de feedback; cartão; divisor; cabeçalho e navegação. Os componentes devem cobrir estados padrão, hover, foco por teclado, pressionado, desabilitado, erro e carregamento quando aplicável.

O foco deve permanecer claramente visível. Mensagens de sucesso, atenção e erro devem combinar cor com texto ou ícone; a cor sozinha não pode transmitir o significado.

## Decisões

- Reutilizar a infraestrutura já presente no frontend Reflex e seus plugins Radix Themes e Tailwind, sem adicionar uma biblioteca visual nesta etapa.
- Concentrar os valores visuais em tokens compartilhados, evitando cores e espaçamentos ad hoc em cada tela.
- Aplicar a mesma linguagem visual a autenticação e área interna, mas manter estruturas de layout adequadas a cada fluxo.
- Validar contraste, teclado e responsividade antes de considerar a fundação concluída.

## Riscos e compensações

- O fundo escuro pode reduzir a legibilidade de textos secundários; validar contraste e clarear os tokens de texto quando necessário.
- Azul e vermelho podem competir se usados com a mesma intensidade; manter o azul como acento de interação e restringir o vermelho a detalhes pequenos e estados de erro.
- Um painel com navegação expansível pode ocupar espaço excessivo em telas pequenas; usar apresentação compacta em viewports estreitos.
- A estilização não deve criar a impressão de que módulos ainda não implementados já estão disponíveis; não exibir itens de navegação inativos ou sem destino.
