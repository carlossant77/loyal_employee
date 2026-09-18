# Contrato de API

Base URL padrão: `http://localhost:8000` (configurável no cliente Windows). JSON em todos os endpoints.

## Autenticação

Todos os endpoints, exceto `/health`, exigem o cabeçalho `X-API-Key`. O backend compara o valor com a variável de ambiente `BACKEND_API_KEY`; ausência, valor vazio ou valor incorreto resulta em HTTP `401`. A documentação e o OpenAPI permanecem públicos para facilitar diagnóstico.

```http
X-API-Key: <valor de BACKEND_API_KEY>
```

| Método | Endpoint | Finalidade |
|---|---|---|
| GET | `/health` | Verificação de disponibilidade |
| GET | `/jobs` | Histórico das últimas 100 execuções |
| POST | `/jobs` | Registra uma execução e suas pendências; ignora correlações em `aguardando_merge` |
| GET | `/findings?status=` | Lista pendências, opcionalmente filtradas por status |
| GET | `/scope` | Obtém a política persistida |
| PUT | `/scope` | Substitui a política persistida |
| POST | `/findings/{id}/process` | Executa Líder → branch/commit → polling CI/Sonar → Revisor → PR |

## POST `/jobs`

```json
{"repository":"org/repo","ref":"main","findings":[{"origin":"ci","category":null,"path":"src/a.py","test_name":"test_a","failure_type":"AssertionError"},{"origin":"sonar","category":"reliability","path":"src/b.py","sonar_key":"AX123"}]}
```

Resposta: `{"job_id":"uuid","status":"completed","findings_persisted":2}`. Findings CI sem categoria ficam `skipped` com a política padrão, conforme documentado em [Decisões de implementação](Decisões%20de%20implementação.md).

## Política de escopo

```json
{"category":{"allowlist":["reliability"],"denylist":[]},"path":{"allowlist":["src/"],"denylist":["src/generated/"]},"origin":{"allowlist":["ci","sonar"],"denylist":[]},"combination":"AND"}
```

Status possíveis: `não_corrigida`, `skipped`, `aguardando_merge`, `corrigida`. Não há endpoint de merge; a confirmação de merge deverá ser recebida por integração GitHub e aplicada por uma transição controlada.

## Processamento de uma Pendência

`POST /findings/{id}/process` só aceita uma Pendência em `não_corrigida`. O Líder produz o patch; o backend cria branch e commit, mas não abre PR. O status passa para `em_validacao`. O backend consulta periodicamente os workflow runs do GitHub Actions filtrados pela branch, com timeout configurável no serviço (padrão de 20 minutos). CI verde e aprovação do Revisor abrem o PR e mudam o status para `aguardando_merge`. CI vermelho, rejeição do Revisor ou timeout removem a branch e retornam a Pendência a `não_corrigida`, registrando o motivo.

Para usar a validação de Sonar neste loop, o repositório monitorado **deve estar configurado para executar SonarCloud também em branches de correção** e expor `SONAR_HOST_URL`, `SONAR_TOKEN` e `SONAR_PROJECT_KEY`. O backend não altera essa configuração. Sem análise de branch, a validação considera apenas o resultado do CI e a verificação disponível ao Revisor.

Não é criado workflow adicional nem callback: o workflow de CI existente é disparado pelo push na branch, e o backend faz polling da API do GitHub Actions.
