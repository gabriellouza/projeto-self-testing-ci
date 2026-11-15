# Relatório técnico — Wallet API

## 1. Objetivo
API REST didática de conciliação simplificada e carteira digital, com automação de qualidade e testes em múltiplos níveis.

## 2. Requisitos funcionais (SRS)
- RF-01: criar conta com titular e saldo inicial não negativo.
- RF-02: consultar conta e saldo atual.
- RF-03: transferir valores positivos com até duas casas decimais.
- RF-04: recusar saldo insuficiente e contas inexistentes.
- RF-05: garantir idempotência por chave única; rejeitar reutilização com dados diferentes.
- RF-06: emitir extrato de débitos e créditos filtrado por tipo e intervalo.
- RF-07: integrar um notificador antifraude fictício, validado por mock.

## 3. Requisitos não funcionais
- RNF-01: transação atômica com atualização condicional de saldo e rollback em erros.
- RNF-02: cobertura >= 85% de linhas e >= 80% de branches.
- RNF-03: pipeline em push e pull request com lint e testes.
- RNF-04: artefatos de cobertura e resultado de testes no GitHub Actions.
- RNF-05: teste de carga com 50 usuários concorrentes, taxa de erro e latência média.

## 4. Arquitetura
FastAPI (controllers), regras financeiras (domain), orquestração de transferências (services), persistência SQLAlchemy/SQLite (repositories). Valores monetários usam Decimal/Numeric(18,2).

O débito usa UPDATE condicional (`balance >= amount`) dentro de transação. A chave de idempotência tem restrição UNIQUE no banco. SQLite é suficiente para demonstração local, mas sob carga pesada pode produzir bloqueios; PostgreSQL é recomendado para produção. O gateway antifraude é um adapter fictício (sem webhook HTTP real), com interações verificadas por mock.

## 5. Estratégia de branching
Trunk-Based Development: criar branches curtas `feature/...` ou `hotfix/...`, abrir PR para `main`, exigir CI verde e revisão antes de merge. Registrar duas correções/merges reais com histórico verificável.

## 6. Evidências de TDD — PREENCHER APÓS EXECUTAR
- Red: commit e log de teste falhando: [link]
- Green: commit e log do teste passando: [link]
- Refactor: commit de refatoração e log: [link]
- Correção/merge 1: [link]
- Correção/merge 2: [link]

## 7. Pirâmide de testes
- Unitários: validação e débito financeiro puro.
- Integração: persistência SQLite em memória, Mock do notificador (contagem/parâmetros) e Stub de validação cadastral.
- E2E: TestClient HTTP com criação de contas, transferência, extrato e erros.

## 8. CI e cobertura — PREENCHER APÓS EXECUTAR
- Execução GitHub Actions: [link]
- Cobertura de linhas: [valor real]
- Cobertura de branches: [valor real]
- Artefatos `coverage.xml` e `junit.xml`: [link]
- Branch protection/ruleset: [captura ou link]

## 9. Carga e resiliência — PREENCHER APÓS EXECUTAR
- Ferramenta: Locust, 50 usuários concorrentes, spawn-rate 10, 60 segundos.
- Comando: `locust -f performance/locustfile.py --headless -u 50 -r 10 -t 60s --host http://127.0.0.1:8000 --csv performance/results`
- Requisições totais: [valor]
- Taxa de erro: [valor]
- Latência média: [valor em ms]
- Observações sobre bloqueios SQLite: [resultado real]

## 10. Limitações
Não há autenticação de clientes nem integração bancária real. Notificações antifraude são simuladas; a entrega confiável de webhooks em produção exigiria outbox/retry. Não publicar credenciais em código.
