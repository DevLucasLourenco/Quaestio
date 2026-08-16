# Especificação: modernização do protocolo MCP

Status: implementado

## Objetivo

Atualizar o Quaestio para operar como um servidor MCP moderno, alinhado à revisão `2026-07-28` da especificação oficial, utilizando o SDK Python atual e mantendo o transporte stdio como canal principal para execução local.

Como o Quaestio ainda não possui usuários ou clientes dependentes da implementação atual, esta especificação não preserva fluxos legados. A implementação deve priorizar o contrato moderno, a clareza dos metadados e a previsibilidade para clientes MCP atuais.

## Referências oficiais

- [MCP Specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [Server discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [stdio transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
- [Python SDK oficial](https://github.com/modelcontextprotocol/python-sdk)

## Decisões arquiteturais

- a revisão MCP adotada será `2026-07-28`;
- o servidor será stateless no transporte stdio;
- `server/discover` será o ponto de descoberta do servidor;
- `initialize`, `notifications/initialized` e `ping` não farão parte do contrato moderno;
- o servidor declarará apenas a capacidade `tools`;
- `resources` e `prompts` ficam fora do escopo desta atualização;
- o transporte HTTP não será implementado nesta etapa;
- o SDK será atualizado para a linha moderna e terá versão limitada para evitar mudanças silenciosas de API;
- stdout conterá somente mensagens MCP válidas; logs continuarão exclusivamente em stderr;
- a ordem das ferramentas será determinística;
- todos os resultados de ferramentas continuarão oferecendo texto serializado para compatibilidade de apresentação e também `structuredContent` para clientes que suportam conteúdo estruturado.

## Contrato de descoberta

O servidor deve responder a `server/discover` com:

- versões de protocolo suportadas, contendo `2026-07-28`;
- identidade do servidor, com nome `quaestio` e versão derivada do pacote;
- capacidade `tools`;
- instruções resumidas sobre a política de confiabilidade do Quaestio;
- metadados suficientes para o cliente entender que o servidor resolve, verifica, classifica e processa questões com anexos.

O servidor deve aceitar os metadados definidos pela especificação no campo `_meta`, incluindo versão de protocolo, identidade do cliente e capacidades do cliente. Metadados desconhecidos não devem causar falha quando não forem necessários ao processamento.

## Contrato de ferramentas

### Listagem

`tools/list` deve:

- retornar todas as ferramentas em ordem determinística;
- declarar `resultType: "complete"` quando a listagem estiver completa;
- estar preparada para paginação por cursor, mesmo que o conjunto atual caiba em uma única resposta;
- declarar os schemas de entrada em JSON Schema 2020-12;
- declarar `outputSchema` para cada ferramenta sempre que o formato de saída for conhecido;
- informar descrições objetivas e orientadas à operação;
- não expor chaves, URLs privadas, prompts internos ou detalhes sensíveis da configuração.

### Execução

`tools/call` deve:

- validar o nome da ferramenta e os argumentos antes da execução;
- retornar `resultType: "complete"` quando houver resultado final;
- usar `isError: true` para falhas de execução da ferramenta sem transformar erros de negócio em respostas MCP inválidas;
- preservar `structuredContent` como objeto JSON;
- incluir uma representação textual serializada do mesmo resultado em `content`;
- retornar mensagens de erro úteis, sem credenciais, payloads privados ou stack traces;
- manter a política do Quaestio de não inventar respostas quando não houver evidência suficiente.

Resultados que necessitem de nova entrada do cliente não fazem parte da primeira implementação. Caso sejam necessários futuramente, deverão seguir o contrato `input_required` da revisão adotada, sem criar um protocolo próprio.

### Schemas de saída

Os schemas de saída devem refletir os modelos públicos já utilizados pelo serviço, incluindo, quando aplicável:

- resposta proposta e resposta final;
- confiança e classificação de confiabilidade;
- avisos e necessidade de revisão;
- rastreabilidade por pergunta;
- fontes retornadas pela busca de material;
- resultado de OCR, parsing, análise, compilação e execução isolada.

Quando uma ferramenta retornar uma união de formatos, o schema deve documentar explicitamente os campos comuns e as variantes possíveis.

## Capacidades declaradas

O servidor deve declarar:

```json
{
  "tools": {
    "listChanged": false
  }
}
```

`listChanged` será `false` porque a lista de ferramentas é definida no carregamento do processo e não muda durante a sessão.

O servidor não deve declarar capacidades de recursos, prompts, sampling, roots ou logging enquanto não houver implementação real desses recursos.

## Transporte stdio

O transporte stdio deve cumprir estas regras:

- uma mensagem JSON-RPC por linha;
- nenhuma mensagem parcial ou com newline embutido no stdout;
- somente respostas e notificações MCP no stdout;
- logs operacionais exclusivamente no stderr;
- flush imediato após cada resposta;
- encerramento limpo quando o stdin for fechado;
- mensagens JSON inválidas devem gerar erro JSON-RPC bem formado sem derrubar o processo imediatamente.

## Dependência do SDK

O projeto deve migrar para a API moderna do SDK Python MCP e limitar a dependência à linha principal adotada, evitando `mcp>=1.0.0` sem limite superior. A integração deve continuar opcional: o fallback próprio só deve permanecer se ele implementar o mesmo contrato moderno e for necessário para desenvolvimento ou diagnóstico.

Se o SDK moderno for obrigatório para a execução normal, isso deve ser documentado claramente no README e coberto por teste de inicialização.

## Segurança e confiabilidade

- nenhum segredo deve aparecer em stdout, stderr ou respostas MCP;
- entradas de ferramentas devem ser tratadas como dados não confiáveis;
- anexos inline devem respeitar limites de tamanho e MIME type já definidos pelo domínio;
- URIs externas não devem ser buscadas implicitamente;
- o servidor deve continuar retornando `needs_review` quando a evidência for insuficiente;
- erros de backend externo devem ser representados como falha controlada da ferramenta;
- o contrato MCP não deve prometer uma resposta correta quando o serviço só possui uma proposta incerta.

## Observabilidade

Os logs em stderr devem identificar, sem dados sensíveis:

- inicialização e encerramento do servidor;
- método MCP recebido;
- ferramenta chamada;
- duração da operação;
- resultado de sucesso, erro controlado ou necessidade de revisão.

Perguntas completas, anexos, tokens, headers de autorização e respostas integrais de provedores não devem ser registrados.

## Critérios de aceitação

- o servidor responde a `server/discover` com a revisão `2026-07-28`;
- a resposta de descoberta declara somente as capacidades realmente implementadas;
- `tools/list` retorna a lista completa, em ordem estável, com schemas de entrada e saída;
- `tools/call` valida argumentos e retorna `resultType`, `content`, `structuredContent` e `isError` conforme o caso;
- o stdout contém somente JSON-RPC válido;
- o servidor encerra corretamente quando o stdin é fechado;
- a execução com o SDK moderno funciona em um processo stdio real;
- a execução de todas as ferramentas existentes continua coberta por testes;
- falhas de configuração, timeout e backend não vazam segredos;
- a política de baixa confiança e `needs_review` continua preservada;
- a documentação descreve somente o protocolo e o comportamento efetivamente implementados;
- a suíte de testes cobre descoberta, listagem, chamada, erros, schemas e transporte.

## Fora de escopo

- suporte a revisões MCP anteriores;
- compatibilidade com clientes legados;
- Streamable HTTP;
- autenticação de servidor remoto;
- resources;
- prompts;
- subscriptions;
- tarefas e interações que exigem novas entradas durante uma chamada;
- cliente Selenium ou automação de plataformas externas;
- alteração da lógica de seleção das LLMs além do necessário para o contrato MCP.
