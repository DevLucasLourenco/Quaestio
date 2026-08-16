# Especificação: avaliação multilíngue e multimodal

Status: pendente

## Objetivo

Medir se a preparação para inglês e o consenso multimodal aumentam ou preservam a qualidade da resolução sem alterar a pergunta, as alternativas ou as evidências visuais.

## Conjunto mínimo de avaliação

O conjunto deve conter questões autorizadas, com gabarito, distribuídas entre:

- português sem imagem;
- português com texto em imagem;
- gráficos, tabelas e diagramas;
- matemática e fórmulas;
- código;
- inglês, para validar o bypass da tradução;
- OCR ambíguo ou incompleto;
- perguntas abertas.

Cada item deve conter, quando aplicável:

- identificador;
- idioma;
- texto e alternativas;
- anexos;
- resposta esperada;
- tipo de questão;
- categoria de dificuldade;
- observações de anotação.

## Métricas

- acurácia do solver primário;
- acurácia do solver secundário;
- acurácia do consenso;
- taxa de concordância;
- taxa de `needs_review`;
- fidelidade da tradução;
- preservação de alternativas, fórmulas e código;
- sucesso de OCR;
- latência por etapa;
- custo estimado por questão.

## Critérios de aceitação

- o conjunto é reproduzível sem depender de questões ativas;
- cada item possui gabarito e metadados completos;
- a avaliação separa erros de tradução, OCR, solver e consenso;
- questões originalmente em inglês não passam por tradução desnecessária;
- imagens originais permanecem idênticas nos dois payloads multimodais;
- nenhum resultado `verified` é atribuído somente por consenso de LLM;
- o relatório permite comparar modelos individualmente e em conjunto.

## Fora de escopo

- treinar ou ajustar pesos de modelos;
- coletar questões automaticamente de plataformas;
- automatizar preenchimento de respostas em sites.
