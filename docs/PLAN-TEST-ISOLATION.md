# Plano de implementação: isolamento dos testes e dos provedores externos

Status: implementado

## Fase 1 — Mapeamento das dependências

- localizar todos os pontos que leem variáveis de ambiente;
- identificar imports que inicializam serviços globais;
- listar testes que podem acessar rede, Docker, Tesseract ou armazenamento persistente;
- definir o conjunto mínimo de dublês necessários.

Saída: matriz de dependências externas por módulo e teste.

## Fase 2 — Ambiente de teste controlado

- criar fixture de ambiente para limpar ou sobrescrever variáveis `QUAESTIO_*`;
- impedir que o `.env` de desenvolvimento ative provedores durante a suíte padrão;
- usar diretórios temporários para a base de conhecimento;
- garantir restauração do ambiente após cada teste.

Saída: testes independentes da máquina e das credenciais locais.

## Fase 3 — Dublês e testes de configuração

- adicionar dublês para solver, tradutor, embeddings e verificador semântico;
- testar configuração completa, parcial e ausente;
- testar timeout, resposta inválida e erro de rede;
- preservar os testes de consenso e de falha fechada.

Saída: cobertura determinística dos caminhos externos.

## Fase 4 — Execução e documentação

- executar a suíte padrão sem credenciais;
- adicionar um comando separado para smoke tests reais;
- documentar a diferença entre `pytest` e validação externa;
- verificar que logs de teste não expõem segredos.

## Ordem recomendada

1. fixture de ambiente;
2. armazenamento temporário;
3. dublês dos provedores;
4. testes de erro e configuração;
5. comando separado de smoke test;
6. documentação.

## Implementação concluída

- carregamento do `.env` pode ser desativado com `QUAESTIO_DISABLE_DOTENV`;
- a suíte padrão remove configurações externas antes dos imports dos testes;
- testes permanecem livres de chamadas reais por padrão;
- o comportamento de configuração externa continua disponível para smoke tests explícitos.
