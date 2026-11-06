# Design: Correção integrada do Lotus Barber

## Princípios

- A regra crítica existe no Xano e é repetida no frontend apenas para feedback
  imediato.
- O formulário completo de contato será um componente/fábrica compartilhado; o
  modal não terá uma segunda implementação de validação.
- Datas de formulário representam datas civis em `America/Sao_Paulo`; timestamps
  de agenda são enviados ao Xano em ISO com offset `-03:00` ou epoch equivalente,
  sempre com limites explícitos.
- Um intervalo de atendimento é `[start_at, end_at)`. Conflito ocorre quando
  `existing.start < requested.end` e `existing.end > requested.start`.

## CPF compartilhado

Criar um helper único que:

1. converta o valor para string;
2. remova tudo que não for dígito;
3. exija exatamente 11 dígitos;
4. rejeite os 11 dígitos iguais;
5. calcule o primeiro dígito com pesos 10..2 e o segundo com pesos 11..2;
6. compare dígitos como inteiros, sem depender de coerção implícita.

O valor enviado ao Xano será normalizado sem máscara. O endpoint de cliente e o
endpoint de profissional devem aplicar a mesma regra, além de unicidade no campo
normalizado.

## Datas

Os inputs de nascimento e primeiro contato receberão `max` igual à data atual
calculada no fuso da barbearia. O submit rejeitará data inválida ou posterior a
hoje com mensagens específicas em pt-BR. O Xano receberá `Y-m-d` para datas civis
e validará contra `now|format_timestamp:"Y-m-d":"America/Sao_Paulo"`.

## Disponibilidade

- Para um profissional específico, consultar somente seus agendamentos e
  bloqueios.
- Para “Toda a equipe”, consultar todos os profissionais ativos e seus intervalos.
- Ignorar apenas status `cancelled`; qualquer outro status ocupa o intervalo.
- Somar `duration_minutes` dos snapshots/serviços do agendamento; nunca assumir
  30 minutos para uma reserva já criada.
- Um slot é `available` se algum profissional estiver livre.
- É `blocked` somente quando todos os profissionais candidatos estão bloqueados
  ou o slot não cabe no expediente; é `occupied` quando nenhum está bloqueado,
  mas todos estão ocupados.
- Bloqueio de equipe (`professional_id = null/0`) prevalece para todos.
- A consulta mensal usa início do primeiro dia e fim do primeiro dia do mês
  seguinte, convertidos de `America/Sao_Paulo` para UTC no request. A data exibida
  é convertida de volta para o mesmo fuso antes da comparação.

O endpoint de disponibilidade pode retornar os intervalos brutos do mês; o
frontend não deve inferir ausência de ocupação a partir de uma consulta filtrada
por um único profissional.

## Formulário de cliente e novo agendamento

Extrair uma função de componente/formulário parametrizada por estado e prefixo de
IDs. O cadastro completo e o cadastro dentro do agendamento usarão os mesmos
campos: nome, telefone, CPF, nascimento, e-mail, origem, primeiro contato e
observações. Após `POST /contacts`, o contato retornado será inserido/atualizado
na coleção local e seu ID será atribuído a `appointment_form_contact_id`.

O select de cliente não terá campo de busca. A lista poderá continuar paginada no
backend, mas a filtragem por nome/telefone no navegador e seu estado serão
removidos.

## Foto de perfil

1. O navegador valida extensão/MIME por assinatura e tamanho máximo de 5 MB.
2. O navegador envia o arquivo diretamente ao Cloudinary usando `cloud_name`,
   `upload_preset` restrito e `folder`; nenhum segredo é enviado.
3. O frontend envia ao endpoint autenticado do Xano somente `secure_url` e
   `public_id` retornados.
4. O Xano valida o `public_id` na pasta do usuário, salva o novo asset e, após
   sucesso, chama a API de destruição Cloudinary com `api_secret` no ambiente
   seguro. Falhas de remoção antiga são registradas e não desfazem uma URL nova
   já persistida.
5. A resposta atualiza o estado de perfil e sidebar. A remoção exclui o asset no
   Cloudinary antes de limpar a referência do Xano, com erro explícito se falhar.

## Perfil e senha

`PATCH /auth/me` recebe somente nome, e-mail e telefone; valida e-mail único,
telefone normalizado e devolve o usuário atualizado. O estado local e o bloco da
sidebar são atualizados com essa resposta.

`POST /auth/change-password` valida senha atual com o helper de senha nativo do
Xano, exige nova senha e confirmação iguais, aplica mínimo de 8 caracteres,
letra e número, grava pelo mecanismo de hash do campo `password` e limpa os
inputs após sucesso. Nenhuma falha de API será convertida em sucesso.

## Layout

- A sidebar será `position: sticky` (ou `fixed` no breakpoint correspondente),
  `top: 0`, `height: 100dvh`, com `min-height: 0`.
- O container do menu terá `overflow-y: auto`; o bloco de usuário ficará fora
  desse scroll, com `margin-top: auto`.
- O wrapper da pesquisa terá `min-width: 0`, `overflow: hidden` e o foco usará
  `box-shadow`/border interno, sem `outline-offset` para fora do campo.
- Modais terão `width: min(680px, calc(100vw - 32px))`, `max-height` de viewport,
  rolagem interna e layout em coluna em telas estreitas.

## Riscos e mitigação

- **Cloudinary free pode mudar:** registrar limites e links na documentação da
  change; manter a URL abstraída por endpoint Xano.
- **Consulta mensal grande:** limitar campos/intervalos retornados e filtrar por
  mês no Xano; testar bordas de mês e UTC-3.
- **Mudança de contrato Xano:** validar respostas reais antes de ligar cada tela,
  preservando mensagens de erro do backend.
