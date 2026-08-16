# Plano de implementação: verificação semântica multimodal

Status: planejado

## Fase 1 — Contrato de conteúdo multimodal

- reutilizar `Attachment` como entrada do verificador;
- definir serialização de texto e imagem;
- mapear MIME types e limites de tamanho;
- criar dublês para payloads multimodais.

Saída: contrato testável sem API externa.

## Fase 2 — Backend do verificador

- alterar o protocolo para aceitar a pergunta completa;
- incluir anexos no payload somente quando existirem;
- preservar o parser tolerante de JSON;
- tratar respostas com raciocínio separado ou texto cercado por JSON.

Saída: verificador compatível com modelos textuais e multimodais.

## Fase 3 — Integração no serviço

- passar a pergunta original e a proposta ao verificador;
- registrar estágio visual no `trace`;
- manter `supports` como evidência semântica, nunca como `verified`;
- retornar `needs_review` em contradições.

## Fase 4 — Testes

- texto sem anexo;
- imagem com questão objetiva;
- imagem ilegível;
- MIME type inválido;
- timeout e falha de upload;
- modelo textual configurado para confirmar fallback.

## Ordem recomendada

1. contrato;
2. backend;
3. integração no serviço;
4. testes unitários;
5. smoke test multimodal;
6. avaliação no dataset.
