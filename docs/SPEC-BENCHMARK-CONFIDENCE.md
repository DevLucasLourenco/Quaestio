# Especificação: benchmark e calibração de confiança

Status: implementado

## Objetivo

Criar um conjunto pequeno, versionado e reproduzível de questões com gabarito para medir a precisão do Quaestio e calibrar a confiança exibida ao cliente.

## Contrato dos itens

Cada item deve conter:

- `id` estável;
- pergunta e alternativas;
- idioma;
- anexos opcionais;
- resposta esperada ou índice esperado;
- disciplina e tópico;
- categoria de dificuldade;
- origem/licença do material;
- versão do dataset.

## Regras de avaliação

- respostas devem ser comparadas por índice quando a questão for objetiva;
- respostas abertas devem usar normalização e, quando necessário, revisão humana;
- resultados `needs_review` não podem ser contados como corretos ou incorretos;
- o relatório deve distinguir acurácia, cobertura e abstenção;
- mudanças de modelo ou prompt devem gerar uma nova execução identificável.

## Calibração

A confiança deve ser analisada contra o resultado real do gabarito. O sistema deve observar:

- confiança média em respostas corretas;
- confiança média em respostas incorretas;
- erros de excesso de confiança;
- taxa de `needs_review`;
- diferença entre solver individual, consenso e verificador.

Nenhuma alteração de threshold deve transformar uma resposta incorreta em `verified` sem evidência determinística.

## Critérios de aceitação

- existe um dataset inicial com gabarito revisado;
- a avaliação calcula `evaluated`, `correct`, `incorrect`, `coverage` e `accuracy`;
- resultados são segmentados por tipo, idioma, imagem e disciplina;
- o relatório identifica excesso de confiança;
- uma configuração pode ser comparada com outra;
- a calibração é validada em um conjunto separado do conjunto usado para ajustar parâmetros.

## Fora de escopo

- treinamento supervisionado;
- coleta automática de dados de plataformas;
- publicação de questões protegidas por direitos autorais.

## Implementação concluída

O relatório registra acurácia, cobertura, `needs_review`, média de confiança e gap de excesso de confiança em cinco faixas de confiança. O gabarito permanece no dataset e não é enviado como instrução ao solver.

O primeiro conjunto sintético versionado está em `data/evaluation/benchmark-v1.jsonl`, com 30 questões, incluindo 13 de matemática e 12 de engenharia de software. Ele é separado do `smoke.jsonl`, que permanece como fixture mínima da suíte local.
