# 📦 Orders API

API REST para gerenciamento de pedidos desenvolvida em **Node.js** com **PostgreSQL**, autenticação **JWT** e documentação **Swagger**.

---

## 🗂️ Estrutura do Projeto

```
orders-api/
├── src/
│   ├── config/
│   │   ├── database.js      # Conexão com PostgreSQL (Pool)
│   │   ├── migrate.js       # Script de criação das tabelas
│   │   └── swagger.js       # Configuração do Swagger/OpenAPI
│   ├── controllers/
│   │   ├── authController.js    # Lógica de autenticação JWT
│   │   └── orderController.js   # Lógica de negócio dos pedidos
│   ├── middleware/
│   │   └── auth.js          # Middleware de verificação do JWT
│   ├── models/
│   │   └── orderModel.js    # Queries ao banco de dados
│   ├── routes/
│   │   ├── authRoutes.js    # Rotas de autenticação
│   │   └── orderRoutes.js   # Rotas de pedidos + validações
│   ├── utils/
│   │   └── orderMapper.js   # Mapeamento PT → EN dos campos
│   └── server.js            # Entry point da aplicação
├── .env.example             # Template de variáveis de ambiente
├── .gitignore
├── package.json
└── README.md
```

---

## 🗄️ Estrutura do Banco de Dados

```sql
-- Tabela de pedidos
CREATE TABLE "Order" (
  "orderId"      VARCHAR(100) PRIMARY KEY,
  "value"        NUMERIC(15, 2) NOT NULL,
  "creationDate" TIMESTAMPTZ NOT NULL,
  "createdAt"    TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de itens (relacionada com Order via FK + CASCADE)
CREATE TABLE "Items" (
  "id"        SERIAL PRIMARY KEY,
  "orderId"   VARCHAR(100) NOT NULL REFERENCES "Order"("orderId") ON DELETE CASCADE,
  "productId" INTEGER NOT NULL,
  "quantity"  INTEGER NOT NULL,
  "price"     NUMERIC(15, 2) NOT NULL
);
```

---

## 🔄 Mapeamento de Campos (Transformação)

| Entrada (PT)     | Banco / Resposta (EN) |
|------------------|-----------------------|
| `numeroPedido`   | `orderId`             |
| `valorTotal`     | `value`               |
| `dataCriacao`    | `creationDate`        |
| `idItem`         | `productId` (int)     |
| `quantidadeItem` | `quantity`            |
| `valorItem`      | `price`               |

---

## 🚀 Como Executar

### 1. Pré-requisitos
- Node.js >= 18
- PostgreSQL >= 13

### 2. Instalação

```bash
git clone <seu-repositorio>
cd orders-api
npm install
```

### 3. Configuração

```bash
cp .env.example .env
# Edite o .env com suas credenciais do PostgreSQL e JWT secret
```

### 4. Criar as tabelas

```bash
npm run migrate
```

### 5. Iniciar o servidor

```bash
# Produção
npm start

# Desenvolvimento (com hot reload)
npm run dev
```

---

## 📡 Endpoints

### 🔐 Autenticação

| Método | URL           | Descrição           | Auth |
|--------|---------------|---------------------|------|
| POST   | `/auth/login` | Obter token JWT     | ❌   |

### 📦 Pedidos

| Método | URL               | Descrição                | Auth |
|--------|-------------------|--------------------------|------|
| POST   | `/order`          | Criar pedido             | ✅   |
| GET    | `/order/list`     | Listar todos os pedidos  | ✅   |
| GET    | `/order/:orderId` | Obter pedido por ID      | ✅   |
| PUT    | `/order/:orderId` | Atualizar pedido         | ✅   |
| DELETE | `/order/:orderId` | Remover pedido           | ✅   |

---

## 📋 Exemplos de uso

### 1. Login

```bash
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 2. Criar pedido

```bash
curl -X POST http://localhost:3000/order \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <seu_token>" \
  -d '{
    "numeroPedido": "v10089015vdb-01",
    "valorTotal": 10000,
    "dataCriacao": "2023-07-19T12:24:11.5299601+00:00",
    "items": [
      {
        "idItem": "2434",
        "quantidadeItem": 1,
        "valorItem": 1000
      }
    ]
  }'
```

### 3. Buscar pedido

```bash
curl http://localhost:3000/order/v10089015vdb-01 \
  -H "Authorization: Bearer <seu_token>"
```

### 4. Listar todos

```bash
curl http://localhost:3000/order/list \
  -H "Authorization: Bearer <seu_token>"
```

### 5. Atualizar pedido

```bash
curl -X PUT http://localhost:3000/order/v10089015vdb-01 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <seu_token>" \
  -d '{
    "valorTotal": 15000,
    "dataCriacao": "2023-07-19T12:24:11.5299601+00:00",
    "items": [
      {
        "idItem": "9999",
        "quantidadeItem": 3,
        "valorItem": 5000
      }
    ]
  }'
```

### 6. Deletar pedido

```bash
curl -X DELETE http://localhost:3000/order/v10089015vdb-01 \
  -H "Authorization: Bearer <seu_token>"
```

---

## 📖 Documentação Swagger

Após iniciar o servidor, acesse:

```
http://localhost:3000/api-docs
```

---

## 🔒 Autenticação JWT

Todas as rotas de `/order` requerem um token JWT válido.

1. Faça `POST /auth/login` com as credenciais
2. Copie o `token` da resposta
3. Use no header: `Authorization: Bearer <token>`

---

## ⚙️ Variáveis de Ambiente

| Variável         | Descrição                    | Padrão        |
|------------------|------------------------------|---------------|
| `PORT`           | Porta do servidor            | `3000`        |
| `DB_HOST`        | Host do PostgreSQL           | `localhost`   |
| `DB_PORT`        | Porta do PostgreSQL          | `5432`        |
| `DB_NAME`        | Nome do banco de dados       | `orders_db`   |
| `DB_USER`        | Usuário do PostgreSQL        | `postgres`    |
| `DB_PASSWORD`    | Senha do PostgreSQL          | —             |
| `JWT_SECRET`     | Chave secreta para JWT       | —             |
| `JWT_EXPIRES_IN` | Expiração do token           | `24h`         |
| `ADMIN_USER`     | Usuário admin para login     | `admin`       |
| `ADMIN_PASSWORD` | Senha admin para login       | `admin123`    |

---

## 🛠️ Tecnologias

- **Node.js** + **Express** — Servidor HTTP
- **PostgreSQL** + **pg** — Banco de dados relacional
- **JWT** (jsonwebtoken) — Autenticação stateless
- **express-validator** — Validação de entrada
- **swagger-jsdoc** + **swagger-ui-express** — Documentação interativa
- **dotenv** — Variáveis de ambiente
