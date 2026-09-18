# Exo-esqueleto do Agente CI/SonarQube

Repositório com deployment separado: `backend/` (API, domínio e persistência) e `windows-client/` (WPF nativo).

## Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
export TURSO_DATABASE_URL='libsql://seu-banco.turso.io'
export TURSO_AUTH_TOKEN='seu-token-turso'
export BACKEND_API_KEY='chave-local-de-desenvolvimento'
uvicorn app.main:app --reload
```

## Cliente Windows

Em uma máquina Windows com .NET 8 SDK:

```powershell
dotnet build windows-client/ExoAgente.Windows.csproj
```

O cliente aponta por padrão para `http://localhost:8000` e permite alterar o backend na própria tela.

Consulte [Contrato de API.md](Contrato%20de%20API.md) e [Decisões de implementação.md](Decisões%20de%20implementação.md).
Consulte também [Pendências do usuário](PENDENCIAS-DO-USUARIO.md) e [Decisões de fornecedores](DECISÕES%20DE%20FORNECEDORES.md).
