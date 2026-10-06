# Project Overview — PixelCode

## 1. Visão geral

PixelCode é um sistema interno de gestão para barbearias, pensado para ser usado principalmente pelo barbeiro e por sua equipe. A plataforma centraliza a agenda, os contatos, os serviços, os agendamentos e os históricos financeiros, mas o cliente não acessa a aplicação diretamente.

A interação com o cliente continua acontecendo fora do sistema, principalmente pelo WhatsApp, telefone ou indicação. O barbeiro usa a ferramenta para registrar o contato, organizar o atendimento e controlar o fluxo do negócio sem depender de um portal do cliente.

---

## 2. Problema de negócio

Barbearias ainda convivem com processos manuais, como agendas em caderno, mensagens pessoais e ligações para confirmar horários. Esse modelo gera:

- conflitos de agenda;
- perda de histórico de clientes e pedidos;
- dificuldade de rastrear serviços realizados;
- baixa organização das finanças;
- dependência da memória do barbeiro ou de ferramentas dispersas.

A proposta do PixelCode é resolver isso com uma ferramenta comercial simples, orientada ao uso do empresário/barbeiro, e não com um sistema de login para o cliente.

---

## 3. Objetivo do sistema

- organizar a agenda da barbearia;
- manter cadastro de contatos e clientes em uma base centralizada;
- registrar serviços, horários e status de agendamento;
- facilitar a gestão do barbeiro e da equipe;
- acompanhar pagamentos e histórico de atendimento;
- permitir que o orçamento e o agendamento sejam criados a partir do contato do cliente, sem exigir acesso do cliente à plataforma.

---

## 4. Público-alvo e usuários

### 4.1 Barbeiro / dono do negócio

É o principal usuário do sistema. Ele usa a plataforma para:

- administrar agenda;
- registrar clientes por contato;
- mapear serviços e horários;
- controlar pagamentos e histórico do negócio.

### 4.2 Equipe da barbearia

Pode incluir outros profissionais ou colaboradores que acompanham agendamentos e organização interna.

### 4.3 Cliente

O cliente não é usuário do sistema. Ele entra em contato com o barbeiro por fora, como WhatsApp, telefone ou indicação, e o profissional registra esse atendimento na plataforma.

---

## 5. Escopo funcional

### 5.1 Funcionalidades do escopo inicial

- cadastro de contatos/clientes;
- cadastro de barbeiros e equipe;
- catálogo de serviços com preço;
- criação e edição de agendamentos;
- controle de agenda por profissional;
- registro de pagamentos;
- histórico de atendimentos por cliente e por profissional;
- acompanhamento do status do agendamento.

### 5.2 Fora do escopo inicial

- login para o cliente;
- painel do cliente;
- autoatendimento por app;
- notificações automáticas para clientes via app;
- múltiplas filiais complexas;
- relatórios analíticos avançados;
- integrações financeiras avançadas.

---

## 6. Fluxo principal de valor

O fluxo principal do sistema é o seguinte:

1. O cliente entra em contato com a barbearia pelo WhatsApp ou outra forma externa.
2. O barbeiro conversa sobre o serviço desejado.
3. O barbeiro confirma disponibilidade e agenda o atendimento.
4. O sistema registra cliente, barbeiro, serviço e horário.
5. O atendimento é realizado.
6. O pagamento e o histórico são registrados no sistema.
7. A barbearia consegue consultar a agenda e o histórico sem depender de papel ou mensagens dispersas.

Esse ciclo é a base do valor comercial do produto.

---

## 7. Regras de negócio centrais

- o cliente não possui login no sistema;
- o sistema é operado pela barbearia e não por um cliente final;
- todo agendamento deve conter cliente, barbeiro e serviço;
- o profissional deve estar ativo para receber agendamento;
- o serviço deve estar ativo para constar no catálogo;
- o mesmo barbeiro não pode ter sobreposição de horários;
- o valor do serviço deve ser preservado no agendamento, mesmo que o catálogo seja atualizado depois;
- o pagamento pode ficar pendente, mas o agendamento precisa existir com integridade mínima de dados.

---

## 8. Arquitetura tecnológica

- **Backend**: Xano, para persistência de dados, autenticação da equipe, regras de negócio e APIs.
- **Frontend**: Reflex, para painel administrativo da barbearia.
- **Modelo de uso**: painel interno do barbeiro, com fluxo de agenda e controle financeiro.

A regra essencial é que a lógica crítica do negócio fique no backend, e não no navegador.

---

## 9. Estrutura de uso do sistema

### 9.1 Ambiente do barbeiro

A interface principal é voltada ao dono da barbearia ou ao profissional que administra a agenda.

### 9.2 Ambiente do cliente

Não existe. O cliente não acessa a plataforma. A comunicação com o cliente acontece fora do sistema, principalmente por WhatsApp.

### 9.3 Papel da tecnologia

A tecnologia serve como apoio ao trabalho do barbeiro, não como ferramenta autônoma para o cliente.

---

## 10. Requisitos de segurança e integridade

- autenticação e autorização apenas para usuários internos da barbearia;
- controle de acesso para barbeiros e equipe;
- proteção de dados de clientes e finanças;
- validação das regras de negócio no backend;
- histórico confiável de agendamentos e pagamentos.

---

## 11. Estratégia de desenvolvimento

A evolução do projeto deve acontecer em etapas incrementais, seguindo a lógica do negócio da barbearia:

1. cadastro de barbeiros e equipe;
2. catálogo de serviços;
3. gestão de contatos e clientes;
4. agenda e agendamentos;
5. pagamentos e histórico;
6. refinamentos de UX e relatórios.

---

## 12. Critérios de sucesso

O projeto será bem-sucedido quando:

- o barbeiro conseguir organizar a agenda com menos esforço;
- os atendimentos ficarem rastreáveis;
- o histórico do cliente e do serviço permanecer organizado;
- os pagamentos e agendamentos forem mais fáceis de controlar;
- o processo de trabalho da barbearia deixar de depender de caderno e mensagens dispersas.

---

## 13. Documento relacionado

- Modelo de domínio: domain-model.md
- Regras do projeto: AGENTS.md
- Especificações do sistema: openspec/specs/

---

## 14. Resumo executivo

PixelCode deixa de ser um sistema com cliente logado e vira uma ferramenta interna de gestão para a barbearia. O cliente continua sendo atendido por canais externos, principalmente WhatsApp, e o barbeiro passa a usar a plataforma como centro de organização do negócio. A proposta central é transformar a rotina manual em uma operação estruturada, organizada e fácil de administrar.

