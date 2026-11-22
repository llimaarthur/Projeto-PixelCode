## ADDED Requirements

### Requirement: Validar data de movimentação pela API

A validação de data futura SHALL usar o relógio da API financeira como fonte
autoritativa. A interface SHALL enviar a data convertida no fuso da barbearia
e SHALL apresentar a rejeição da API sem indicar sucesso.

#### Scenario: API rejeita movimentação com data futura

- **WHEN** a API financeira considera a data enviada como futura
- **THEN** a interface exibe a mensagem amigável retornada pela API e não
  registra a movimentação como sucesso
