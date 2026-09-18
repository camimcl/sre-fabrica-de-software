# Fluxo principal do protótipo

```text
Login
  -> Dashboard
      -> Projetos e endpoints
          -> Cadastrar endpoint autorizado
      -> Novo cenário
          -> Iniciar execução
              -> Monitoramento ao vivo
                  -> Parada de emergência
                  -> Conclusão
                      -> Histórico
                          -> Relatório comparativo
      -> Modelos de IA
          -> Consultar versão ativa e métricas
```

## Regras representadas

1. Um teste só pode ser configurado para um endpoint autorizado.
2. O cenário define duração, concorrência, ramp-up, timeout e limites de segurança.
3. A estratégia `IA + regras` usa previsão local de risco e mantém o fallback determinístico disponível.
4. O monitoramento mostra métricas atuais, previsão para os próximos dez segundos e decisões de aumento, manutenção ou redução da concorrência.
5. A parada de emergência interrompe novas requisições e preserva dados para auditoria.
6. O relatório compara condições equivalentes para avaliar o diferencial da IA e da otimização.
