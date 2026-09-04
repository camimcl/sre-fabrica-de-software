# LoadForge (SRE) 🔨

> Plataforma SaaS de testes de carga e avaliação de resiliência (Stress & Resilience Evaluator).
> Transforma a infraestrutura web em um alvo de testes controlados, disparando milhares de requisições
> simultâneas otimizadas via processamento paralelo (CPU/GPU) para prever gargalos antes da produção.

**Projeto Integrador — Fábrica de Software + Tópicos Avançados · UNINASSAU · 2026.2**

---

## O problema

Na atualidade, muitas empresas lançam aplicações e APIs sem conhecer seus reais gargalos de infraestrutura.
Picos sazonais de tráfego, campanhas de marketing ou integrações abruptas podem causar o colapso do 
sistema por falta de escalabilidade previsível.

Ferramentas de estresse convencionais costumam ser complexas, exigem configuração profunda em 
infraestrutura local (terminais) e não fornecem dashboards analíticos intuitivos para a diretoria. 
O problema que resolvemos é a **imprevisibilidade de falhas sob alta carga**. É, na verdade, um 
desafio de concorrência massiva e orquestração de rede.

## A solução

| Etapa | O que o sistema faz |
|---|---|
| **1. Configuração** | O usuário define o alvo (URL/Endpoint), os headers HTTP e o payload. |
| **2. Orquestração** | A plataforma converte a configuração em um plano de ataque (Ramp-up, Pico, Duração). |
| **3. Aceleração (Core)** | O motor próprio dispara o tráfego nos modos — serial, CPU multi-thread (Python) ou **GPU (C++/CUDA)**. |
| **4. Ingestão de Logs** | Captura em tempo real de latência, códigos de status (200, 404, 500) e timeouts. |
| **5. Análise** | Processamento dos resultados para encontrar o ponto exato de degradação da aplicação alvo. |
| **6. Relatório** | Geração de dashboards com gráficos de vazão (throughput) e tempo de resposta. |

**KPI de produto:** Acurácia na detecção do limite de ruptura (breaking point) da aplicação alvo antes que falhas ocorram em produção.

**KPIs técnicos:** *Speedup* do motor de carga em C++/GPU sobre o baseline Python `asyncio` (meta ≥ 10× mais requisições por segundo utilizando o mesmo hardware).

---

## Princípio de projeto: tráfego real, métricas exatas

A geração de carga e a medição de latência são **estritamente determinísticas**. O tempo de resposta 
registrado no dashboard reflete exatamente o ciclo de ida e volta (RTT) do pacote de rede. Não utilizamos 
estimativas ou médias móveis não documentadas. 

Esta precisão é o que permite ao Engenheiro de QA confiar na plataforma: dois testes com a mesma 
configuração de concorrência, contra o mesmo servidor alvo isolado, devem produzir gargalos estatisticamente idênticos.

---

## Stack Tecnológica Sugerida

| Camada | Tecnologia | Por quê |
|---|---|---|
| Núcleo de Estresse | **C++ / CUDA / libcurl** | Máximo desempenho para abrir milhares de sockets TCP simultâneos via GPU/Threads. |
| Orquestração & Filas | **Celery + Redis** | Desacopla o teste demorado da interface web, rodando o estresse em background. |
| Backend / API | **Python 3.11 + FastAPI** | Alta performance assíncrona, integra nativamente com Celery e scripts de análise. |
| Banco de Dados | **PostgreSQL 16** | Armazenamento relacional robusto para histórico de clientes, projetos e milhões de logs de requisição. |
| Interface | **React + Vite + Tailwind** | Dashboard moderno, focado em atualização de métricas em tempo real (WebSockets). |
| Gráficos | **ECharts / Plotly** | Renderização rápida de séries temporais densas (latência ao longo do tempo). |
| Versionamento | **Git + GitHub** | Issues, Projects, Pull Requests e CI/CD. |
| Execução | **Docker Compose** | `docker compose up` sobe a API, o Redis, o Worker e o Banco de uma só vez. |

> O sistema **funciona sem GPU**: quando não há placa compatível, o otimizador cai automaticamente para o
> modo Python Multiprocessing + AsyncIO. A GPU/C++ atua como um acelerador de tráfego, não um bloqueio.

## Arquitetura

```text
Navegador ──▶ Frontend (React + Vite) ──▶ Dashboards e Gráficos
                   │  REST / WebSockets
                   ▼
              API (FastAPI) ────────────▶ PostgreSQL 16 (Projetos/Usuários)
                   │
                   ▼  Envia Job de Teste
             Mensageria (Redis)
                   │
        ┌──────────┴───────────┬────────────────┐
        ▼                      ▼                ▼
   Worker Padrão          Worker Acelerado    Processador de 
 (Python AsyncIO)       (C++ / OpenMP / CUDA) Métricas (Pandas)
        │                      │
        └──────▶ ALVO ◀────────┘
            (Aplicação Testada)
```
## Equipe

**Turma:** CC8NB

| Integrante | GitHub | Papel |
|---|---|---|
|Camile Marcele Pereira de Araújo|  [@camimcl](https://github.com/camimcl) | *Product Owner / Analista de QA* |
|Ricardo Cezar Ottoni |  [@RicardoAlmeida06](https://github.com/RicardoAlmeida06) | *Engenheiro de Dados / Infraestrutura* |
|Aline Bianca Arantes da Silva |[@aline-exe ](https://github.com/aline-exe) | *Desenvolvedor Backend (Python)* |
|Emerson Wallace Barcelos de Araujo |  [@itswall](https://github.com/itswall) | *Scrum Master / Desenvolvedor Backend* |
|Cayo Vitor Fagundes |  [@cayo-vitor](https://github.com/cayo-vitor) | *Desenvolvedor Frontend / UI/UX* |

**Orientação:** Prof. Antenor Parnaíba (Tópicos Avançados) e Prof.ª Pryscilla Gonçalves (Fábrica de Software) 

---
