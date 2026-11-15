# Wallet API — Capstone Self-Testing CI

Projeto acadêmico FastAPI com contas, transferências idempotentes, extratos, testes e GitHub Actions.

## Windows / PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest --cov=src --cov-branch --cov-report=xml:coverage.xml
python scripts/check_coverage.py coverage.xml
python -m uvicorn src.main:app --reload
```

Abra http://127.0.0.1:8000/docs para testar a API. Execute `python -m ruff check src tests` para lint.

## Teste de carga
Em outro terminal, com a API aberta:
```powershell
locust -f performance/locustfile.py --headless -u 50 -r 10 -t 60s --host http://127.0.0.1:8000 --csv performance/results
```

## Histórico acadêmico
Não apresente os commits do ZIP inicial como evidência de Red-Green-Refactor. Para comprovar TDD, realize um ciclo genuíno numa nova funcionalidade: primeiro commit de teste falhando, segundo commit de implementação, terceiro commit de refatoração, cada um com logs. Faça PRs e registre links no RELATORIO_TECNICO.md.
