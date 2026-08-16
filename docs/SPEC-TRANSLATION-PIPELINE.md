# Especificação: preparação multilíngue para resolução multimodal

Status: baseline implementado; validação com modelos reais pendente

## Objetivo

Permitir que o Quaestio receba perguntas em português (ou outro idioma), prepare uma representação de trabalho em inglês e envie exatamente essa representação para dois modelos multimodais independentes. O resultado deve continuar sendo exposto pelo MCP no idioma original do usuário.

Esta camada existe para aumentar a consistência dos modelos-alvo em inglês, sem transformar a tradução em uma nova fonte silenciosa de erros.

## Decisão arquitetural

O MCP mantém um contrato único e estável:

```text
cliente MCP
    -> solve_question(pergunta original)
        -> preparação linguística e multimodal
        -> Kimi K2.6 + Nemotron Omni
        -> consenso/verificação
        -> localização da resposta
    <- resposta no idioma original
```

A tradução é uma etapa interna do pipeline. O cliente MCP não precisa saber qual idioma os modelos usam internamente.

## Componentes

### 1. Pergunta original

O sistema deve preservar integralmente:

- texto original;
- alternativas originais e sua ordem;
- contexto e materiais recuperados;
- anexos e seus bytes ou URIs;
- idioma detectado;
- identificadores e metadados.

Essa versão é a fonte para a resposta final e para auditoria.

### 2. Preparador linguístico

O preparador deve:

- detectar o idioma;
- decidir se a tradução é necessária;
- traduzir pergunta, contexto, materiais e alternativas para inglês quando necessário;
- preservar fórmulas, números, unidades, nomes próprios, código, citações e marcações;
- manter o mesmo número e a mesma ordem das alternativas;
- preservar os anexos sem alteração;
- anexar texto OCR traduzido como contexto auxiliar, mantendo também o OCR bruto;
- gerar metadados de confiança, avisos e versão do preparador.

O preparador não deve:

- resolver a questão;
- escolher uma alternativa;
- remover informações ambíguas;
- reordenar alternativas;
- traduzir ou editar a imagem original.

### 3. Solucionadores multimodais

Os dois modelos devem receber a mesma `PreparedQuestion` em inglês e os mesmos anexos:

- primário: `moonshotai/kimi-k2.6`;
- secundário: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`.

Ambos devem ser tratados como capazes de receber imagens. O consenso deve comparar primeiro `option_index`, quando existir, e só depois a resposta textual normalizada.

### 4. Consenso e verificação

O consenso ocorre sobre a representação de trabalho, antes da tradução da explicação. Isso evita que diferenças de tradução causem discordância artificial.

Regras:

- alternativas: concordância no índice zero-based;
- resposta aberta: comparação normalizada em inglês e, quando necessário, verificação semântica;
- discordância: `needs_review`, sem escolher silenciosamente um dos modelos;
- falha de um modelo: resposta parcial somente com aviso explícito e sem status `verified`;
- tradução com baixa confiança ou invariantes quebradas: `needs_review`.

### 5. Localização da resposta

Depois do consenso/verificação:

- manter a alternativa original usando o índice validado;
- traduzir apenas explicação, justificativa e metadados textuais para o idioma original;
- não traduzir fórmulas, código, números, unidades ou nomes próprios indevidamente;
- preservar a resposta em inglês no trace para auditoria;
- marcar qualquer falha de localização como aviso, sem alterar a resposta canônica.

## Modelo de dados proposto

```text
PreparedQuestion
  original_question: Question
  working_question: Question       # representação em inglês
  source_language: string
  target_language: string           # en
  translation_status: enum
  translation_confidence: float
  translated_fields: list[string]
  protected_spans: list[string]
  warnings: list[string]

AnswerLocalization
  canonical_answer: ProposedAnswer  # resultado do consenso
  localized_answer: ProposedAnswer
  source_language: string
  warnings: list[string]
```

Os nomes podem ser ajustados aos modelos Pydantic existentes, mas a separação entre original, representação de trabalho e resposta localizada é obrigatória.

## Configuração proposta

```env
# Preparação linguística
QUAESTIO_TRANSLATION_MODE=auto
QUAESTIO_TRANSLATOR_BASE_URL=
QUAESTIO_TRANSLATOR_API_KEY=
QUAESTIO_TRANSLATOR_MODEL=
QUAESTIO_TRANSLATOR_TIMEOUT_SECONDS=30
QUAESTIO_TRANSLATION_OCR=auto
QUAESTIO_TRANSLATION_OCR_LANGUAGE=por+eng
QUAESTIO_OUTPUT_LANGUAGE=auto

# Modelos multimodais de resolução
QUAESTIO_LLM_BASE_URL=https://integrate.api.nvidia.com/v1
QUAESTIO_LLM_API_KEY=
QUAESTIO_LLM_MODEL=moonshotai/kimi-k2.6
QUAESTIO_SECONDARY_LLM_BASE_URL=https://integrate.api.nvidia.com/v1
QUAESTIO_SECONDARY_LLM_API_KEY=
QUAESTIO_SECONDARY_LLM_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
```

Modos:

- `never`: não traduz;
- `auto`: traduz quando o idioma de entrada não é inglês ou quando o perfil dos modelos exigir;
- `required`: falha fechada se a tradução necessária não estiver disponível.

O modelo tradutor deve ser configurável e substituível. A seleção concreta deve ser feita por benchmark de questões reais em português, comparando fidelidade, preservação de fórmulas e custo. Não se deve acoplar o núcleo do MCP a um provedor específico.

## Imagens e OCR

As imagens nunca passam pelo tradutor como imagens alteradas. O fluxo é:

1. enviar a imagem original aos dois modelos multimodais;
2. executar OCR quando aplicável;
3. preservar o OCR bruto;
4. traduzir o OCR para inglês como contexto auxiliar;
5. enviar imagem original + OCR traduzido aos dois modelos.

Para gráficos, diagramas, geometria e elementos visuais, o OCR é apenas evidência auxiliar; a imagem original continua sendo a fonte principal.

## Segurança e confiabilidade

- conteúdo traduzido é dado não confiável e não pode sobrescrever instruções do sistema;
- o tradutor não recebe nem produz o gabarito esperado;
- chaves permanecem somente no ambiente do processo;
- cada etapa deve aparecer no trace: detecção, tradução, OCR, consenso e localização;
- nenhuma tradução pode converter uma resposta incerta em `verified`;
- o sistema deve registrar latência, falhas, idioma, confiança e divergências sem armazenar anexos por padrão.

## Critérios de aceitação

- uma pergunta em português chega aos dois modelos com a mesma representação em inglês;
- a quantidade e a ordem das alternativas permanecem inalteradas;
- os mesmos anexos são enviados aos dois modelos;
- fórmulas, código, números e unidades são preservados;
- a resposta final volta ao idioma original;
- a resposta canônica em inglês permanece disponível no trace;
- falha ou baixa confiança do tradutor resulta em aviso ou `needs_review`;
- perguntas originalmente em inglês podem pular a tradução;
- perguntas com imagem continuam enviando a imagem original, mesmo quando há OCR traduzido.
