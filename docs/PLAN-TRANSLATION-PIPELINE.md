# Plano de implementação: preparação multilíngue e consenso multimodal

Status: implementação inicial concluída; benchmark e refinamentos pendentes

## Estado atual

- [x] contratos de preparação e tradução;
- [x] tradutor OpenAI-compatible configurável;
- [x] representação de trabalho compartilhada pelos dois solucionadores;
- [x] preservação de imagens e alternativas;
- [x] OCR opcional como contexto auxiliar;
- [x] localização da resposta após o consenso;
- [x] testes automatizados do fluxo;
- [ ] escolher e validar o modelo tradutor dedicado;
- [ ] validar o fluxo contra endpoints reais do NVIDIA NIM;
- [ ] ajustar parâmetros específicos de raciocínio e saída JSON dos modelos.

## Fase 1 — Contratos e invariantes

- adicionar modelos para a pergunta original, pergunta de trabalho e metadados de tradução;
- definir estados `skipped`, `translated`, `failed` e `needs_review`;
- criar validações para quantidade/ordem de alternativas e preservação de anexos;
- ampliar o trace com os estágios linguísticos.

Saída: contratos testáveis sem depender de uma LLM.

## Fase 2 — Abstração do tradutor

- criar um protocolo `TranslationBackend`;
- implementar um backend OpenAI-compatible com saída JSON estrita;
- adicionar proteção de fórmulas, código, números, unidades e nomes próprios;
- implementar detecção de idioma e modo `auto`;
- não traduzir quando a entrada já estiver em inglês;
- manter o tradutor separado dos solucionadores.

Saída: uma pergunta em português vira uma `PreparedQuestion` em inglês sem resolver o conteúdo.

## Fase 3 — Preparação multimodal

- conectar o preparador ao OCR existente;
- preservar OCR bruto e gerar OCR traduzido como contexto auxiliar;
- manter anexos originais inalterados;
- validar o payload multimodal aceito por Kimi e Nemotron;
- tratar limites de tamanho de imagem e erros de upload.

Saída: ambos os modelos recebem texto de trabalho em inglês e a mesma evidência visual.

## Fase 4 — Solução e consenso

- executar Kimi K2.6 e Nemotron Omni com a mesma pergunta preparada;
- normalizar respostas para `option_index` e `ProposedAnswer`;
- lidar com campos de raciocínio separados do conteúdo final;
- comparar alternativas por índice;
- retornar `needs_review` em caso de discordância;
- manter falha parcial explicitamente sinalizada.

Saída: consenso multimodal real, sem que um modelo textual valide uma questão visual.

## Fase 5 — Localização da resposta

- traduzir explicações somente depois do consenso;
- manter alternativa original e índice canônico;
- preservar fórmulas, código, números e unidades;
- adicionar idioma original e avisos ao resultado;
- guardar a resposta de trabalho no trace, sem expô-la como resposta principal.

Saída: resposta natural para o usuário, com auditoria do caminho interno.

## Fase 6 — Avaliação

Criar um conjunto de avaliação com questões reais e gabarito, distribuído entre:

- português sem imagem;
- português com texto em imagem;
- gráficos, tabelas e diagramas;
- matemática e fórmulas;
- código;
- inglês, para confirmar que o bypass funciona;
- ambiguidades e erros intencionais de OCR.

Medir:

- acurácia do consenso;
- acurácia de cada modelo individual;
- fidelidade da tradução;
- preservação de alternativas e fórmulas;
- taxa de `needs_review`;
- latência e custo por pergunta;
- falhas por tipo de anexo.

Critério inicial: não adotar o tradutor como obrigatório até que ele não reduza a acurácia em questões que os modelos já resolvem corretamente em português.

## Fase 7 — Operação e documentação

- documentar as novas variáveis no `.env.example`;
- adicionar limites de tamanho, timeout e retry;
- registrar métricas sem expor segredos ou anexos;
- atualizar o README com o fluxo multilíngue;
- criar testes unitários, de contrato, MCP e uma avaliação offline reproduzível.

## Ordem recomendada

1. contratos e invariantes;
2. tradutor configurável;
3. integração com OCR e anexos;
4. consenso Kimi + Nemotron;
5. localização da resposta;
6. benchmark em português;
7. ativação gradual de `auto` e depois `required`, se os resultados justificarem.
