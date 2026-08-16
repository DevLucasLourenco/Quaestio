# Plano de implementação: avaliação multilíngue e multimodal

Status: implementado

## Fase 1 — Formato do dataset

- definir formato JSONL ou equivalente;
- criar schema de validação;
- separar dados de entrada, gabarito e metadados;
- definir política para imagens e arquivos de teste.

Saída: dataset versionado e validável.

## Fase 2 — Dataset inicial anotado

- montar um conjunto pequeno e balanceado;
- incluir exemplos positivos, ambiguidades e falhas de OCR;
- revisar gabaritos independentemente;
- remover dados pessoais e conteúdo de avaliações ativas.

Saída: primeira versão do conjunto de avaliação.

## Fase 3 — Executor de avaliação

- chamar o MCP para cada item;
- salvar apenas resultados estruturados e métricas;
- registrar o `trace` para diagnóstico;
- permitir repetir a avaliação com diferentes configurações.

Saída: avaliação reproduzível.

## Fase 4 — Relatório

- calcular métricas gerais e por categoria;
- separar falhas de tradução, OCR, solver e consenso;
- comparar primary, secondary e consensus;
- medir latência e custo;
- produzir recomendações de configuração.

## Ordem recomendada

1. schema;
2. dataset pequeno;
3. executor;
4. relatório por categoria;
5. expansão do conjunto;
6. decisão de ativação padrão.

## Implementação concluída

- schema `EvaluationItem` e `EvaluationDataset` criado;
- dataset JSONL sintético inicial adicionado;
- executor `quaestio-evaluate` criado;
- métricas gerais, por categoria, por idioma e por faixa de confiança implementadas.
