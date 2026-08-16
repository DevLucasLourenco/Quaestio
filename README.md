# Quaestio MCP Server

O Quaestio é um servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) para análise, resolução e verificação de questões. Ele expõe ferramentas MCP para que um host compatível possa enviar perguntas, anexos e materiais de estudo e receber resultados estruturados, rastreáveis e conservadores.

O servidor não é uma interface de usuário nem um modelo de linguagem. Ele é a camada MCP que organiza o contrato de entrada, chama os componentes configurados, valida as respostas e devolve uma decisão estruturada ao cliente.

## O que é MCP neste projeto

MCP é um protocolo aberto para conectar aplicações host a servidores que oferecem ferramentas e dados de forma padronizada. No Quaestio:

```text
host MCP / cliente MCP
          │
          │ transporte stdio + JSON-RPC
          ▼
Quaestio MCP Server
          │
          ├── ferramentas de resolução e verificação
          ├── parsing, OCR e PDF
          ├── materiais de estudo e busca semântica
          ├── análise e execução controlada de código
          └── políticas de confiabilidade e auditoria
```

O MCP Server atualmente expõe a primitiva `tools`. Ele não publica `resources`, `resource templates` ou `prompts` como primitivas MCP separadas. Materiais, OCR, PDFs e capacidades do servidor são acessados por ferramentas.

Referências de protocolo utilizadas:

- [MCP — documentação oficial](https://modelcontextprotocol.io/);
- [especificação de ferramentas](https://modelcontextprotocol.io/specification/2025-06-18/server/tools);
- [especificação de transportes](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports);
- [Python SDK oficial](https://github.com/modelcontextprotocol/python-sdk);
- [servidores de referência oficiais](https://github.com/modelcontextprotocol/servers).

## Capacidades

- resolver questões de múltipla escolha e abertas;
- processar perguntas com imagens inline;
- executar consenso entre dois backends LLM configuráveis;
- preparar perguntas não inglesas para os modelos configurados;
- preservar alternativas, índices, fórmulas, código e anexos;
- verificar estruturalmente e, quando configurado, semanticamente uma proposta;
- aplicar verificação matemática determinística e simbólica opcional;
- adicionar e pesquisar materiais de estudo locais;
- usar embeddings semânticos com fallback para TF-IDF;
- extrair texto de imagens com Tesseract;
- extrair e interpretar texto de PDFs;
- analisar código sem executá-lo;
- compilar/verificar sintaxe sem executar o código;
- executar Python ou JavaScript somente em sandbox Docker;
- avaliar lotes com gabarito e calcular métricas;
- retornar um `trace` das etapas executadas.

## Princípios de confiabilidade

O servidor foi projetado para falhar de forma explícita quando não há evidência suficiente.

- ausência de backend ou proposta válida resulta em `needs_review`;
- discordância entre os modelos não é resolvida silenciosamente;
- verificação semântica não é tratada como prova determinística;
- `verified` é reservado para evidência confiável, como verificações matemáticas determinísticas;
- a confiança declarada por um modelo é limitada pelo servidor;
- entradas, anexos, contexto e materiais recuperados são tratados como dados não confiáveis, nunca como instruções do sistema;
- falhas de provedores externos são convertidas em avisos e estados estruturados;
- o servidor não deve ser usado para considerar uma resposta de LLM como garantia de correção.

## Arquitetura interna

```text
tools/call
   │
   ▼
MCP boundary
   │  valida argumentos e serializa resultado
   ▼
QuaestioService
   ├── classificação
   ├── recuperação de materiais
   ├── preparação linguística/OCR
   ├── solver determinístico ou LLM
   ├── consenso
   ├── verificação estrutural/semântica
   └── avaliação e trace
```

Os principais componentes internos são:

- `models.py`: contratos canônicos e estados públicos;
- `mcp_server.py`: registro, despacho e transporte MCP;
- `service.py`: orquestração do pipeline;
- `backends.py`: backends determinísticos, LLM, tradução e consenso;
- `verification.py`: validações estruturais e matemáticas;
- `semantic_verifier.py`: revisão semântica independente opcional;
- `knowledge.py` e `embeddings.py`: base local e recuperação semântica;
- `ocr.py` e `pdf.py`: extração local de conteúdo;
- `sandbox.py`: execução controlada de código em Docker.

## Transporte e ciclo MCP

O transporte principal é `stdio`, adequado para servidores locais. O host inicia o processo e conversa com ele por `stdin` e `stdout`; cada mensagem é JSON-RPC. Logs de inicialização são enviados para `stderr` para não corromper o canal MCP.

O fallback incluído implementa os fluxos essenciais:

1. `initialize` — negociação inicial e identificação do servidor;
2. `notifications/initialized` — confirmação do cliente;
3. `tools/list` — descoberta das ferramentas e seus schemas;
4. `tools/call` — execução de uma ferramenta;
5. `ping` — verificação de disponibilidade.

Quando o pacote oficial `mcp` está instalado, o servidor utiliza `FastMCP` com transporte `stdio`. Sem o pacote, usa o transporte stdio mínimo incluído no projeto. Os dois caminhos registram o mesmo conjunto de ferramentas.

O servidor não inicia uma porta HTTP. Para uma implantação HTTP seria necessário adicionar explicitamente um transporte compatível, como Streamable HTTP, conforme a [documentação oficial de transportes do MCP](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

## Instalação

Requisitos:

- Python 3.11 ou superior;
- `pip`;
- credenciais de um endpoint LLM compatível com a API de chat da OpenAI para resolução assistida;
- Tesseract, somente para OCR local;
- Docker e imagens locais, somente para `run_code`;
- `pypdf`, somente para extração de PDFs.

Instalação básica:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Extras opcionais:

```powershell
pip install -e ".[sdk]"   # Python SDK oficial do MCP
pip install -e ".[math]"  # SymPy
pip install -e ".[pdf]"   # pypdf
```

## Configuração

Copie `.env.example` para `.env` e preencha somente os provedores que deseja utilizar. O `.env` não deve ser versionado nem compartilhado.

### Resolução LLM

```env
QUAESTIO_LLM_BASE_URL=https://integrate.api.nvidia.com/v1
QUAESTIO_LLM_API_KEY=...
QUAESTIO_LLM_MODEL=...
QUAESTIO_LLM_TIMEOUT_SECONDS=45
```

Esse é o backend principal. Se o segundo backend estiver totalmente configurado, o Quaestio executa consenso:

```env
QUAESTIO_SECONDARY_LLM_BASE_URL=https://integrate.api.nvidia.com/v1
QUAESTIO_SECONDARY_LLM_API_KEY=...
QUAESTIO_SECONDARY_LLM_MODEL=...
```

Sem backend, o servidor continua disponível, mas questões que não puderem ser resolvidas deterministicamente retornam `needs_review`.

### Preparação linguística

```env
QUAESTIO_TRANSLATION_MODE=auto
QUAESTIO_TRANSLATION_TARGET_LANGUAGE=en
QUAESTIO_TRANSLATOR_BASE_URL=https://integrate.api.nvidia.com/v1
QUAESTIO_TRANSLATOR_API_KEY=...
QUAESTIO_TRANSLATOR_MODEL=...
QUAESTIO_TRANSLATOR_TIMEOUT_SECONDS=30
QUAESTIO_TRANSLATION_OCR=auto
QUAESTIO_TRANSLATION_OCR_LANGUAGE=por+eng
```

Modos disponíveis:

- `never`: nunca traduz;
- `auto`: traduz quando a pergunta não estiver em inglês;
- `required`: exige o tradutor quando a tradução for necessária.

A imagem original não é alterada. Quando há OCR, o texto reconhecido pode ser usado como contexto auxiliar, mas a imagem continua sendo enviada como evidência visual.

### Busca semântica

```env
QUAESTIO_KNOWLEDGE_BASE_PATH=./data/knowledge.json
QUAESTIO_EMBEDDING_BASE_URL=https://integrate.api.nvidia.com/v1
QUAESTIO_EMBEDDING_API_KEY=...
QUAESTIO_EMBEDDING_MODEL=...
QUAESTIO_EMBEDDING_TIMEOUT_SECONDS=30
```

Embeddings são opcionais. Quando indisponíveis, a base local usa TF-IDF. A base armazena materiais e vetores localmente; não adicione conteúdo que não possa ser persistido nesse arquivo.

### Verificação semântica independente

```env
QUAESTIO_VERIFIER_LLM_BASE_URL=https://integrate.api.nvidia.com/v1
QUAESTIO_VERIFIER_LLM_API_KEY=...
QUAESTIO_VERIFIER_LLM_MODEL=...
QUAESTIO_VERIFIER_LLM_TIMEOUT_SECONDS=45
```

Esse backend deve ser separado do solver quando a independência da revisão for importante. Ele retorna `supports`, `contradicts` ou `uncertain`; não transforma uma resposta de LLM em `verified`.

### Recursos locais opcionais

```env
QUAESTIO_TESSERACT_PATH=
QUAESTIO_DOCKER_PATH=
QUAESTIO_SANDBOX_PYTHON_IMAGE=python:3.12-slim
```

O Docker sandbox não baixa imagens automaticamente. As imagens precisam existir localmente.

## Como iniciar o servidor

Após a instalação editável:

```powershell
quaestio
```

Sem instalação editável:

```powershell
$env:PYTHONPATH = "src"
python -m quaestio.mcp_server
```

O processo parece ficar aguardando entrada porque o transporte `stdio` é dirigido pelo cliente MCP. Isso é o comportamento esperado.

## Configuração em um cliente MCP

Um host MCP precisa iniciar o comando do servidor como subprocesso. Exemplo genérico para Windows:

```json
{
  "mcpServers": {
    "quaestio": {
      "command": "C:\\caminho\\para\\Quaestio\\.venv\\Scripts\\quaestio.exe"
    }
  }
}
```

Alternativamente, usando Python:

```json
{
  "mcpServers": {
    "quaestio": {
      "command": "C:\\caminho\\para\\Quaestio\\.venv\\Scripts\\python.exe",
      "args": ["-m", "quaestio.mcp_server"],
      "env": {
        "PYTHONPATH": "C:\\caminho\\para\\Quaestio\\src"
      }
    }
  }
}
```

As variáveis de ambiente podem ser fornecidas pelo `.env` local ou pela configuração do host. Prefira o mecanismo de segredos do host quando disponível e nunca inclua chaves reais no repositório.

## Ferramentas MCP

### Resolução e verificação

| Ferramenta | Uso |
| --- | --- |
| `solve_question` | Resolve uma questão e retorna resposta, status, confiança, fontes, verificações e trace. |
| `solve_questions_batch` | Resolve até 500 questões preservando seus IDs. |
| `verify_answer` | Verifica consistência estrutural de uma proposta com a pergunta e suas opções. |
| `verify_answer_semantically` | Solicita revisão a um verificador LLM independente, quando configurado. |
| `classify_question` | Classifica tipo, disciplina e tópico. |
| `evaluate_questions` | Resolve questões com gabarito e retorna métricas de avaliação. |

### Materiais e recuperação

| Ferramenta | Uso |
| --- | --- |
| `add_study_material` | Adiciona texto autorizado à base local. |
| `search_study_material` | Busca materiais relevantes por TF-IDF ou embeddings. |

### Parsing, OCR e documentos

| Ferramenta | Uso |
| --- | --- |
| `parse_questions` | Converte texto numerado em questões canônicas. |
| `solve_text` | Faz parsing e resolução de um bloco de texto. |
| `extract_questions_from_image` | Extrai questões de imagens por backend visual configurado. |
| `ocr_image` | Executa OCR local com Tesseract, sem persistir a imagem. |
| `ocr_parse_image` | Executa OCR e transforma o resultado em questões. |
| `extract_pdf_text` | Extrai texto de um PDF inline usando `pypdf`. |
| `extract_questions_from_pdf` | Extrai texto do PDF e cria questões canônicas. |

Para processamento visual e OCR, a entrada precisa conter uma imagem inline em base64. Referências URI são aceitas no contrato canônico, mas o fluxo atual de OCR e envio multimodal utiliza os bytes inline.

### Código

| Ferramenta | Uso |
| --- | --- |
| `analyze_code` | Analisa código estaticamente sem executar. |
| `compile_code` | Verifica sintaxe/compilação sem executar. |
| `run_code` | Executa somente Python ou JavaScript em Docker sem rede e com limites de recursos. |

`run_code` não executa código no host. Se Docker, imagem ou linguagem não estiverem disponíveis, retorna um estado estruturado de indisponibilidade.

### Diagnóstico

| Ferramenta | Uso |
| --- | --- |
| `server_capabilities` | Expõe capacidades e a política de confiabilidade do servidor. |

## Contrato de entrada

Uma questão canônica pode ser enviada assim:

```json
{
  "question": "Qual é a capital do Brasil?",
  "options": ["Rio de Janeiro", "Brasília", "São Paulo"],
  "question_id": "q-001",
  "context": "Questão de geografia.",
  "attachments": []
}
```

Campos principais:

- `question`: texto obrigatório;
- `options`: lista opcional com pelo menos duas alternativas únicas;
- `question_id`: identificador preservado em lotes;
- `context`: contexto adicional ou material recuperado;
- `attachments`: imagens ou documentos, normalmente com `mime_type` e `data_base64`;
- `expected_answer` e `expected_option_index`: somente para avaliação com gabarito, não para orientar o solver.

## Contrato de saída

Uma resposta contém, entre outros campos:

```json
{
  "question_type": "multiple_choice",
  "answer": "Brasília",
  "option_index": 1,
  "confidence": 0.75,
  "status": "answered",
  "method": "consensus",
  "verification": {
    "status": "answered",
    "verified": false,
    "semantic": {
      "status": "supports",
      "confidence": 0.91
    }
  },
  "sources": [],
  "warnings": [],
  "trace": []
}
```

### Status da resposta

- `verified`: evidência determinística suficiente;
- `answered`: uma proposta foi produzida, mas não há prova determinística;
- `needs_review`: faltou consenso, evidência ou validação;
- `error`: falha no pipeline.

O campo `correct` só é preenchido quando o cliente fornece um gabarito por `expected_answer` ou `expected_option_index`.

## Exemplo de chamada MCP

Depois de `initialize` e `notifications/initialized`, o cliente pode chamar:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "solve_question",
    "arguments": {
      "question": "Qual é a capital do Brasil?",
      "options": ["Rio de Janeiro", "Brasília", "São Paulo"]
    }
  }
}
```

O resultado MCP inclui conteúdo textual serializado e `structuredContent` para clientes que suportam resultados estruturados.

## Desenvolvimento e validação

Execute a suíte automatizada com:

```powershell
pytest -q
```

Os testes unitários devem ser executados sem depender de chamadas reais aos provedores. Smoke tests contra APIs externas devem ser explícitos, usando credenciais locais e questões autorizadas.

Documentação técnica relacionada:

- [especificação e plano de preparação multilíngue](docs/SPEC-TRANSLATION-PIPELINE.md) / [plano](docs/PLAN-TRANSLATION-PIPELINE.md);
- [especificação de isolamento de testes](docs/SPEC-TEST-ISOLATION.md) / [plano](docs/PLAN-TEST-ISOLATION.md);
- [especificação de smoke test NIM](docs/SPEC-NIM-SMOKE-TEST.md) / [plano](docs/PLAN-NIM-SMOKE-TEST.md);
- [especificação de avaliação multimodal](docs/SPEC-MULTILINGUAL-MULTIMODAL-EVALUATION.md) / [plano](docs/PLAN-MULTILINGUAL-MULTIMODAL-EVALUATION.md);
- [especificação de embeddings](docs/SPEC-EMBEDDING-QUERY-PASSAGE.md) / [plano](docs/PLAN-EMBEDDING-QUERY-PASSAGE.md);
- [especificação do verificador multimodal](docs/SPEC-SEMANTIC-VERIFIER-MULTIMODAL.md) / [plano](docs/PLAN-SEMANTIC-VERIFIER-MULTIMODAL.md);
- [especificação de benchmark e confiança](docs/SPEC-BENCHMARK-CONFIDENCE.md) / [plano](docs/PLAN-BENCHMARK-CONFIDENCE.md).

## Limites atuais

- transporte público HTTP ainda não está implementado;
- o servidor não expõe resources ou prompts MCP;
- o verificador semântico aceita imagens inline; URIs externas, PDFs e vídeo ainda não são enviados nessa etapa;
- o índice de embeddings exige reindexação quando o modelo configurado é trocado;
- OCR e extração de PDF dependem de instalações locais opcionais;
- consenso e revisão semântica reduzem risco, mas não substituem gabarito, prova formal ou revisão humana.
