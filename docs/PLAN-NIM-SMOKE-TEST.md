# Plano de implementação: smoke test dos endpoints NVIDIA NIM

Status: planejado

## Fase 1 — Harness de smoke test

- criar um comando ou módulo separado da suíte unitária;
- carregar o `.env` somente quando o comando for executado explicitamente;
- validar previamente a presença das variáveis necessárias;
- mascarar credenciais em toda saída.

Saída: executor opt-in com diagnóstico seguro.

## Fase 2 — Testes de contratos individuais

- testar chat primário e secundário;
- testar tradução JSON;
- testar embeddings;
- testar verificador semântico;
- registrar latência, status HTTP e tipo de falha.

Saída: confirmação de compatibilidade por provedor.

## Fase 3 — Teste integrado

- resolver uma questão de múltipla escolha em português;
- validar a etapa de tradução;
- validar consenso entre os dois modelos;
- validar a verificação semântica;
- inspecionar o `trace`, avisos e status final.

Saída: primeiro fluxo real aprovado.

## Fase 4 — Falhas controladas

- executar com modelo inexistente;
- executar com timeout reduzido;
- simular resposta JSON inválida;
- verificar retorno `needs_review` ou `uncertain` sem crash.

## Ordem recomendada

1. harness seguro;
2. contratos individuais;
3. integração completa;
4. falhas controladas;
5. documentação do comando e do resultado.
