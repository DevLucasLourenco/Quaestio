# Plano de implementação: modernização do protocolo MCP

Status: implementado

## Resultado esperado

Entregar um servidor Quaestio MCP moderno, funcional em stdio, baseado na revisão `2026-07-28`, integrado ao SDK Python atual e com contratos de ferramentas suficientemente descritos para clientes MCP.

Este plano é 1:1 com `SPEC-MCP-PROTOCOL-MODERNIZATION.md`. Cada fase abaixo implementa diretamente uma parte da especificação correspondente.

## Fase 1 — Inventário e contrato público

- mapear todas as ferramentas registradas em `TOOL_HANDLERS`;
- identificar o modelo de saída público de cada ferramenta;
- separar schemas de entrada, schemas de saída e metadados MCP;
- definir constantes para versão do protocolo, nome, versão e instruções do servidor;
- definir a ordem determinística oficial das ferramentas;
- remover dependência de valores de versão duplicados no código.

Saída: contrato MCP centralizado e testável, sem alteração de comportamento de domínio.

## Fase 2 — Migração do SDK MCP

- inspecionar a API disponível na versão moderna do SDK;
- substituir a integração antiga baseada em `FastMCP` pela API moderna recomendada;
- limitar a dependência `mcp` à linha moderna adotada;
- manter a inicialização opcional somente se houver motivo técnico para o fallback próprio;
- garantir que todos os handlers registrados mantenham nomes, argumentos e descrições corretos;
- validar que exceções de handlers sejam convertidas em resultados MCP controlados.

Saída: servidor executando pelo SDK moderno em stdio.

## Fase 3 — Descoberta moderna

- implementar `server/discover`;
- aceitar e validar `_meta` sem depender de campos desconhecidos;
- retornar versão suportada, identidade, capacidades e instruções;
- declarar somente `tools` e `listChanged: false`;
- remover do caminho moderno as referências a handshake e métodos obsoletos;
- criar resposta estável e serializável para clientes com diferentes capacidades declaradas.

Saída: cliente MCP consegue descobrir corretamente o Quaestio antes de listar ou chamar ferramentas.

## Fase 4 — Listagem e schemas das ferramentas

- atualizar `tools/list` para o contrato moderno;
- adicionar `resultType: "complete"`;
- adicionar `outputSchema` às ferramentas;
- definir schemas para respostas de sucesso e variantes de erro controlado;
- incluir metadados como título, descrição e anotações somente quando forem verdadeiros;
- preparar o retorno para cursor e cache sem introduzir paginação artificial;
- verificar que nenhuma informação sensível seja incluída nos schemas.

Saída: clientes MCP conseguem apresentar e interpretar as ferramentas e seus resultados com precisão.

## Fase 5 — Chamada de ferramentas e resultados

- atualizar `tools/call` para produzir o envelope moderno;
- validar argumentos antes do dispatch;
- preservar `structuredContent` e o texto serializado equivalente;
- garantir `resultType: "complete"` em resultados finais;
- padronizar erros de ferramenta, ferramenta inexistente, argumentos inválidos e exceções inesperadas;
- manter `isError` separado de estados de negócio como `needs_review`;
- impedir que stack traces, tokens ou dados de anexos apareçam na resposta.

Saída: chamadas reais mantêm o contrato MCP mesmo quando o domínio falha de forma controlada.

## Fase 6 — Transporte stdio e encerramento

- garantir uma mensagem JSON-RPC por linha;
- verificar que stdout nunca receba logs;
- garantir flush após cada resposta;
- tratar JSON inválido de maneira determinística;
- testar stdin fechado e encerramento limpo;
- revisar logs de inicialização, chamada, duração e falha para remover dados sensíveis.

Saída: processo confiável para ser iniciado e supervisionado por qualquer cliente MCP local.

## Fase 7 — Testes de conformidade

- testar `server/discover` com `_meta` completo, parcial e desconhecido;
- testar capacidades declaradas;
- testar `tools/list`, ordem, schemas e `resultType`;
- testar chamada de ferramenta com sucesso;
- testar argumentos inválidos, ferramenta inexistente e exceção do handler;
- testar preservação de `structuredContent` e `content`;
- testar JSON inválido e linhas vazias no stdio;
- testar encerramento por EOF;
- testar ausência de segredos nos logs e respostas;
- executar a suíte de domínio já existente para confirmar que a modernização não altera a lógica das ferramentas.

Saída: evidência automatizada de conformidade do protocolo e regressão controlada.

## Fase 8 — Documentação e operação

- atualizar o README para a revisão `2026-07-28`;
- documentar instalação do SDK moderno;
- documentar execução stdio e o contrato de descoberta;
- documentar exemplos de `server/discover`, `tools/list` e `tools/call`;
- registrar explicitamente que HTTP, resources e prompts não fazem parte desta versão;
- revisar exemplos para não sugerirem métodos legados;
- registrar limitações operacionais e política `needs_review`.

Saída: documentação reproduzível e coerente com o servidor entregue.

## Ordem de execução

1. inventário e contrato público;
2. migração do SDK;
3. descoberta moderna;
4. listagem e schemas;
5. chamada e resultados;
6. transporte stdio;
7. testes de conformidade;
8. documentação e validação final.

## Estratégia de versionamento

Realizar commits pequenos e independentes, preferencialmente nesta ordem:

1. `refactor: centralize MCP protocol metadata`;
2. `feat: migrate to modern MCP Python SDK`;
3. `feat: add modern MCP server discovery`;
4. `feat: expose modern tool schemas`;
5. `feat: modernize MCP tool results`;
6. `test: add MCP protocol conformance coverage`;
7. `docs: update MCP protocol guidance`.

Cada commit deve manter o projeto executável e passar os testes relevantes. O commit de documentação deve ocorrer somente depois de validar o comportamento final.

## Validação final

- `python -m compileall src tests`;
- `pytest`;
- execução do entrypoint `quaestio` com entrada stdio real;
- inspeção manual de uma descoberta, uma listagem e uma chamada de ferramenta;
- confirmação de que stdout contém somente mensagens MCP;
- confirmação de que nenhum segredo aparece nos artefatos de teste;
- revisão final contra todos os critérios de aceitação da especificação.

## Riscos e mitigação

### Mudança da API do SDK

Mitigação: fixar a linha moderna do SDK, testar a inicialização em processo real e evitar dependência de APIs internas.

### Schemas divergentes da saída real

Mitigação: gerar ou validar schemas a partir dos modelos públicos e cobrir cada ferramenta com exemplos de saída.

### Erros contaminando stdout

Mitigação: centralizar logging em stderr e adicionar teste que analisa byte a byte a saída do processo.

### Crescimento do contrato de ferramentas

Mitigação: manter a lista determinística, definir schemas explicitamente e separar mudanças de protocolo de mudanças de domínio.

## Fora de escopo do plano

- implementação de HTTP;
- suporte a protocolo legado;
- criação de resources ou prompts;
- alteração do pipeline de Selenium;
- troca ou avaliação de provedores de LLM;
- criação de clientes MCP.
