# Pendências que exigem ação do usuário

As escolhas de fornecedor estão fechadas: **Render Free**, **Turso**, **Groq `llama-3.1-8b-instant`** e **Google AI Studio `gemini-3.5-flash-lite`**. O backend foi escolhido como orquestrador do loop e consulta o CI existente por polling; não há workflow adicional nem callback.

## 1. Criar o serviço Render

Crie um Web Service no Render, plano Free, conectado ao repositório GitHub. Configure o diretório do backend e o comando de inicialização:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

O Render fornecerá uma URL HTTPS, que será usada como `BACKEND_URL` no GitHub Actions e no cliente Windows. Não configure Persistent Disk: o estado ficará no Turso.

No Environment do serviço Render, cadastre:

| Variável | Valor |
|---|---|
| `TURSO_DATABASE_URL` | URL `libsql://...` do banco Turso |
| `TURSO_AUTH_TOKEN` | Token de autenticação do banco Turso |
| `BACKEND_API_KEY` | Chave aleatória forte compartilhada com o cliente e o workflow |
| `GROQ_API_KEY` | Chave criada no console Groq |
| `GOOGLE_AI_API_KEY` | Chave criada no Google AI Studio |
| `GITHUB_TOKEN` | Fine-grained PAT descrito abaixo |

## 2. Criar o banco Turso

Crie uma conta em [Turso](https://turso.tech), crie um database e copie a URL libSQL para `TURSO_DATABASE_URL`. Gere um token de autenticação no painel/CLI do Turso e cadastre-o como `TURSO_AUTH_TOKEN` no Render. O backend cria o schema automaticamente na primeira inicialização.

## 3. Criar a chave Groq

Crie uma conta em [Groq Console](https://console.groq.com), gere uma API key e cadastre-a no Render como `GROQ_API_KEY`. O modelo confirmado é `llama-3.1-8b-instant`. Não coloque essa chave no GitHub Actions, no cliente Windows ou no repositório.

## 4. Criar a chave Google AI Studio

Acesse [Google AI Studio](https://aistudio.google.com/app/apikey), crie uma API key e cadastre-a no Render como `GOOGLE_AI_API_KEY`. O modelo confirmado é `gemini-3.5-flash-lite`. Não coloque essa chave no cliente Windows ou no repositório.

## 5. Criar o PAT mínimo do GitHub

Crie um fine-grained Personal Access Token com acesso somente ao repositório alvo e permissões:

- **Contents: Read and write**;
- **Pull requests: Read and write**;
- sem merge, bypass, administration, deletion ou workflows write.

Cadastre o token no Render como `GITHUB_TOKEN`. No GitHub Actions, o workflow usa o token automático para leitura; não copie o PAT para o repositório se não for necessário.

## 6. Criar e cadastrar a API key do backend

Gere uma chave aleatória forte. Cadastre-a no Render como `BACKEND_API_KEY` e como repository secret de mesmo nome em **GitHub → Settings → Secrets and variables → Actions**.

No Windows Credential Manager, crie uma credencial genérica com:

```text
Target: ExoAgenteCI.BackendApiKey
Password: valor de BACKEND_API_KEY
```

No cliente Windows, informe a URL HTTPS do Render no campo Backend. A chave não deve ser gravada em arquivo, XAML, `.csproj` ou JSON.

## 7. Secrets do GitHub Actions

Em **GitHub → Settings → Secrets and variables → Actions**, cadastre:

| Secret | Valor |
|---|---|
| `BACKEND_URL` | URL HTTPS do Web Service Render |
| `BACKEND_API_KEY` | Mesmo valor configurado no Render |
| `SONAR_TOKEN` | Token de consulta criado no SonarCloud |
| `SONAR_HOST_URL` | Normalmente `https://sonarcloud.io` |
| `SONAR_PROJECT_KEY` | Chave do projeto SonarCloud |

O workflow `.github/workflows/agent-job.yml` referencia esses nomes.

## 8. Pré-requisitos externos do loop implementado

O endpoint `POST /findings/{id}/process` já implementa branch/commit, polling do CI existente, timeout, revisão e abertura de PR. O repositório monitorado deve estar configurado para disparar seu CI ao receber push em branches e, se aplicável, executar SonarCloud também em branches. Não é criado workflow adicional nem callback.

## 9. Validação de produção

Depois de cadastrar as variáveis, confirme `GET /health` pela URL Render, teste uma chamada autenticada com `X-API-Key`, confirme `401` sem chave e execute `workflow_dispatch`. Verifique se o schema foi criado no Turso e se Jobs/Pendências sobrevivem a um restart do Render.
