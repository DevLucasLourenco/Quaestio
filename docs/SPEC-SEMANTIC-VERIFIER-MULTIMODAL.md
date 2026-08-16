# Especificação: verificação semântica multimodal

Status: implementado

## Objetivo

Permitir que o verificador semântico independente avalie uma proposta usando não apenas o texto da questão, mas também os anexos visuais que fundamentaram a resposta.

## Fluxo

```text
pergunta original + contexto + anexos + proposta
                    ↓
          verificador semântico
                    ↓
       supports / contradicts / uncertain
```

## Requisitos

- o verificador deve receber os mesmos anexos relevantes da pergunta;
- anexos devem ser enviados sem alteração;
- o prompt deve tratar pergunta, contexto e proposta como dados não confiáveis;
- a saída deve continuar limitada ao contrato `SemanticCheck`;
- imagens não disponíveis ou não suportadas devem gerar `uncertain`, não `supports`;
- o verificador não pode marcar a resposta como prova determinística.

## Compatibilidade

O backend deve continuar aceitando modelos somente textuais. Nesse caso, o comportamento atual permanece válido e a ausência de suporte visual deve aparecer no resultado ou no trace.

## Segurança e privacidade

- não persistir anexos por padrão;
- não registrar base64, URI privada ou conteúdo visual nos logs;
- respeitar limites de tamanho e MIME type;
- manter a chave apenas nos headers da chamada.

## Critérios de aceitação

- o verificador textual continua funcionando sem anexos;
- um modelo multimodal recebe imagem e texto no formato compatível;
- proposta correta visualmente fundamentada pode retornar `supports`;
- proposta contradita pela imagem retorna `contradicts` ou `uncertain` conforme a evidência;
- falha de upload ou parsing retorna `uncertain` sem interromper o MCP;
- o `trace` identifica quando a verificação visual foi executada.

## Fora de escopo

- extrair novas questões da imagem;
- substituir o solver multimodal;
- aceitar vídeo ou áudio nesta primeira versão.

## Implementação concluída

O verificador aceita imagens inline em `verify_answer_semantically` e no fluxo integrado de resolução. Anexos sem bytes inline permanecem no contexto textual, sem que o servidor tente buscar URIs externas.
