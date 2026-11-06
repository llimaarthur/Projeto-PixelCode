# Especificação: Correções do Lotus Barber

## ADDED Requirements

### Requirement: validar CPF com a mesma regra em clientes e profissionais
O sistema SHALL normalizar CPF removendo caracteres não numéricos, exigir 11
dígitos, rejeitar sequências iguais e validar os dois dígitos verificadores com a
mesma função no cadastro de cliente e no cadastro de profissional.

#### Cenário: CPF válido com máscara
- **Dado** um CPF oficialmente válido informado com pontos e hífen
- **Quando** o usuário salvar cliente ou profissional
- **Então** o frontend remove a máscara, o backend valida o mesmo valor e o
  cadastro prossegue se não houver duplicidade.

#### Cenário: exemplos informados são inválidos
- **Dado** `312.830.192-38` ou `129.338.123-78`
- **Quando** o usuário salvar
- **Então** o sistema informa CPF inválido, pois ambos falham no cálculo oficial.

### Requirement: rejeitar datas posteriores a hoje
Nascimento e primeiro contato SHALL ter `max` igual à data atual em
`America/Sao_Paulo`, validação no submit e validação equivalente no Xano.

#### Cenário: data futura
- **Quando** nascimento ou primeiro contato for posterior a hoje
- **Então** o formulário impede o envio e mostra mensagem clara em pt-BR.

### Requirement: calcular ocupação por intervalo e equipe
O calendário SHALL somar a duração dos serviços, ignorar somente agendamentos
cancelados, respeitar bloqueios e mostrar disponível apenas se pelo menos um
profissional candidato estiver livre.

#### Cenário: todos ocupados
- **Dado** “Toda a equipe” e agendamentos sobrepostos para todos os
  profissionais
- **Quando** o horário for consultado
- **Então** o horário aparece como “Ocupado”.

#### Cenário: um profissional livre
- **Dado** “Toda a equipe” e pelo menos um profissional livre
- **Então** o horário aparece como “Disponível”.

#### Cenário: bloqueio
- **Dado** bloqueio de equipe ou bloqueios individuais cobrindo o intervalo
- **Então** o horário aparece como “Bloqueado” quando nenhum candidato puder
  atender por bloqueio.

### Requirement: cadastro rápido reutiliza cadastro completo
O modal de novo cliente SHALL exibir nome, telefone, CPF, nascimento, e-mail,
origem, primeiro contato e observações, reutilizando validações e componentes
do cadastro de clientes.

#### Cenário: cliente cadastrado no agendamento
- **Quando** o cadastro for concluído
- **Então** o cliente retornado pelo Xano é selecionado automaticamente e os
  demais dados do agendamento permanecem intactos.

### Requirement: equipe possui lista atualizada
O cadastro de profissional SHALL mostrar lista com loading, estado vazio, erro,
foto/ícone, nome, e-mail, telefone e cargo; a lista SHALL atualizar após cadastro.

#### Scenario: lista de profissionais atualizada
- **WHEN** o administrador conclui um cadastro válido de profissional
- **THEN** a lista recarrega e exibe o novo profissional, ou exibe estado de
  erro explícito se a consulta falhar

### Requirement: foto não usa armazenamento pago do Xano
O sistema SHALL usar Cloudinary com upload sem segredo no frontend, validar
JPEG/PNG/WebP até 5 MB, persistir URL e identificador no Xano e suportar
substituição/remoção do asset anterior.

#### Scenario: upload de foto rejeitado
- **WHEN** o usuário seleciona arquivo não suportado ou maior que 5 MB
- **THEN** o upload não é enviado e uma mensagem pt-BR explica o formato ou
  tamanho permitido

### Requirement: perfil atualiza dados e senha
Salvar dados SHALL usar token, validar e-mail/telefone, atualizar estado local e
sidebar e exibir falhas. Alterar senha SHALL conferir senha atual, exigir
confirmação, usar hash no backend e limpar campos após sucesso.

#### Scenario: alteração de perfil e senha
- **WHEN** o usuário envia dados válidos ou troca a senha com a senha atual correta
- **THEN** o Xano persiste a operação, a interface atualiza o usuário e limpa
  os campos de senha após sucesso

### Requirement: layout preserva foco e viewport
A pesquisa SHALL manter foco contido no próprio campo; a sidebar SHALL ocupar a
viewport inteira com rolagem interna do menu e usuário no rodapé; os modais
SHALL ser responsivos e ter rolagem interna quando necessário.

#### Scenario: layout em viewport curta
- **WHEN** o usuário abre uma página longa ou modal em viewport desktop ou mobile
- **THEN** a sidebar ocupa a viewport, somente o menu/modal rola e o foco da
  pesquisa permanece contido no campo
