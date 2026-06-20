> ⚠️ **Licença restrita** — Código público para fins de portfólio. 
> Uso, cópia ou redistribuição sem autorização do autor é proibido. 
> Contato: undersomm@hotmail.com
# Undermap

[![CI](https://github.com/seu-usuario/undermap/actions/workflows/ci.yml/badge.svg)](https://github.com/seu-usuario/undermap/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![License: Restrita](https://img.shields.io/badge/License-Restrita-red.svg)](LICENSE)
[![Versão](https://img.shields.io/badge/vers%C3%A3o-0.1.0-brightgreen)](https://github.com/seu-usuario/undermap/releases)

**Prospecção B2B automatizada para devs e agências web.**  
Encontra empresas locais ativas, sem site, enriquece com dados da Receita Federal e envia cold emails personalizados — tudo pelo terminal.

```
  _   _           _
 | | | |_ __   __| | ___ _ __ _ __ ___   __ _ _ __
 | | | | '_ \ / _` |/ _ \ '__| '_ ` _ \ / _` | '_ \
 | |_| | | | | (_| |  __/ |  | | | | | | (_| | |_) |
  \___/|_| |_|\__,_|\___|_|  |_| |_| |_|\__,_| .__/
                                               |_|
```

---

## O que faz

1. **Varre o Google Maps** por empresas no nicho + região escolhidos  
2. **Filtra** somente as que não têm site cadastrado  
3. **Enriquece** cada lead com CNPJ, porte, nome do sócio (via Receita Federal)  
4. **Gera e envia** cold emails personalizados com o gargalo específico do nicho  

---

## Demo

```bash
$ undermap scan marmoraria "Zona Leste São Paulo" --limite 20

  Undermap v0.1.0 — Prospecção B2B automatizada

  ── Etapa 1 · Varredura geolocalizada ─────────────────────────────────
  ✔ 18 empresas sem site encontradas

  ── Etapa 2 · Enriquecimento de dados ─────────────────────────────────
   Empresa               ⭐    Porte  Sócio       E-mail              Status
   Marmoraria Zago       4.8   ME     Roberto     roberto@zago...     ✔ qualificado
   Granitos Silva        4.6   EPP    Ana Paula   —                   ✔ qualificado
   Arte em Pedras Costa  4.9   ME     Marcos      marcos@arte...      ✔ qualificado
   ...

  ✔ 14 leads qualificados — salvos localmente

  ┌─────────────────────────────────────────────────┐
  │ Pronto! Para enviar os e-mails:                 │
  │   undermap scan marmoraria "Zona Leste SP" -e   │
  └─────────────────────────────────────────────────┘
```

---

## Instalação

### Pré-requisitos

- Python 3.10+
- Git
- Conta Google Cloud (para a Places API) — [criar aqui](https://console.cloud.google.com)
- Gmail com App Password — [configurar aqui](https://myaccount.google.com/apppasswords)

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/undermap.git
cd undermap

# 2. Crie o ambiente virtual
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows

# 3. Instale o projeto
pip install -e .

# 4. Configure as credenciais
cp .env.example .env
# Edite o .env com sua chave do Google e senha SMTP

# 5. Teste a instalação
undermap --help
```

### Configuração do `.env`

```env
GOOGLE_API_KEY=sua_chave_aqui
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seuemail@gmail.com
SMTP_PASSWORD=sua_app_password
SENDER_NAME=Seu Nome
SENDER_EMAIL=seuemail@gmail.com
```

---

## Uso

### Comandos disponíveis

```bash
# Ver todos os nichos disponíveis
undermap nichos

# Varrer um nicho e salvar leads (sem enviar e-mails)
undermap scan <nicho> "<região>"

# Varrer E enviar e-mails
undermap scan <nicho> "<região>" --enviar

# Testar sem usar a API (dados fictícios)
undermap scan <nicho> "<região>" --mock

# Preview do e-mail antes de enviar
undermap preview <nicho>

# Ver leads salvos localmente
undermap leads
undermap leads --status qualified
```

### Exemplos reais

```bash
# Marmorarias na Zona Leste de SP
undermap scan marmoraria "Zona Leste São Paulo" --limite 50

# Restaurantes em Campinas, já enviando e-mails
undermap scan restaurante "Centro Campinas" --enviar

# Clínicas em Curitiba, raio de 10km
undermap scan clinica "Curitiba" --raio 10000

# Testar fluxo completo sem gastar cota da API
undermap scan oficina "Belo Horizonte" --mock --enviar
```

---

## Nichos disponíveis

| Chave         | Nicho                     | Gargalo mapeado                          |
|---------------|---------------------------|------------------------------------------|
| `restaurante` | Restaurantes              | Dependência de taxas do iFood            |
| `clinica`     | Clínicas e Consultórios   | Falta de agendamento online 24h          |
| `oficina`     | Oficinas Mecânicas        | Sem registro digital de orçamentos       |
| `marmoraria`  | Marmorarias e Pedras      | Portfólio apenas no WhatsApp             |
| `petshop`     | Pet Shops e Veterinárias  | Agenda de tosa no papel                  |
| `salao`       | Salões e Barbearias       | Dependência de plataformas caras         |
| `academia`    | Academias e Studios       | Captação apenas por indicação            |
| `construtora` | Construtoras e Reformas   | Portfólio sem credibilidade visual       |

---

## Arquitetura

```
undermap/
├── core/
│   ├── scanner.py      # Varredura Google Maps + filtro de ausência digital
│   ├── enricher.py     # Enriquecimento via Receita Federal (BrasilAPI)
│   ├── mailer.py       # Cold mailing personalizado por nicho
│   └── niches.py       # Matriz de gargalos — adicione novos nichos aqui
├── data/
│   └── models.py       # Modelos Pydantic + SQLAlchemy (SQLite local)
├── cli/
│   └── main.py         # Interface de terminal (Typer + Rich)
├── tests/              # Testes unitários (pytest)
└── .github/workflows/  # CI: lint + testes + security scan
```

**Stack:** Python 3.10+ · Typer · Rich · httpx · Pydantic v2 · SQLAlchemy · Jinja2

---

## Desenvolvimento

```bash
# Instalar dependências de dev
pip install -e ".[dev]"

# Rodar testes
pytest tests/ -v

# Lint e formatação
ruff check .
ruff format .

# Scan de segurança
bandit -r core/ cli/ data/ -ll
```

---

## Planos

| Plano    | Leads/mês | Nichos  | Preço     |
|----------|-----------|---------|-----------|
| Starter  | 20        | 3       | Gratuito  |
| Pro      | 500       | Todos   | R$ 97/mês |
| Agência  | Ilimitado | Todos   | R$ 297/mês|

→ [Assinar em undermap.com.br](https://undermap.com.br)

---

## Contribuindo

1. Fork o repositório
2. Crie uma branch: `git checkout -b feat/novo-nicho`
3. Adicione seu nicho em `core/niches.py`
4. Rode os testes: `pytest tests/`
5. Abra um Pull Request

---

## Licença

MIT © 2025 — Veja [LICENSE](LICENSE) para detalhes.
