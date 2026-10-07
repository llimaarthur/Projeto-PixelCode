# Spec Delta: Fundação visual

## Propósito

Definir requisitos para uma identidade visual coerente, legível e responsiva aplicada aos fluxos Reflex existentes do PixelCode. “Lotus Barber” é o nome hipotético da barbearia que aparece na interface, sem renomear o projeto ou seus componentes técnicos.

## ADDED Requirements

### Requirement: Linguagem visual compartilhada
O sistema SHALL usar tokens visuais compartilhados para cores, tipografia, espaçamento e contornos nas telas cobertas, em vez de definir valores visuais independentes para cada página.

#### Scenario: Telas existentes compartilham os tokens
- **WHEN** um usuário navega entre login, troca de senha, área interna e cadastro de profissional
- **THEN** as telas apresentam cores, tipografia, espaçamento e estados de controles consistentes

#### Scenario: Atualização de token
- **WHEN** um token compartilhado é ajustado
- **THEN** todos os componentes que dependem dele refletem o ajuste sem exigir estilos duplicados por tela

### Requirement: Contraste e hierarquia legível
O sistema SHALL manter contraste de texto e controles compatível com WCAG 2.1 AA e SHALL comunicar estados sem depender somente de cor.

#### Scenario: Texto em superfície
- **WHEN** texto normal ou texto grande é apresentado sobre uma superfície
- **THEN** a combinação atende ao nível AA aplicável da WCAG 2.1

#### Scenario: Mensagem de erro
- **WHEN** um campo ou operação apresenta erro
- **THEN** a interface apresenta uma indicação textual perceptível e não comunica o erro apenas pela cor

### Requirement: Acesso por teclado e foco
O sistema SHALL permitir operar os controles interativos das telas cobertas por teclado e SHALL mostrar claramente o foco atual.

#### Scenario: Navegação por teclado
- **WHEN** o usuário percorre controles com o teclado
- **THEN** a ordem de foco é lógica e cada controle focado tem um indicador visível

### Requirement: Layout responsivo
O sistema SHALL manter conteúdo e controles utilizáveis em larguras de viewport menores e maiores sem rolagem horizontal para a página inteira.

#### Scenario: Tela estreita
- **WHEN** o painel é exibido em viewport estreito
- **THEN** formulários, ações e navegação se reorganizam para permanecer legíveis e operáveis

### Requirement: Navegação apenas para destinos disponíveis
O sistema SHALL apresentar somente destinos de navegação que tenham uma rota implementada.

#### Scenario: Módulo futuro ainda indisponível
- **WHEN** clientes, serviços, agenda ou pagamentos ainda não possuem tela implementada
- **THEN** o painel não apresenta um link de navegação inativo para esses módulos

### Requirement: Consistência dos estados dos componentes
O sistema SHALL aplicar padrões compartilhados para controles e feedback, incluindo estados de foco, desabilitado, erro e sucesso quando aplicáveis.

#### Scenario: Erro em formulário
- **WHEN** uma operação de formulário falha
- **THEN** o feedback aparece de forma consistente e próxima do contexto relacionado, mantendo o conteúdo compreensível

#### Scenario: Senha temporária
- **WHEN** o administrador cria uma conta e a senha temporária é exibida
- **THEN** o estilo da apresentação preserva a instrução para compartilhamento seguro e a ação existente de ocultar a senha

### Requirement: Animação consistente da faixa tricolor
Em qualquer tela que apresente a faixa azul, branca e vermelha da identidade visual, o sistema SHALL aplicar o mesmo movimento contínuo, discreto e horizontal, e SHALL respeitar a preferência de movimento reduzido do dispositivo.

#### Scenario: Faixa em diferentes telas
- **WHEN** a faixa tricolor aparece em mais de uma tela
- **THEN** ela mantém velocidade e direção consistentes em todas as ocorrências

#### Scenario: Movimento reduzido habilitado
- **WHEN** o dispositivo informa preferência por movimento reduzido
- **THEN** a faixa permanece visível em uma apresentação estática e não animada

### Requirement: Identidade da barbearia hipotética
A interface SHALL exibir “Lotus Barber” como nome da barbearia e SHALL manter o emblema Lotus correspondente. Essa identidade visual não SHALL renomear o projeto nem seus componentes técnicos PixelCode. O conteúdo do painel de referência continua ilustrativo e não SHALL introduzir funcionalidades de domínio.

#### Scenario: Aplicação da base visual
- **WHEN** a fundação visual é aplicada às telas existentes
- **THEN** a implementação apresenta “Lotus Barber” na identidade das telas, mantém os fluxos e destinos atuais e não cria agenda, clientes, serviços, pagamentos ou métricas funcionais a partir do conteúdo demonstrativo das prévias
