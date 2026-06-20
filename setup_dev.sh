#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Undermap — Setup de ambiente de desenvolvimento
# Rode: bash setup_dev.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e  # para na primeira falha

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
BOLD="\033[1m"
RESET="\033[0m"

banner() {
  echo -e "${GREEN}"
  echo "  _   _           _"
  echo " | | | |_ __   __| | ___ _ __ _ __ ___   __ _ _ __"
  echo " | | | | '_ \ / _\` |/ _ \ '__| '_ \` _ \ / _\` | '_ \\"
  echo " | |_| | | | | (_| |  __/ |  | | | | | | (_| | |_) |"
  echo "  \___/|_| |_|\__,_|\___|_|  |_| |_| |_|\__,_| .__/"
  echo "                                               |_|"
  echo -e "${RESET}${BOLD}  Setup de ambiente — v0.1.0${RESET}"
  echo ""
}

step() { echo -e "\n${CYAN}${BOLD}▶ $1${RESET}"; }
ok()   { echo -e "${GREEN}  ✔ $1${RESET}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${RESET}"; }
err()  { echo -e "${RED}  ✗ $1${RESET}"; exit 1; }

banner

# ── 1. Verifica Python ────────────────────────────────────────────────────────
step "Verificando Python"
if ! command -v python3 &>/dev/null; then
  err "Python 3 não encontrado. Instale em: https://python.org"
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
  err "Python $PY_VERSION detectado. Necessário: 3.10+. Atualize em: https://python.org"
fi
ok "Python $PY_VERSION detectado"

# ── 2. Cria ambiente virtual ──────────────────────────────────────────────────
step "Criando ambiente virtual"
if [ -d ".venv" ]; then
  warn ".venv já existe — reutilizando"
else
  python3 -m venv .venv
  ok "Ambiente virtual criado em .venv/"
fi

# Ativa o venv
source .venv/bin/activate
ok "Ambiente virtual ativado"

# ── 3. Instala dependências ───────────────────────────────────────────────────
step "Instalando dependências"
pip install --upgrade pip -q
pip install -e ".[dev]" -q
ok "Dependências instaladas"

# ── 4. Configura .env ─────────────────────────────────────────────────────────
step "Configurando variáveis de ambiente"
if [ -f ".env" ]; then
  warn ".env já existe — pulando criação"
else
  cp .env.example .env
  ok ".env criado a partir de .env.example"
  echo ""
  echo -e "  ${YELLOW}${BOLD}ATENÇÃO: Edite o arquivo .env com suas credenciais:${RESET}"
  echo -e "  ${YELLOW}  • GOOGLE_API_KEY — obtenha em: console.cloud.google.com${RESET}"
  echo -e "  ${YELLOW}  • SMTP_USER / SMTP_PASSWORD — use Gmail App Password${RESET}"
  echo -e "  ${YELLOW}  • SENDER_NAME / SENDER_EMAIL — seu nome e e-mail${RESET}"
fi

# ── 5. Roda os testes ─────────────────────────────────────────────────────────
step "Rodando testes"
if pytest tests/ -q --tb=short 2>&1; then
  ok "Todos os testes passaram"
else
  warn "Alguns testes falharam — verifique acima"
fi

# ── 6. Lint rápido ────────────────────────────────────────────────────────────
step "Verificando qualidade do código"
if ruff check . -q 2>&1; then
  ok "Código sem problemas de lint"
else
  warn "Problemas de lint encontrados — rode: ruff check . para detalhes"
fi

# ── 7. Banco de dados ─────────────────────────────────────────────────────────
step "Inicializando banco de dados local"
python3 -c "
from data.models import get_engine
import os
engine = get_engine(os.getenv('DATABASE_URL', 'sqlite:///undermap.db'))
print('  Banco SQLite criado: undermap.db')
"
ok "Banco de dados pronto"

# ── Resumo ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  ✔ Setup concluído!${RESET}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
echo ""
echo -e "  Próximos passos:"
echo ""
echo -e "  ${BOLD}1. Edite suas credenciais:${RESET}"
echo -e "     nano .env"
echo ""
echo -e "  ${BOLD}2. Teste sem usar API:${RESET}"
echo -e "     undermap scan marmoraria \"São Paulo\" --mock"
echo ""
echo -e "  ${BOLD}3. Ver nichos disponíveis:${RESET}"
echo -e "     undermap nichos"
echo ""
echo -e "  ${BOLD}4. Preview de e-mail:${RESET}"
echo -e "     undermap preview marmoraria"
echo ""
echo -e "  ${CYAN}Documentação: README.md${RESET}"
echo ""
