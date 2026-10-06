# Domain Model — PixelCode

## 1. Objetivo do modelo de domínio

Este modelo descreve o sistema como uma ferramenta de gestão operacional para a barbearia, com foco na rotina do barbeiro e da equipe. O cliente não acessa o sistema por login, mas entra em contato pela barbearia por WhatsApp, telefone ou indicação. O barbeiro usa a plataforma para organizar a agenda, registrar contatos, manter o catálogo de serviços e acompanhar pagamentos e atendimentos.

O centro do domínio continua sendo a gestão do atendimento: capturar o contato do cliente, converter esse contato em agendamento, manter a agenda organizada e registrar o histórico financeiro e operacional do negócio.

---

## 2. Visão do negócio

A barbearia opera de forma prática e direta:

- o barbeiro é o principal usuário do sistema;
- o cliente entra em contato por WhatsApp ou outro canal externo;
- o barbeiro registra o cliente como contato e cria o agendamento;
- a agenda, os serviços e os pagamentos ficam centralizados em uma ferramenta interna.

O sistema não é um portal do cliente. Ele é um painel de operação da barbearia, usado para gerenciar o fluxo de atendimento e manter o negócio em ordem.

---

## 3. Entidades centrais do domínio

### 3.1 Cliente / Contato externo

Representa a pessoa que entra em contato com a barbearia, mas não possui acesso ao sistema.

### Responsabilidades

- manter o registro do cliente como contato da barbearia;
- registrar dados relevantes para o relacionamento e o atendimento;
- servir como referência para a criação de agendamentos;
- manter o histórico do relacionamento e de atendimentos anteriores.

### Atributos conceituais

- id_cliente;
- nome;
- telefone;
- origem_contato (WhatsApp, indicação, Instagram, ligação, outra origem);
- observacoes;
- status (ativo, inativo, recorrente);
- data_primeiro_contato.

### Relacionamentos

- um cliente pode ter vários agendamentos;
- cada agendamento pertence a um cliente específico;
- o cliente pode ser reconhecido pelo telefone ou pelo nome registrado no contato.

### Regras estruturais importantes

- não existe autenticação de cliente no sistema;
- não deve haver login, senha ou painel do cliente;
- o contato deve ser rastreável e permitir que o barbeiro saiba de onde veio o cliente;
- a data do primeiro contato e a origem do contato ajudam a manter o histórico do relacionamento.

### 3.2 Barbeiro / Funcionário

Representa o profissional que administra a barbearia e executa ou coordena os atendimentos.

### Responsabilidades

- manter o cadastro da equipe;
- gerir a agenda e os atendimentos;
- atribuir horários e serviços;
- acompanhar o histórico de cada cliente e de cada serviço realizado.

### Atributos conceituais

- id_funcionario;
- nome;
- cpf;
- telefone;
- cargo;
- status (ativo/inativo);
- especialidade ou disponibilidade;
- data_inicio_atuacao.

### Relacionamentos

- um barbeiro pode atender vários agendamentos;
- um agendamento é sempre associado a um barbeiro responsável.

### Regras estruturais importantes

- não pode haver agendamento sem barbeiro definido;
- o profissional deve estar ativo para receber novos atendimentos;
- a agenda do barbeiro deve impedir sobreposição de horários.

### 3.3 Serviço

Representa o serviço oferecido pela barbearia, como corte, barba, hidratação, lavagem, etc.

### Responsabilidades

- manter o catálogo de serviços disponíveis;
- preservar preço dos serviços;
- permitir a composição de agendamentos com um ou mais itens.

### Atributos conceituais

- id_servico;
- nome;
- descricao;
- categoria;
- preco;
- status (ativo/inativo);
- data_criacao_atualizacao.

### Relacionamentos

- um serviço pode aparecer em vários agendamentos;
- um agendamento deve conter pelo menos um serviço.

### Regras estruturais importantes

- o valor do serviço em um agendamento deve permanecer congelado no momento da criação;
- serviço inativo não deve ser oferecido em novos agendamentos;
- não deve haver agendamento sem ao menos um serviço vinculado.

### 3.4 Agendamento

É a entidade principal do sistema e representa o compromisso de atendimento da barbearia com um cliente.

### Responsabilidades

- registrar a data, o horário e o serviço solicitado;
- associar cliente, barbeiro e serviços;
- refletir o status do atendimento em cada etapa;
- servir como base para o histórico da barbearia.

### Atributos conceituais

- id_agendamento;
- data;
- horario_inicio;
- status;
- observacoes;
- valor_total;
- canal_origem_agendamento (WhatsApp, ligação, indicação, outro).

### Relacionamentos

- pertence a um cliente;
- é atendido por um barbeiro;
- contém um ou mais serviços;
- pode ter um pagamento relacionado.

### Status comuns

- pendente;
- confirmado;
- concluído;
- cancelado;
- reagendado.

### Regras estruturais importantes

- não pode haver agendamento sem cliente informado;
- não pode haver agendamento sem barbeiro definido;
- deve haver pelo menos um serviço associado;
- não pode existir conflito de horário para o mesmo barbeiro;
- o cliente não precisa ter acesso ao sistema para que o agendamento exista.

### 3.5 Pagamento

Representa o registro financeiro do serviço orçado ou realizado.

### Responsabilidades

- registrar valor do atendimento;
- registrar forma de pagamento;
- acompanhar status de pagamento e cobrança;
- manter histórico financeiro por cliente ou por agendamento.

### Atributos conceituais

- id_pagamento;
- valor;
- forma_pagamento;
- data_pagamento;
- status;
- observacoes_cobranca;
- referencia_pagamento quando houver.

### Relacionamentos

- um pagamento está associado a um único agendamento;
- um agendamento pode estar pendente de pagamento ou já pago.

### Regras estruturais importantes

- cada pagamento deve estar relacionado a um agendamento válido;
- o valor pago deve ser consistente com o valor do agendamento;
- o pagamento pode ser registrado antes ou depois do atendimento, conforme a rotina da barbearia;
- o valor do serviço deve ser preservado mesmo que o preço do catálogo mude depois.

---

## 4. Relacionamentos principais

A estrutura central do domínio pode ser resumida assim:

- Cliente entra em contato com a barbearia por WhatsApp, ligação, indicação ou outro canal externo;
- Barbeiro recebe e organiza o pedido;
- Agendamento é registrado com cliente, barbeiro e serviços;
- Pagamento e histórico são registrados ao longo do atendimento;
- O sistema funciona como agenda e ferramenta de gestão operacional da barbearia, não como portal do cliente.

---

## 5. Regras de integridade do domínio

As regras abaixo devem ser preservadas em qualquer operação:

1. O cliente não precisa ter acesso ao sistema nem conta de usuário.
2. Todo agendamento deve ter cliente, barbeiro e serviço definidos.
3. O barbeiro deve estar ativo para receber agendamentos.
4. O serviço deve estar ativo para estar disponível.
5. Um barbeiro não pode ter dois agendamentos no mesmo horário.
6. O valor do serviço no agendamento deve ser preservado mesmo que o preço do catálogo mude mais tarde.
7. Um agendamento pode existir sem pagamento, mas não sem dados mínimos de negócio.
8. A origem do contato e a data do primeiro contato são elementos importantes para registrar o histórico do relacionamento com a barbearia.

---

## 6. Ciclo de vida do atendimento

O fluxo principal é:

1. O cliente entra em contato pela barbearia via WhatsApp, telefone ou indicação.
2. O barbeiro conversa, entende a demanda e identifica o serviço desejado.
3. O barbeiro cadastra ou seleciona o contato e cria o agendamento.
4. A agenda é validada para evitar conflitos de horário.
5. O atendimento é realizado.
6. O pagamento pode ser registrado conforme a rotina da barbearia.
7. O histórico do cliente, do serviço e do relacionamento fica registrado para futuras consultas.

---

## 7. Resumo executivo

O domínio do PixelCode é centrado na operação da barbearia. O cliente é um contato externo, não um usuário da plataforma. O barbeiro é o principal usuário do sistema e usa a ferramenta para coordenar agenda, contatos, serviços, agendamentos e pagamentos. A origem do contato e a data do primeiro contato são campos importantes porque ajudam a manter o histórico do relacionamento e a dar contexto ao atendente, sem depender de um portal para o cliente.

---

## 8. Referências internas

- Visão geral do projeto: project.overview.md
- Regras do projeto: AGENTS.md
- Especificações: openspec/specs/
- Backend: xano/
- Frontend: frontend/
