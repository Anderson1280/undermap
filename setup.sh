#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  Undermap — Setup local em um comando
#  Uso: bash setup.sh
# ─────────────────────────────────────────────────────────────────

set -e  # para se qualquer comando falhar

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${GREEN}  Undermap — Setup${NC}"
echo "  ─────────────────"
echo ""

# 1. Verifica Python
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}✗ Python 3 não encontrado. Instale em: https://python.org${NC}"
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✔${NC} Python $PYTHON_VERSION encontrado"

# 2. Cria ambiente virtual
if [ ! -d ".venv" ]; then
  echo "  Criando ambiente virtual..."
  python3 -m venv .venv
  echo -e "${GREEN}✔${NC} Ambiente virtual criado"
else
  echo -e "${GREEN}✔${NC} Ambiente virtual já existe"
fi

# 3. Ativa e instala dependências
source .venv/bin/activate
echo "  Instalando dependências..."
pip install -e ".[dev]" -q
echo -e "${GREEN}✔${NC} Dependências instaladas"

# 4. Copia .env se não existir
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "${YELLOW}⚡${NC} Arquivo .env criado — preencha suas chaves antes de rodar"
else
  echo -e "${GREEN}✔${NC} .env já configurado"
fi

# 5. Roda testes
echo "  Rodando testes..."
if pytest tests/ -q --tb=short 2>/dev/null; then
  echo -e "${GREEN}✔${NC} Todos os testes passaram"
else
  echo -e "${YELLOW}⚠${NC} Alguns testes falharam — verifique acima"
fi

echo ""
echo -e "${GREEN}  Pronto! Para começar:${NC}"
echo ""
echo "    source .venv/bin/activate"
echo "    undermap --help"
echo "    undermap nichos"
echo "    undermap scan marmoraria \"São Paulo\" --mock"
echo ""
