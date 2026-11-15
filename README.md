# Wallet API — Capstone Self-Testing CI

API acadêmica em FastAPI, SQLAlchemy e SQLite. O Swagger apresenta os cinco endpoints sem precisar de frontend. Consulte [o relatório técnico](RELATORIO_TECNICO.md) e as [evidências locais](docs/evidencias/).

## Executar no Windows (PowerShell)

Abra o terminal na pasta do projeto. Use o Python 3.12 para reproduzir o ambiente do CI. Se o 3.12 não estiver instalado, `py --list` lista os disponíveis. O log inicial do Windows foi obtido com 3.15.2, mas a validação desta revisão foi feita com 3.12.14 em Linux.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ruff check src tests scripts performance
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-branch --cov-report=term-missing --cov-report=xml:coverage.xml --junitxml=junit.xml
.\.venv\Scripts\python.exe scripts/check_coverage.py coverage.xml
.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Se a sua pasta já tiver um `.venv` criado com outra versão, use-o para testar ou recrie o ambiente com 3.12 para comparar com o CI. Não é preciso ativar a venv. Abra [Swagger](http://127.0.0.1:8000/docs). Os testes usam bancos isolados. O servidor de demonstração usa `wallet.db` por padrão. O arquivo `.env.example` é uma referência, não é carregado pelo processo automaticamente.

| Método e rota | Uso |
|---|---|
| `POST /accounts` | Criar conta com titular e saldo inicial |
| `GET /accounts/{account_id}` | Consultar conta e saldo |
| `POST /transfers` | Transferir saldo com chave de idempotência |
| `GET /accounts/{account_id}/statement` | Filtrar extrato por `kind`, `start` e `end` |
| `GET /health` | Verificar se a API está respondendo |

## Demonstrar o webhook antifraude

Em um terminal, inicie o receptor fictício:

```powershell
.\.venv\Scripts\python.exe scripts/mock_antifraud.py
```

Em outro, inicie a API com o webhook e banco de demonstração (pare o processo que já usa a porta 8000):

```powershell
$env:DATABASE_URL = 'sqlite:///./wallet-demo.db'
$env:ANTIFRAUD_WEBHOOK_URL = 'http://127.0.0.1:9001/antifraud'
.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

No Swagger, crie uma conta com saldo e outra sem saldo. Faça uma transferência e repita exatamente o mesmo JSON com a mesma chave de idempotência. A primeira retorna `created: true`, a repetição retorna `created: false` com o mesmo ID. Só a primeira aparece como `transfer.confirmed` no terminal do receptor. O envio ocorre depois do commit, com timeout de 2 segundos. Se falhar, a API registra um aviso e mantém a transferência confirmada, sem retry automático. Sem URL configurada, não há chamada HTTP.

## Reproduzir a carga de 64 requisições

Use dois terminais na raiz do projeto. No primeiro, inicie uma instância instrumentada, com SQLite separado e webhook desativado:

```powershell
$env:DATABASE_URL = 'sqlite:///./wallet-load.db'
Remove-Item Env:ANTIFRAUD_WEBHOOK_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m uvicorn performance.observed_api:app --host 127.0.0.1 --port 8001 --no-access-log | Out-File -Encoding utf8 performance/results-server.txt
```

No segundo terminal, confirme que a API está pronta e execute:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
.\.venv\Scripts\python.exe -m locust -f performance/locustfile.py --headless -u 1 -r 1 -t 30s --host http://127.0.0.1:8001 --json-file performance/results-locust
```

Quando o Locust finalizar, pressione `Ctrl+C` no terminal do servidor para fechar o log. No segundo terminal, gere o resumo:

```powershell
.\.venv\Scripts\python.exe performance/summarize.py performance/results-locust.json performance/results-server.txt
```

O `-u 1` inicia um coordenador que abre uma barreira para **64 POSTs HTTP em paralelo**. A rotina ASGI mede o intervalo de cada requisição sem inserir atrasos e o resumo calcula o pico de intervalos sobrepostos. O teste falha se o pico for menor que 50, se houver erro ou se as contagens Locust/servidor divergirem. As duas contas são criadas antes da medição. Ao repetir, pare o servidor e reinicie com um novo log para evitar misturar rodadas.

## GitHub Actions

- `push` em `main`, `feature/**` ou `hotfix/**` e `pull_request` com destino a `main` acionam o job `quality` em Ubuntu e Python 3.12. Os limites independentes são 85% de linhas e 80% de branches.
- Abra **Actions → Wallet API - CI → execução → quality** para consultar os logs. Na página da execução, baixe **wallet-ci-reports** e confirme `coverage.xml`, `junit.xml` e `ci-*.log`.
- Após o primeiro CI verde, abra **Settings → Branches → Add branch protection rule** para `main`. Ative **Require a pull request before merging** e **Require status checks to pass before merging**. Selecione o check exibido para o job `quality` e habilite **Do not allow bypassing the above settings** se disponível. Se houver revisor autorizado, solicite revisão real e registre-a no PR. Não marque uma aprovação que não existiu.
- Confira pelo menos uma execução de cada gatilho e registre as URLs. A proteção e o upload só podem ser confirmados no GitHub.

[Proteção de branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule) · [Logs do workflow](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs) · [Download de artefatos](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)
