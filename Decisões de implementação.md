# Decisões de implementação

## Hospedagem

O backend será hospedado no **Render Web Service, plano Free**, com HTTPS gerenciado. O Render Free tem compute limitado e filesystem efêmero, portanto não deve armazenar o estado do sistema em arquivo local.

## Persistência

Foi escolhido **Turso (libSQL)** como banco remoto. A camada `TursoStore` usa `libsql-client` e mantém o schema SQL de Jobs, Pendências e Escopo. O backend exige `TURSO_DATABASE_URL` e `TURSO_AUTH_TOKEN` no ambiente de produção. URLs `file:` são aceitas somente para testes locais isolados.

A combinação Render Free + Turso resolve a limitação do filesystem: o serviço pode dormir/reiniciar/redeployar sem perder o estado, pois os dados ficam no banco remoto. Não há mais necessidade de Persistent Disk no Render.

## Modelo do Líder Operacional

O fornecedor confirmado é **Groq**, usando o modelo **`llama-3.1-8b-instant`**. A chave deve ser fornecida via `GROQ_API_KEY`. `GroqLeader` está implementado e é usado automaticamente quando essa variável está presente; sem ela, o backend cai para `StubLeader` (que sempre rejeita), nunca falha silenciosamente.

## Modelo do Revisor

O fornecedor confirmado é **Google AI Studio**, usando o modelo **`gemini-3.5-flash-lite`**. A chave deve ser fornecida via `GOOGLE_AI_API_KEY`. `GoogleReviewer` está implementado e é usado automaticamente quando essa variável está presente; sem ela, o backend cai para `StubReviewer` (que sempre rejeita).

## Agendamento

A execução agendada será um workflow do GitHub Actions, coerente com a decisão arquitetural de que CI roda no GitHub Actions. O arquivo `.github/workflows/agent-job.yml` consulta GitHub Actions/SonarCloud e chama o backend.

## Execução do loop de correção

Foi escolhido o **backend como orquestrador por endpoint** (`POST /findings/{id}/process`), sem criar workflow adicional ou endpoint de callback. O push na branch criada dispara o CI já existente do repositório monitorado; o backend consulta a API do GitHub Actions filtrando pela branch até conclusão ou timeout. O timeout padrão é 20 minutos e é tratado como reprovação, com remoção da branch e retorno a `não_corrigida`. Essa abordagem reduz componentes e evita transportar patches por um segundo workflow, mantendo a execução de testes no ambiente já configurado do repositório.

O repositório monitorado precisa executar SonarCloud em branches de correção para que o resultado seja considerado no Revisor. Essa é uma exigência externa; o backend não cria nem altera a configuração Sonar do repositório.

## Interface Windows

WPF com .NET 8 foi escolhido. É uma aplicação Windows nativa, sem Electron, navegador embutido ou empacotamento de PWA. O cliente consome o backend via HTTP. As notificações usam `Microsoft.Toolkit.Uwp.Notifications` para emitir Windows Toasts. Essa biblioteca exige TFM Windows versionado; por isso o projeto usa `net8.0-windows10.0.19041.0` e `TargetPlatformMinVersion` `10.0.17763.0`.

## Regra de Escopo

A política persistida usa três eixos (`category`, `path`, `origin`), cada um com allowlist e denylist, e uma combinação explícita `AND` ou `OR`. Denylist tem precedência no eixo. Em `AND`, todos os eixos devem casar; em `OR`, ao menos um deve casar. O backend carrega a política persistida; o Líder não decide o escopo.

## Decisão explícita para achados sem `category`

Foi escolhida a opção **(a), fail-safe intencional**. `category` é um conceito do Sonar; achados de CI normalmente chegam com `category=None`. Como a política padrão não contém uma autorização específica para categoria de CI, o eixo de categoria não corresponde e o achado CI fica fora do escopo (`skipped`). Assim, nada de CI é encaminhado para correção automática até que a política persistida seja configurada explicitamente para permitir esse caso.

## Autenticação da API

A API usa o header `X-API-Key`, comparado com `BACKEND_API_KEY`. O middleware é fail-closed: se a variável não existir no servidor, qualquer endpoint protegido retorna `401`; não há fallback inseguro. `/health`, documentação OpenAPI e Redoc permanecem públicos para diagnóstico. O cliente Windows lê a chave do Windows Credential Manager, no target `ExoAgenteCI.BackendApiKey`, nunca de texto plano.

## PAT do GitHub e abertura de PR

`GitHubPullRequestProvider` usa a GitHub REST API e lê `GITHUB_TOKEN` do ambiente. O PAT destinado a esse provider deve ter somente **Contents: Read and write** e **Pull requests: Read and write** no repositório alvo, sem permissões de merge, bypass, administração, exclusão ou workflows write. O provider implementa branch, blobs, árvore, commit e abertura de PR, mas não possui método de merge.

O `GitHubPullRequestProvider` está integrado ao fluxo real via `ValidationOrchestrator` (`POST /findings/{id}/process`): cria a branch, commita o patch do Líder, e — só após o CI da branch ficar verde e o Revisor aprovar — abre o PR. Continua sem método de merge, por desenho.

## Suposições

Autenticação multiusuário continua fora do escopo (uso pessoal, uma máquina). O loop completo Líder → validação por CI real → Revisor → PR está implementado e testado (ver "Execução do loop de correção"). Nenhum endpoint de merge existe por desenho, em nenhuma camada do sistema.
