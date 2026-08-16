# Plano de implementação: distinção entre consulta e passagem em embeddings

Status: implementado

## Fase 1 — Contrato do provedor

- ampliar o protocolo para receber o tipo de entrada;
- manter compatibilidade com dublês existentes;
- definir resposta e erros para provedores que não aceitam `input_type`.

Saída: abstração capaz de diferenciar indexação e pesquisa.

## Fase 2 — Integração com a base

- usar `passage` em `add_document`;
- usar `query` em `search`;
- preservar fallback TF-IDF;
- adicionar metadados do modelo e dimensão ao armazenamento.

Saída: índice semanticamente consistente.

## Fase 3 — Migração e compatibilidade

- detectar índices antigos;
- emitir aviso de reindexação;
- evitar mistura de vetores de modelos diferentes;
- documentar o procedimento de reindexação.

## Fase 4 — Avaliação

- testar consultas com pouco ou nenhum overlap lexical;
- comparar TF-IDF e embeddings;
- medir precisão do top-k;
- validar o comportamento quando a API está indisponível.

## Ordem recomendada

1. protocolo;
2. base de conhecimento;
3. metadados e migração;
4. testes de fallback;
5. avaliação de relevância.

## Implementação concluída

- protocolo de embeddings ampliado com `input_type`;
- indexação e busca usam tipos distintos;
- índice persistido versionado com modelo e dimensão;
- índices antigos continuam carregáveis;
- fallback TF-IDF permanece disponível;
- testes cobrem chamadas e metadados.
