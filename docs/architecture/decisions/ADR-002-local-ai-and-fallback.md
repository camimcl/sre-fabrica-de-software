# ADR 002 IA local e fallback por regras

## Contexto

O projeto precisa demonstrar implementação própria de inteligência artificial e otimização, sem limitar-se ao consumo de uma API ou a uma funcionalidade superficial.

## Decisão

O `DegradationRiskModel` será treinado pela equipe e executado localmente por um adaptador que atende `RiskPredictor`. O `AdaptiveLoadController` combinará a previsão com as métricas atuais. Quando a versão aprovada do modelo estiver indisponível, a entrada for inválida ou a inferência falhar, o `RulesController` assumirá automaticamente.

Cada decisão registrará janela, estratégia, versão do modelo, probabilidade, concorrência anterior, concorrência nova e motivo.

## Consequências

O teste continua seguro mesmo sem IA, as decisões podem ser explicadas e as três estratégias podem ser comparadas. A aplicação não depende de rede ou fornecedor externo para inferência.
