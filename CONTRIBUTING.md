# Como contribuir com o Undermap

Obrigado pelo interesse! Contribuições são bem-vindas.

## Setup de desenvolvimento

```bash
git clone https://github.com/seu-user/undermap
cd undermap
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # preencha suas chaves
```

## Antes de abrir um PR

```bash
ruff check . && ruff format .   # lint e formatação
pytest tests/ -v                # todos os testes devem passar
bandit -r core/ cli/ data/ -ll  # sem vulnerabilidades críticas
```

## Adicionar um novo nicho

1. Abra `core/niches.py`
2. Adicione uma entrada no dicionário `NICHES` seguindo o padrão existente
3. Adicione um teste em `tests/test_niches.py`
4. Abra um PR com o título: `feat(nicho): adiciona <nome-do-nicho>`

## Convenção de commits

```
feat:     nova funcionalidade
fix:      correção de bug
docs:     documentação
test:     testes
refactor: refatoração sem mudança de comportamento
chore:    tarefas de manutenção
```
