# Tarefas

Cada tarefa abaixo é independente para aceite funcional e deve ser validada no
fluxo feliz e no fluxo de erro correspondente.

## 1. Clientes e validações

- [ ] **1.1 Corrigir e compartilhar validação de CPF.** Cobrir máscara, dígitos
  repetidos, tipos string/número, CPF válido conhecido com e sem máscara e os
  dois exemplos inválidos (`312.830.192-38` e `129.338.123-78`). Aplicar a mesma
  função a cliente e profissional e alinhar normalização/unicidade no Xano.
- [ ] **1.2 Impedir datas futuras de cliente.** Adicionar `max`, validação de
  submit e mensagens pt-BR para nascimento e primeiro contato; ajustar POST/PATCH
  Xano ao mesmo fuso e testar data de hoje, data passada, formato inválido e
  data futura.

## 2. Calendário

- [ ] **2.1 Remover o filtro de serviço do calendário.** Excluir select,
  computed vars, estado, handlers e referências sem uso; confirmar que a grade
  continua renderizando slots de 30 minutos apenas como visualização.
- [ ] **2.2 Corrigir disponibilidade “Toda a equipe”.** Revisar endpoints,
  filtros de mês/profissional, UTC-3, parsing de timestamps, status cancelado,
  bloqueios, equipe e duração total. Testar Rubens em 03/11/2026 às 16:00 com
  Americano + Sobrancelha + Barba e testar profissional específico.

## 3. Agendamentos

- [ ] **3.1 Conter foco da pesquisa.** Ajustar wrapper, largura, padding,
  `outline`/`box-shadow` e overflow sem alterar o tema; testar foco por teclado
  em desktop e mobile.
- [ ] **3.2 Remover busca de cliente.** Remover input, estado, handler,
  filtragem e markup relacionados; confirmar que o select direto continua
  carregando clientes e exibindo erro quando nenhum é selecionado.
- [ ] **3.3 Reutilizar formulário completo no cadastro rápido.** Incluir todos
  os campos obrigatórios/opcionais, aplicar CPF/datas/origem/primeiro contato e
  manter layout modal centralizado com scroll; testar validações e sucesso.
- [ ] **3.4 Selecionar cliente recém-criado.** Usar o retorno do POST, inserir o
  contato na lista sem duplicação e preencher o select automaticamente,
  preservando profissional, serviços, data e horário do agendamento.

## 4. Equipe

- [ ] **4.1 Corrigir CPF de profissional.** Usar o helper compartilhado no
  frontend e endpoint Xano, normalizar CPF/telefone, validar duplicidade e
  apresentar mensagens pt-BR.
- [ ] **4.2 Adicionar lista responsiva de profissionais.** Criar consulta
  autenticada, loading, vazio, erro e cards com foto/ícone, nome, e-mail,
  telefone e cargo; atualizar após cada cadastro e empilhar abaixo em telas
  estreitas.

## 5. Navegação e perfil

- [ ] **5.1 Corrigir sidebar de viewport.** Isolar rolagem no menu, manter 100dvh,
  fixar o usuário no rodapé e testar páginas longas, viewport curto e mobile.
- [ ] **5.2 Ajustar nome do arquivo da foto.** Adicionar borda igual aos inputs,
  truncamento e tooltip/label acessível para nomes longos.
- [ ] **5.3 Migrar foto para Cloudinary.** Configurar preset restrito, validar
  JPEG/PNG/WebP e 5 MB no cliente e Xano, salvar URL/public_id, substituir e
  remover asset antigo, atualizar sidebar/perfil e testar falhas do serviço sem
  expor segredo.
- [ ] **5.4 Corrigir salvar alterações de perfil.** Verificar método, token,
  CORS, payload, e-mail único, telefone normalizado, resposta Xano, estado local
  e sidebar; testar sucesso, e-mail duplicado, formato inválido, sessão expirada
  e erro de rede.
- [ ] **5.5 Corrigir alteração de senha.** Exigir senha atual, nova e confirmação,
  validar força, verificar senha atual no Xano, usar hash nativo, limpar campos
  após sucesso e exibir erros de autenticação/validação sem silêncio.

## 6. Verificação

- [ ] **6.1 Executar testes automatizados e análise estática.** Adicionar testes
  unitários para CPF, datas, intervalos e disponibilidade; executar sintaxe,
  importação e `reflex compile --dry`.
- [ ] **6.2 Executar roteiro manual por task.** Para cada item 1.1–5.5 registrar
  fluxo feliz e erro, verificar console sem erros, responsividade desktop/mobile,
  contratos Xano reais e ausência de segredos no bundle.
- [ ] **6.3 Revisar documentação e contrato.** Atualizar especificações de
  clientes, agenda, equipe e perfil com os cenários implementados e registrar
  limites do Cloudinary e qualquer pendência de ambiente Xano.

## Continuação — filtro, equipe, CPF e perfil

- [x] **7.1 Remover “Toda a equipe” do calendário.** O filtro agora exige um
  profissional cadastrado e seleciona o usuário profissional ou o primeiro
  profissional disponível para administradores.
- [x] **7.2 Compactar e paginar profissionais.** A lista usa linhas, cabeçalho,
  avatar pequeno e paginação frontend de seis itens, preservando estados de
  carregamento e vazio.
- [x] **7.3 Aceitar CPF não vazio sem validar dígitos.** A máscara só formata,
  o frontend não rejeita tamanho ou dígitos verificadores, e o Xano normaliza
  apenas números e verifica duplicidade entre clientes e profissionais.
- [ ] **7.4 Validar perfil ponta a ponta no navegador.** Reproduzir upload,
  salvar dados e alteração de senha com sessão autenticada, registrar resposta
  Xano e confirmar persistência após recarregar.
