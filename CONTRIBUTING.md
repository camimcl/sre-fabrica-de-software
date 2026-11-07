# Fluxo de contribuição por tarefa

## Branches

Cada nova tarefa possui uma branch curta e com escopo único: `test/s09-validacoes-api`, `fix/s09-autorizacao-endpoint` ou `docs/s09-entrega-qa`. Use `feat/`, `fix/`, `test/`, `docs/` ou `chore/` conforme a natureza da alteração. Não crie uma única branch de implementação para toda a sprint. O histórico anterior permanece intacto.

Prefira partir da `main` atualizada. Quando uma tarefa depender de outra ainda não integrada, é possível empilhar branches: registre a branch-base e abra o PR contra ela. Após integrar a base, ajuste o destino para `main` e confirme o diff. A branch final de documentação pode depender dos testes e correções; isso não substitui suas branches e revisões individuais.

## Commits e revisão

- Um commit deve conter uma mudança coerente, com título `tipo(escopo): descrição` e explicação do motivo quando necessário.
- Separe teste reprodutor, correção e documentação quando forem etapas úteis de revisão. Identifique o bug ou caso de teste correspondente.
- Não crie commits vazios, alterações cosméticas artificiais ou reescrita de histórico para aumentar participação aparente.
- Registre `Co-authored-by` apenas com atribuição válida e email fornecido pelo integrante; os trailers ficam juntos no último parágrafo.
- Cada PR apresenta escopo, riscos, comandos/resultados, evidências, dependências e pendências. Um teste local não equivale a um check remoto executado.
- Não trabalhe diretamente na `main`. A integração ocorre por PR revisado; preservar commits individuais facilita rastrear testes e correções.

## QA e documentação

Antes de corrigir um bug, registre passos mínimos, esperado, obtido, impacto e ambiente. Acrescente teste de regressão na interface pública pertinente, verifique a falha e depois a correção. No relatório, diferencie bug confirmado, melhoria e limitação conhecida.

Nunca publique `.env`, tokens, dados pessoais, modelos serializados ou dumps do banco. Use dados descartáveis nos testes. Para capturas, apresente contexto, procedimento e conclusão; uma imagem sem explicação não comprova o comportamento.

O PDF de entrega é incremental: sprints anteriores preservadas, nova seção vinculada às evidências da revisão atual. Instruções operacionais detalhadas ficam no README e nos guias do repositório. As evidências de desempenho precisam informar as condições e não devem extrapolar uma amostra local.
