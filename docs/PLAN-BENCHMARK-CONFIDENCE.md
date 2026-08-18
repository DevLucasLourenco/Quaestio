# Plano de implementação: benchmark e calibração de confiança

Status: implementado

## Fase 1 — Dataset inicial

- definir schema e versionamento;
- selecionar questões autorizadas;
- revisar respostas esperadas;
- balancear português, inglês, imagens, matemática, código e questões abertas.

Saída: dataset mínimo confiável.

## Fase 2 — Executor

- usar `evaluate_questions` como ponto de integração;
- executar em modo serial e em lote;
- salvar resultados estruturados, trace e versão da configuração;
- mascarar credenciais e evitar persistência de anexos sem necessidade.

Saída: execução reproduzível.

## Fase 3 — Métricas

- calcular acurácia geral;
- calcular métricas por categoria;
- medir cobertura e `needs_review`;
- separar abstenções por revisão de respostas efetivamente incorretas;
- comparar primary, secondary, consensus e verifier;
- registrar latência e custo estimado.

Saída: relatório quantitativo.

## Fase 4 — Calibração

- separar conjunto de ajuste e conjunto de validação;
- analisar faixas de confiança;
- ajustar caps e thresholds somente com evidência;
- validar que a taxa de excesso de confiança diminuiu;
- registrar a decisão no changelog do projeto.

## Fase 5 — Operação contínua

- executar o benchmark após mudanças de modelo, prompt ou pipeline;
- detectar regressões por categoria;
- manter histórico de resultados;
- definir critérios para ativação gradual em produção.

## Ordem recomendada

1. dataset;
2. executor;
3. métricas;
4. calibração;
5. regressão contínua.

## Implementação concluída

- loader JSONL com validação de gabarito;
- execução em lotes de até 500 itens;
- relatório estruturado com métricas segmentadas;
- `needs_review` excluído de `incorrect`, com `coverage` explícita;
- bins de confiança e cálculo de excesso de confiança;
- comando `quaestio-evaluate` adicionado ao pacote.
- dataset sintético `data/evaluation/benchmark-v1.jsonl` criado com 30 questões de matemática, engenharia de software e categorias de controle.
