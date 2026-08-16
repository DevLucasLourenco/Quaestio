# Especificação: distinção entre consulta e passagem em embeddings

Status: implementado

## Objetivo

Usar corretamente o modelo de embeddings durante a indexação de materiais e durante a pesquisa, distinguindo documentos (`passage`) de consultas (`query`).

## Comportamento esperado

- documentos e seus metadados são indexados como `passage`;
- perguntas e buscas são embutidas como `query`;
- o provedor continua compatível com endpoints OpenAI-compatible;
- se o provedor não aceitar `input_type`, o sistema deve ter fallback explícito;
- documentos antigos com dimensão/modelo incompatível não devem produzir resultados silenciosamente incorretos.

## Persistência

O índice deve guardar metadados suficientes para identificar:

- modelo usado;
- dimensão do vetor;
- versão do formato;
- tipo de conteúdo indexado.

Ao trocar o modelo, o sistema deve solicitar ou executar reindexação controlada.

## Critérios de aceitação

- indexação envia `input_type=passage` quando suportado;
- busca envia `input_type=query` quando suportado;
- o fallback é coberto por teste;
- vetores incompatíveis são ignorados ou reindexados com aviso;
- a busca semântica continua com fallback para TF-IDF;
- resultados mantêm `document_id`, fonte, snippet e score auditáveis.

## Fora de escopo

- embeddings de imagem;
- reranking neural;
- alteração do contrato MCP de busca.

## Implementação concluída

O provedor envia `input_type=passage` na indexação e `input_type=query` na busca. O índice persistido guarda modelo, dimensão e versão de formato; vetores de modelo incompatível são reindexados quando um provedor está disponível.
