# Proposta: Correção integrada do Lotus Barber

## Por quê

As telas de clientes, agenda, novo agendamento, equipe, sidebar e perfil apresentam
falhas de validação, disponibilidade, layout e integração com o Xano. A causa não é
uniforme: há regras duplicadas no frontend, estado legado ainda renderizado, consultas
de agenda mensais que não representam corretamente “toda a equipe”, e endpoints Xano
que aceitam o formato errado ou dependem do armazenamento de arquivos pago.

Esta change corrige as causas no backend e no frontend, preservando o tema escuro,
cards, botões azuis, responsividade e mensagens em pt-BR.

## Investigação inicial

- **CPF:** o requisito vigente aceita qualquer valor informado, normalizando apenas
  os dígitos para detectar duplicidade. A validação de dígitos verificadores, tamanho
  e formato foi removida do frontend e do Xano; clientes e profissionais compartilham
  a regra de unicidade.
- **Datas:** o cliente valida nascimento no submit, mas não valida `first_contact_at`
  contra hoje no frontend e não há `max` comum nos inputs. O Xano compara nascimento
  com a data de São Paulo, mas compara primeiro contato com `"now"` como timestamp,
  deixando o contrato inconsistente.
- **Calendário:** ainda existem `appointment_calendar_service_id`,
  `appointment_calendar_service_options` e o select “Qualquer serviço (30 min)”.
  A função de slots tem cálculo de duração, conflitos e equipe, mas o estado do
  calendário deve ser removido e a consulta/normalização mensal precisa garantir que
  todos os profissionais e bloqueios retornados sejam considerados.
- **Agendamentos:** a busca por cliente/telefone continua renderizada e filtrada
  em `appointment_contact_options`, embora o requisito seja selecionar diretamente
  um cliente.
- **Cadastro rápido:** `save_quick_contact` envia somente nome/telefone e o modal
  renderiza somente esses dois campos, duplicando um subconjunto do formulário de
  contatos e não aplicando CPF/datas/origem/primeiro contato/observações.
- **Equipe:** há cadastro de profissional, mas não há estado, endpoint integrado e
  componente de lista com loading/vazio/atualização após cadastro. A API atual
  `auth/professionals` também não valida CPF oficialmente nem normaliza telefone.
- **Sidebar e pesquisa:** a sidebar já usa `height: 100vh`, porém o layout permite
  que o documento principal revele espaço abaixo em combinações de viewport e o
  conteúdo do menu não está isolado de forma robusta. O foco da pesquisa usa
  `outline-offset` no container de agenda, fazendo o contorno sair da área visual.
- **Foto:** o frontend envia arquivo para `auth/me/avatar`; o Xano usa
  `storage.create_image` privado. Esse é o recurso que retorna a exigência de plano
  pago. O fallback deve ser um storage de imagens externo, sem segredo no navegador.
- **Perfil/senha:** os handlers existem, mas dependem de contratos Xano ainda
  inconsistentes: `auth/me PATCH` aceita CPF opcional mas não valida CPF, o upload
  depende do storage bloqueado, e a senha grava o valor recebido diretamente no
  campo `password` após uma compatibilidade legada. Os contratos devem ser
  verificados com respostas reais, hash nativo do Xano e feedback explícito.

## O que muda

1. Criar uma função compartilhada de CPF, aplicada a clientes e profissionais,
   mantendo a rejeição correta de CPFs inválidos e dígitos repetidos.
2. Padronizar datas não futuras no formulário, submit e endpoints Xano.
3. Corrigir a disponibilidade da agenda por duração total, profissional, equipe,
   cancelamento, bloqueio, timezone UTC-3 e intervalo consultado.
4. Remover o filtro de serviço sem efeito, a busca de cliente do agendamento e
   todo estado/markup morto correspondente.
5. Reutilizar o formulário completo de cliente no modal de novo agendamento e
   selecionar automaticamente o cliente criado.
6. Conter o foco da pesquisa e tornar a sidebar uma coluna de viewport com rolagem
   somente no menu e usuário preso ao rodapé.
7. Adicionar a lista responsiva de profissionais.
8. Migrar fotos de perfil para Cloudinary, armazenando no Xano apenas URL e
   identificador do asset, com substituição/remoção segura no backend.
9. Corrigir contratos de perfil, autenticação, atualização de estado e alteração
   de senha.

## Alternativas de armazenamento avaliadas

| Opção | Plano gratuito consultado | Integração e segurança | Decisão |
|---|---|---|---|
| Supabase Storage | 1 GB de arquivos, 5 GB de egress e projetos gratuitos pausados após inatividade; fonte: [pricing.supabase.com](https://supabase.com/pricing) | Bom controle por políticas e URLs assinadas, mas exigiria endpoint Xano para emitir upload/download assinado e uma integração adicional de storage | Não escolhida nesta change |
| Firebase Storage | No-cost quotas no plano Blaze: 5 GB-months, 100 GB/mês baixados, 5 mil uploads/mês e 50 mil downloads/mês em regiões elegíveis; fonte: [firebase.google.com/pricing](https://firebase.google.com/pricing) | Robusto, mas exige projeto Google, billing Blaze para Storage atual e regras Firebase; mais infraestrutura do que o caso precisa | Não escolhida nesta change |
| Cloudinary | Plano Free com 25 créditos mensais; cada crédito equivale a 1 GB de storage, 1 GB de bandwidth ou 1.000 transformações; fonte: [cloudinary.com/pricing](https://cloudinary.com/pricing) | Upload direto por preset restrito sem chave secreta no frontend, CDN e APIs específicas para imagens; segredo de destruição fica somente no Xano | **Escolhida** |

O preset Cloudinary será limitado a JPEG/PNG/WebP, 5 MB, pasta da aplicação e
transformações necessárias. O frontend nunca receberá `api_secret`. O Xano
persistirá `secure_url` e `public_id`, e fará a remoção do asset antigo depois que
o novo asset for confirmado.

## Fora do escopo

- Reescrever o tema visual ou migrar o frontend para outra tecnologia.
- Criar login de clientes.
- Alterar regras de pagamentos, relatórios ou notificações.
- Aceitar os dois CPFs de exemplo como válidos.
- Colocar credenciais Cloudinary, Supabase ou Firebase no frontend.

## Impacto

- **Frontend Reflex:** `frontend/frontend/auth_state.py` e
  `frontend/assets/styles.css`, com extração/reuso do formulário de cliente e
  redução de estado legado.
- **Xano:** endpoints de contatos, profissionais, agenda, perfil e senha; novas
  configurações/endpoint de confirmação do asset Cloudinary.
- **Configuração:** variáveis públicas somente para Cloud name/upload preset;
  `CLOUDINARY_API_SECRET` e token de administração permanecem no Xano.
- **Verificação:** testes unitários do CPF e datas, testes de contrato/API,
  compilação Reflex e roteiro manual de fluxo feliz/erro para cada task.
