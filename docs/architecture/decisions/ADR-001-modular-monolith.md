# ADR 001 Monólito modular para o MVP

## Contexto

O fluxo principal integra configuração, execução assíncrona, agregação de métricas, inferência local, controle de concorrência e persistência. O README anterior propunha filas e workers separados antes da validação desse fluxo.

## Decisão

O MVP será desenvolvido como monólito modular em FastAPI. Cada domínio terá uma pasta própria e interfaces pequenas nos pontos que realmente variam. PostgreSQL será o único recurso externo obrigatório nesta fase.

## Consequências

A equipe terá implantação e depuração mais simples, transações locais e menor custo operacional. Se medições futuras demonstrarem necessidade real de processamento distribuído, módulos poderão ser extraídos posteriormente sem alterar os contratos centrais.
