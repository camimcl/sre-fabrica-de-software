# Frontend

Interface React, Vite e TypeScript para demonstrar os fluxos persistidos do LoadForge.

## Funcionalidades

- cadastro público de conta com perfil Visualizador;
- login integrado à API e ao PostgreSQL;
- identificação do perfil ativo;
- consulta de projetos e endpoints para QA e Visualizador;
- CRUD de projetos e endpoints para o QA proprietário;
- listagem e criação de usuários por QA.

## Desenvolvimento local

Com a API disponível em `http://127.0.0.1:8000`:

```bash
npm install
npm run dev
```

A interface ficará em `http://127.0.0.1:5173`. O proxy do Vite encaminha `/api` para a API local sem expor a porta do banco de dados.

## Build

```bash
npm run build
```

O resultado é criado em `dist/`. No Docker Compose, uma imagem Nginx entrega esses arquivos e encaminha `/api` ao container da aplicação.
