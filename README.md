# 💈 PixelCode — Sistema de Gestão para Barbearias

Sistema de gestão desenvolvido para otimizar a administração de barbearias, centralizando o gerenciamento de clientes, profissionais, serviços, agendamentos e movimentações financeiras em uma única plataforma.

O PixelCode foi desenvolvido como projeto acadêmico no segundo semestre, aplicando conceitos de desenvolvimento de software, integração entre frontend e backend, modelagem de dados e organização de processos de negócio. O desenvolvimento contou com a assistência da IA **GitHub Copilot**.

---

## 📌 Sobre o projeto

O PixelCode é uma plataforma voltada para proprietários de barbearias, barbeiros e equipes administrativas.

A proposta é substituir controles manuais, como agendas em papel e informações espalhadas em conversas, por um ambiente digital organizado e intuitivo.

O sistema funciona como um painel interno de gestão. O cliente entra em contato com a barbearia por canais externos, como WhatsApp ou telefone, e o profissional utiliza o PixelCode para registrar e organizar os atendimentos.

## 🎯 Objetivos

- Centralizar as informações da barbearia.
- Facilitar o gerenciamento de clientes e profissionais.
- Organizar agendamentos e horários de atendimento.
- Gerenciar o catálogo de serviços e seus respectivos valores.
- Acompanhar pagamentos e movimentações financeiras.
- Manter o histórico de atendimentos.
- Melhorar a organização e o controle operacional do negócio.

## ⚙️ Funcionalidades

### 👥 Gestão de clientes
- Cadastro e gerenciamento de clientes.
- Consulta de informações e contatos.
- Histórico de atendimentos.

### 💈 Gestão de profissionais
- Cadastro de barbeiros e funcionários.
- Organização da equipe.
- Controle de profissionais ativos e inativos.

### 📅 Agendamentos
- Criação e edição de agendamentos.
- Organização da agenda por profissional.
- Controle de horários e disponibilidade.
- Acompanhamento do status dos atendimentos.

### ✂️ Serviços
- Cadastro e gerenciamento de serviços.
- Definição de preços.
- Organização do catálogo de serviços.

### 💰 Financeiro
- Registro de pagamentos.
- Controle de entradas e saídas.
- Acompanhamento de movimentações financeiras.
- Consulta do histórico financeiro.

## 🛠️ Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Linguagem utilizada no desenvolvimento do frontend |
| Reflex | Construção da interface da aplicação |
| Xano | Backend, APIs, autenticação e persistência de dados |
| OpenSpec | Organização e especificação das mudanças do projeto |
| GitHub Copilot | Assistente de IA utilizado como apoio durante o desenvolvimento |
| Git e GitHub | Versionamento e colaboração |

## 🏗️ Arquitetura do projeto

O projeto utiliza uma arquitetura separada entre frontend e backend, permitindo organizar a interface e as regras de negócio de maneira independente.

- **Frontend:** desenvolvido com Reflex, responsável pela interface e pela interação com os usuários.
- **Backend:** desenvolvido com Xano, responsável pelo gerenciamento de dados, autenticação, APIs e regras de negócio.

## 📂 Estrutura do repositório

```text
Projeto-PixelCode/
│
├── .github/       # Configurações do GitHub
├── .vscode/       # Configurações do ambiente de desenvolvimento
├── docs/          # Documentação e modelagem do projeto
├── frontend/      # Código-fonte da aplicação
├── openspec/      # Especificações e mudanças do sistema
├── xano/          # Organização dos recursos do backend
│
├── AGENTS.md      # Instruções e diretrizes do projeto
└── README.md      # Documentação principal
```

## 🚀 Como executar o projeto

### Pré-requisitos

- Python instalado.
- Git instalado.
- Acesso à configuração do backend no Xano.

### 1. Clone o repositório

```bash
git clone https://github.com/llimaarthur/Projeto-PixelCode.git
```

### 2. Acesse a pasta do frontend

```bash
cd Projeto-PixelCode/frontend
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente (arquivo `.env`)

A aplicação se comunica com o backend no Xano por meio de APIs. Os dados dessa conexão **não ficam no código**: são lidos de um arquivo `.env`, criado localmente na pasta `frontend/`.

Crie o arquivo `.env` e preencha com os valores do seu workspace no Xano:

```env
# URL base da API do Xano
XANO_API_URL=https://seu-workspace.xano.io/api:seu-grupo

# Chave/token de acesso à API (quando aplicável)
XANO_API_KEY=sua_chave_aqui
```

> **Atenção:** os nomes das variáveis acima são exemplos. Utilize os nomes exatamente como definidos no código do projeto.

**Boas práticas importantes:**

- 🔒 **Nunca envie o `.env` para o GitHub.** Ele contém credenciais e informações sensíveis.
- Garanta que o arquivo `.env` esteja listado no `.gitignore`.
- Se alguma credencial for exposta por engano, gere uma nova no Xano imediatamente.
- Cada pessoa que for executar o projeto deve criar o seu próprio `.env` local.
- Sem esse arquivo (ou com valores incorretos), a interface abre, mas as funcionalidades que dependem do backend, como login e consulta de dados, não funcionam.

### 5. Execute a aplicação

```bash
reflex run
```

Após iniciar, acesse o endereço exibido no terminal (por padrão, `http://localhost:3000`).

## 🤖 Uso de inteligência artificial

O desenvolvimento do PixelCode foi **assistido pelo GitHub Copilot**, utilizado como ferramenta de apoio em atividades como:

- Sugestão e complementação de código.
- Apoio na estruturação de componentes e integrações com a API.
- Auxílio na resolução de erros e na revisão de trechos de código.
- Apoio na elaboração da documentação.

Todo o conteúdo gerado foi revisado, testado e validado pela equipe, que permaneceu responsável pelas decisões de projeto, pela modelagem e pelas regras de negócio.

## 📚 Documentação

Para conhecer melhor a estrutura e as regras do sistema, consulte:

- [Visão geral do projeto](docs/project.overview.md)
- [Modelo de domínio](docs/domain-model.md)
- [Especificações do sistema](openspec/)
- [Instruções do projeto](AGENTS.md)

## 🎓 Contexto acadêmico

O PixelCode foi desenvolvido como projeto acadêmico do segundo semestre, com foco na aplicação prática dos conhecimentos adquiridos durante a formação em Análise e Desenvolvimento de Sistemas.

Durante o desenvolvimento, foram explorados conceitos como:

- Desenvolvimento de aplicações.
- Integração entre frontend e backend.
- Modelagem e organização de dados.
- Criação e consumo de APIs.
- Regras de negócio.
- Gerenciamento de variáveis de ambiente e segurança de credenciais.
- Controle de versão com Git e GitHub.
- Utilização de ferramentas de apoio ao desenvolvimento e inteligência artificial.

---

**PixelCode — Tecnologia e organização para transformar a gestão da sua barbearia.** 💈