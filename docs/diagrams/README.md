# Guia de leitura dos diagramas

Os quatro diagramas da Sprint 02 usam uma organização visual comum: o caminho principal é lido da esquerda para a direita, os desdobramentos ficam abaixo da entidade ou componente de origem e as ligações seguem trajetos ortogonais para evitar sobreposição.

## Convenções

- azul-claro: aplicação, domínio e execução;
- verde: segurança, persistência e contratos de serviço;
- lilás: inteligência artificial e artefatos do modelo;
- laranja: otimização e decisões de controle;
- linha contínua: fluxo ou relacionamento principal;
- linha tracejada: vínculo opcional ou implementação de interface.

No diagrama de classes, apenas as associações centrais são desenhadas. Referências secundárias permanecem nos atributos UUID. No modelo relacional, todas as chaves estrangeiras são escritas dentro das tabelas como `FK -> tabela.id`; as linhas representam somente o caminho principal. Essa escolha mantém a informação completa sem criar cruzamentos difíceis de acompanhar.

## Arquivos

| Diagrama | Fonte semântica | Exportação oficial |
|---|---|---|
| Arquitetura | `architecture.mmd` | `exports/architecture.png` |
| Classes | `classes.mmd` | `exports/classes.png` |
| MER | `mer.mmd` | `exports/mer.png` |
| Modelo relacional | `relational-model.mmd` | `exports/relational-model.png` |

As fontes Mermaid preservam a estrutura editável e os relacionamentos completos. As imagens oficiais são geradas por `scripts/render_diagrams.py`, que aplica o posicionamento explícito adotado no documento técnico. Execute `python scripts/validate_diagrams.py` para conferir a presença, as dimensões e a legibilidade mínima dos quatro artefatos.

## Decisões representadas

**Arquitetura.** O monólito modular mantém o ciclo de execução, métricas, previsão e controle no mesmo processo, reduzindo a complexidade do MVP. As três faixas separam o acesso autorizado, o ciclo adaptativo e a persistência.

**Classes.** Entidades persistidas e serviços foram colocados em painéis diferentes. Interfaces pequenas desacoplam o coordenador dos algoritmos de IA e controle, permitindo fallback por regras e testes independentes.

**MER.** Os agrupamentos destacam a passagem de configuração para experimento e resultado. Relações de resultado são opcionais porque execuções e janelas podem existir antes da conclusão do processamento.

**Modelo relacional.** UUIDs identificam os registros, chaves estrangeiras preservam a rastreabilidade e restrições únicas limitam previsão, decisão e relatório ao seu registro de origem. A cardinalidade do desenho acompanha `database/schema.sql`, a migration Alembic e os modelos SQLAlchemy.
