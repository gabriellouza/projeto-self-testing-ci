# Relatório técnico — Wallet API

**Gabriel Alves Louza · Engenharia de Software · UniEVANGÉLICA**

Integração Contínua de Software · Projeto Capstone: 7 Dias

## 1. Objetivo e requisitos

Construir uma API REST didática para movimentação de saldo e extrato, demonstrando transações consistentes, automação de qualidade e evidências verificáveis. A referência principal é o enunciado **Atividade Prática Avaliativa (Projeto Capstone: 7 Dias)**, pp. 1–3. O material das aulas é complementar.

| ID | Requisito funcional | Evidência local |
|---|---|---|
| RF-01 | Criar conta com titular e saldo inicial não negativo | Integração e fluxo E2E |
| RF-02 | Consultar conta e saldo atual | Fluxo E2E |
| RF-03 | Transferir valor positivo com precisão de centavos | Unitários, integração e E2E |
| RF-04 | Rejeitar saldo insuficiente, contas inexistentes e transferência para a mesma conta | Integração e disputa de saldo |
| RF-05 | Repetir a mesma chave sem novo débito, extrato ou notificação e rejeitar reuso com dados conflitantes | Integração e disputas concorrentes |
| RF-06 | Consultar extrato por data e tipo de lançamento | E2E com quatro datas e limites inclusivos |
| RF-07 | Enviar confirmação a um webhook antifraude fictício configurável | Mock do HTTPX e demonstração HTTP local |

| ID | Requisito não funcional | Verificação |
|---|---|---|
| RNF-01 | Manter débito, crédito, transferência e extrato atômicos | SQLite, contas e lançamentos verificados após disputas |
| RNF-02 | Cobertura independente ≥ 85% de linhas e ≥ 80% de branches | Coverage.py e gate executados localmente |
| RNF-03 | Rodar lint e testes em push/PR e bloquear merges se o CI não passar | Workflow validado localmente. Execução e proteção remotas pendentes |
| RNF-04 | Publicar cobertura, JUnit e logs em um artefato de CI | Cinco arquivos gerados localmente. Publicação remota pendente |
| RNF-05 | Medir ≥ 50 POSTs simultâneos de transferência, erros e latência | 64 requisições sobrepostas no servidor em rodada local |

## 2. Arquitetura preservada

- **`src/controllers`** mantém os contratos das rotas e traduz erros de domínio em respostas HTTP.
- **`src/domain`** contém entidades e regras de valor e saldo, usando `Decimal` e colunas `Numeric(18,2)`.
- **`src/services`** coordena cadastro e transferência. Mantém a atualização condicional do saldo (`balance >= amount`), a restrição única da chave e a reversão em caso de erro. O notificador HTTP roda apenas no caminho de transferência nova, depois do commit.
- **`src/repositories`** abre sessões SQLAlchemy e configura SQLite. A contabilidade e as rotas não foram reescritas. O webhook tem timeout de 2 segundos e falha não reverte a transação confirmada. Não há retry nem confirmação de entrega durável.

## 3. Pirâmide de testes e evidência local

- **7 unitários:** lógica pura de validação de valores e débito.
- **12 de integração:** SQLite em memória para cenários comuns e arquivo temporário com conexões independentes para concorrência. Uma barreira posicionada imediatamente antes do débito faz as requisições disputarem o saldo ou a mesma chave. Foram verificados status, IDs, saldos finais, os dois lançamentos e uma única notificação após o commit. A variante com saldo sobrando também atravessa a restrição única e verifica o rollback do segundo débito.
- **2 E2E:** requisições pelo FastAPI TestClient com criação de contas, transferência, extrato e respostas de erro. Datas controladas mostram que o filtro inclui os dois limites e exclui os lançamentos anteriores e posteriores.
- **Mock:** verifica uma única chamada HTTP, URL, payload e timeout. Um segundo cenário simula timeout e confirma que a transferência já persistida não é revertida. **Stub:** responde sempre `False` na validação cadastral e não verifica interações.

| Execução local | Testes | Linhas | Branches | Ruff |
|---|---:|---:|---:|---|
| Windows, log anterior fornecido, Python 3.15.2 | 17 | 97,53% | 92,11% | F401 apontado no log seguinte |
| ZIP original reexecutado, Linux/Python 3.12.14 | 17 | 97,58% | 92,11% | F401 confirmado |
| Base revisada, Linux/Python 3.12.14 | 21 | 99,51% | 95,45% | Aprovado |

A base revisada passou com os mesmos comandos Bash do workflow. A cobertura revisada inclui `src/repositories/database.py`, antes excluído, e mede todo `src`. O gate compara as contagens exatas do XML, sem arredondar os limites. Foi verificado que 85%/80% passam e que ficar abaixo em qualquer das métricas falha sozinho. O TestClient ainda emite um aviso de depreciação do HTTPX na versão instalada, sem falha de teste. Nenhum resultado local é execução do Actions.

Evidências em [docs/evidencias](docs/evidencias/). O [teste HTTP do webhook](docs/evidencias/webhook/http.txt) registrou duas respostas HTTP 201 para a mesma chave (primeira nova, segunda repetida) e um único POST ao receptor, com resposta 204.

## 4. Desempenho local

Execução com Locust 2.47.0 e Uvicorn, loopback, um processo servidor, SQLite separado e webhook desativado. Um coordenador liberou 64 requisições `POST /transfers` na mesma barreira, todas para o mesmo par de contas, com chaves distintas. A instrumentação ASGI mediu a sobreposição entre início e fim de cada requisição sem introduzir atraso. O limite de execução era 30 s, e a rodada terminou automaticamente após a rajada. A criação das contas não compõe as métricas.

| Métrica | Medição |
|---|---:|
| Requisições ao endpoint | 64 |
| Pico simultâneo observado no servidor | 64 |
| Respostas HTTP 201 | 64 |
| Erros / taxa de erro | 0 / 0,00% |
| Latência média pelo Locust | 213,04 ms |
| Saldos finais | 99.936,00 na origem e 64,00 no destino |
| Lançamentos persistidos | 64 débitos e 64 créditos |

A primeira tentativa também completou 64 respostas 201, mas o CSV periódico não gravou a rodada curta. A exportação foi trocada para o JSON final do Locust e o pool do gerador foi ajustado para as 64 conexões. A rodada acima usa o exportador final. Não houve bloqueio reportado pelo SQLite, timeout nem falha HTTP nessa rodada. Isso comprova a rajada local, não capacidade de produção ou carga sustentada.

Evidências: [resumo](docs/evidencias/carga/summary.json), [intervalos ASGI](docs/evidencias/carga/servidor.txt), [estatísticas Locust](docs/evidencias/carga/locust-stats.json) e [conferência da persistência](docs/evidencias/carga/database-check.txt).

## 5. Git, TDD e CI remoto — pendentes de publicação

[Repositório de destino](https://github.com/gabriellouza/projeto-self-testing-ci). A revisão foi feita a partir do ZIP, sem inicializar Git, publicar código, criar commits ou abrir PRs.

- **Trunk-Based:** branches curtas a partir de `main` com PRs revisados, mensagens de commit claras e check obrigatório. Sugestões de merges reais: `feature/concorrencia-extrato` para testes e evidências do núcleo, `feature/webhook-antifraude` para o gateway. O roteiro de publicação do pacote indica os arquivos de cada PR.
- **TDD:** o ajuste de validação para aceitar zeros à direita de centavos (por exemplo, `1.2300`) não está na base. Um ensaio isolado confirmou duas falhas esperadas por `DomainError` no Red e 23 testes passando em Green e Refactor. Esse ensaio não é histórico Git. Os três commits devem ser feitos na ordem do roteiro, preservando o Red no histórico.
- **Actions:** workflow aprovado no actionlint. Gatilhos de push e pull request e caminhos do artefato conferidos localmente. Nenhum check obrigatório, execução remota ou upload foi confirmado.

Após publicar, registre no relatório e no PDF:

| Evidência a anexar | Situação |
|---|---|
| PR 1 e PR 2 mesclados, com revisão real quando realizada | Pendente |
| Commits Red, Green e Refactor, com logs associados | Pendente |
| URLs das execuções de push e pull request, com job `quality` | Pendente |
| Página da execução que contém `wallet-ci-reports` e confirmação de download | Pendente |
| Regra de proteção da `main` e evidência do check obrigatório | Pendente |
| Permalinks das evidências locais versionadas (CI, carga e webhook) | Pendente de publicação |

Antes de enviar, confirme que o professor consegue acessar os links. No AVA, envie apenas o PDF individual atualizado.
