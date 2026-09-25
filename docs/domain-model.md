# Domain Model — PixelCode

## Usuario

### Descrição

Representa o cliente que utiliza o sistema para agendar serviços.

### Responsabilidade

Manter os dados de cadastro e autenticação do cliente.

### Principais atributos conceituais

Nome, CPF, email, telefone, senha, status.

### Relacionamentos

Um usuário pode fazer vários agendamentos. Cada agendamento pertence a exatamente um usuário.

### Regras estruturais importantes

Não pode haver agendamento sem um usuário definido.


## Funcionario

### Descrição

Representa o barbeiro/profissional que atende os agendamentos.

### Responsabilidade

Manter os dados de cadastro dos profissionais da barbearia.

### Principais atributos conceituais

Nome, CPF, telefone, cargo, status.

### Relacionamentos

Um funcionário pode receber vários agendamentos. Cada agendamento é atendido por exatamente um funcionário.

### Regras estruturais importantes

Não pode haver agendamento sem um funcionário definido.


## Servico

### Descrição

Representa um serviço oferecido pela barbearia (ex.: corte, barba), reutilizável entre vários agendamentos.

### Responsabilidade

Manter o catálogo de serviços disponíveis e seus preços.

### Principais atributos conceituais

Nome, descrição, preço, status.

### Relacionamentos

Um serviço pode estar associado a vários agendamentos. Um agendamento deve ter pelo menos um serviço.

### Regras estruturais importantes

O valor cobrado em um agendamento deve ser preservado mesmo que o preço do serviço mude depois.


## Agendamento

### Descrição

Representa a marcação de um horário entre um cliente e um funcionário para a realização de um ou mais serviços. É o conceito central do domínio.

### Responsabilidade

Coordenar cliente, funcionário, serviços e pagamento de um atendimento.

### Principais atributos conceituais

Data, horário, status (pendente, confirmado, concluído, cancelado).

### Relacionamentos

Pertence a um usuário e a um funcionário. Está associado a um ou mais serviços. Pode gerar no máximo um pagamento.

### Regras estruturais importantes

Não pode existir sem cliente e funcionário. Deve ter pelo menos um serviço. Pode existir sem pagamento.


## Pagamento

### Descrição

Representa o registro financeiro de um agendamento.

### Responsabilidade

Registrar valor, forma e data do pagamento de um agendamento.

### Principais atributos conceituais

Valor, forma de pagamento, data do pagamento, status.

### Relacionamentos

Está associado a exatamente um agendamento.

### Regras estruturais importantes

Um agendamento pode não ter pagamento ainda (status "pendente").