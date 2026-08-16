# Especificação: smoke test dos endpoints NVIDIA NIM

Status: implementado

## Objetivo

Validar, com uma execução pequena e explícita, que os modelos configurados no `.env` podem ser acessados pelo Quaestio e retornam respostas compatíveis com os contratos internos.

## Componentes a validar

- solver primário: `moonshotai/kimi-k2.6`;
- solver secundário: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`;
- tradutor: `moonshotai/kimi-k2.6`;
- embeddings: `nvidia/nemotron-3-embed-1b`;
- verificador: `mistralai/mistral-small-4-119b-2603`.

## Regras

- o teste deve usar somente questões sintéticas ou autorizadas;
- nenhum gabarito secreto deve ser enviado ao solver;
- o teste deve ser opt-in e nunca fazer parte do `pytest` padrão;
- respostas e anexos enviados não devem ser persistidos por padrão;
- uma chave ausente ou resposta incompatível deve produzir diagnóstico claro.

## Cenários mínimos

1. chamada textual simples ao solver primário;
2. chamada textual simples ao solver secundário;
3. tradução de uma pergunta curta em português;
4. geração de embedding para documento e consulta;
5. verificação semântica de uma proposta correta;
6. verificação semântica de uma proposta incorreta;
7. resolução completa com consenso.

## Critérios de aceitação

- cada endpoint responde dentro do timeout configurado;
- os modelos retornam conteúdo parseável pelo Quaestio;
- o tradutor preserva a quantidade e a ordem das alternativas;
- o embedding retorna vetor não vazio;
- o verificador retorna `supports`, `contradicts` ou `uncertain` em JSON válido;
- a resolução completa gera `trace` com solver, consenso e verificação;
- falhas são reportadas sem imprimir API keys.

## Fora de escopo

- benchmark estatístico de qualidade;
- teste de carga;
- execução contra provas reais ou sistemas externos.

## Implementação concluída

O comando opt-in `quaestio-smoke` valida os backends configurados, o tradutor, embeddings, o verificador semântico e um fluxo end-to-end. A saída padrão não inclui credenciais nem conteúdo completo das respostas.
