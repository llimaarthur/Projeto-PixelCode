# Project Overview — PixelCode (Sistema de Gestão para Barbearia)

## 1. Visão geral

Sistema de gestão para barbearias, permitindo que clientes agendem serviços online e que a equipe administre agendamentos, serviços, funcionários e pagamentos em um único lugar.

## 2. Problema

Barbearias costumam depender de agenda física, WhatsApp ou ligações para marcar horários, o que gera conflitos de agenda, falta de histórico organizado e dificuldade de acompanhar pagamentos e desempenho dos funcionários.

## 3. Objetivos

- Permitir que clientes agendem serviços sem depender de contato direto com a barbearia.
- Dar à equipe uma visão centralizada dos agendamentos, evitando conflitos de horário.
- Registrar o histórico de serviços prestados e pagamentos realizados.

## 4. Público-alvo / usuários

- **Clientes**: usuários finais que criam conta, consultam serviços disponíveis e fazem agendamentos.
- **Funcionários (barbeiros)**: atendem os agendamentos designados a eles.
- **Administração da barbearia**: gerencia funcionários, serviços oferecidos e acompanha pagamentos.

## 5. Escopo

Escopo inicial: cadastro de usuários e funcionários, catálogo de serviços, criação e acompanhamento de agendamentos, e registro de pagamentos associados a cada agendamento.

Fora do escopo inicial: notificações automáticas (SMS/WhatsApp), relatórios avançados de desempenho, múltiplas unidades/filiais.

## 6. Principais funcionalidades

- Cadastro e autenticação de usuários (clientes).
- Cadastro de funcionários e do catálogo de serviços.
- Criação de agendamentos, vinculando cliente, funcionário e um ou mais serviços.
- Registro de pagamento por agendamento.

## 7. Requisitos e restrições importantes

- Um agendamento deve ter pelo menos um serviço vinculado.
- O valor cobrado por serviço em um agendamento deve ser preservado mesmo que o preço do serviço mude posteriormente.
- Um agendamento pode existir sem pagamento (status "pendente"), mas nunca sem cliente e funcionário definidos.

## 8. Arquitetura tecnológica

- **Backend**: Xano (backend visual/no-code com banco de dados e API REST).
- **Frontend**: Reflex (framework Python para interfaces web).
- Comunicação entre frontend e backend via API REST exposta pelo Xano.

## 9. Princípios de desenvolvimento

- Desenvolvimento incremental, utilizando OpenSpec para planejar e revisar cada mudança antes de implementá-la.
- Regras de negócio devem residir no backend (Xano), não no frontend.

## 10. Segurança e integridade

- Autenticação de usuários obrigatória para criação de agendamentos.
- Regras de autorização aplicadas no backend.

## 11. Estratégia de desenvolvimento

O projeto será dividido em mudanças incrementais via OpenSpec, começando pelo cadastro de usuários/autenticação, seguido pelo catálogo de serviços, depois agendamentos, e por fim pagamentos.

## 12. Fonte de verdade e documentação

O modelo de domínio conceitual está descrito em `docs/domain-model.md`. Regras operacionais para os agentes de IA estão em `AGENTS.md`. O comportamento consolidado do sistema é mantido em `openspec/specs/`.