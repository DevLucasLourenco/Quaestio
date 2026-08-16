# Especificação: isolamento dos testes e dos provedores externos

Status: implementado

## Objetivo

Garantir que os testes unitários, de contrato e de protocolo MCP sejam reproduzíveis e não façam chamadas acidentais para os provedores configurados no `.env` real.

## Escopo

O isolamento deve abranger:

- LLM primária e secundária;
- tradutor;
- embeddings;
- verificador semântico;
- caminhos que dependam de OCR, Docker ou arquivos persistentes.

## Decisão arquitetural

Os testes não devem depender do `.env` de desenvolvimento. Provedores externos serão substituídos por dublês, e os testes que validam configuração usarão variáveis explicitamente controladas.

O `.env` real continuará disponível para smoke tests manuais, mas não será usado pela suíte padrão.

## Requisitos

- Nenhum teste unitário pode executar uma chamada de rede por acidente.
- Testes de configuração devem conseguir simular variáveis preenchidas, vazias ou ausentes.
- O conhecimento persistido usado pelos testes deve ser temporário.
- A suíte deve continuar validando o comportamento `not_configured` quando o verificador não está configurado.
- O modo de execução com provedores reais deve ser explícito e separado da suíte padrão.

## Critérios de aceitação

- `pytest` executa sem ler credenciais do `.env` real.
- A suíte completa passa sem chamadas de rede.
- O teste do verificador não configurado retorna `not_configured`.
- Um teste separado comprova que um verificador configurado é criado corretamente.
- Falhas de rede simuladas retornam `uncertain`, sem interromper o protocolo MCP.
- Nenhum segredo aparece em logs, relatórios ou mensagens de teste.

## Fora de escopo

- Alterar a política de confiabilidade do produto.
- Remover a possibilidade de executar smoke tests reais.
- Criar um novo sistema de gerenciamento de segredos.
