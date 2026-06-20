"""
Matriz de gargalos por nicho.
Cada nicho define: termos de busca, dor principal e solução proposta.
Para adicionar um novo nicho, basta inserir uma entrada aqui — nenhum
outro arquivo precisa ser alterado.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NicheProfile:
    display_name: str           # nome exibido ao usuário
    search_terms: list[str]     # variações para busca no Google Maps
    pain_point:   str           # dor do cliente
    solution:     str           # solução que você oferece
    subject_line: str           # assunto do e-mail


NICHES: dict[str, NicheProfile] = {
    "restaurante": NicheProfile(
        display_name  = "Restaurantes e Lanchonetes",
        search_terms  = ["restaurante", "lanchonete", "pizzaria", "hamburgueria"],
        pain_point    = (
            "dependência de taxas de até 30% por pedido no iFood e outros "
            "apps de delivery, sem canal de venda próprio"
        ),
        solution      = (
            "site com cardápio digital e botão de pedido direto pelo WhatsApp, "
            "eliminando comissões e fidelizando clientes"
        ),
        subject_line  = "Seu restaurante pode parar de pagar 30% pro iFood",
    ),
    "clinica": NicheProfile(
        display_name  = "Clínicas e Consultórios",
        search_terms  = ["clínica", "consultório", "odontologia", "fisioterapia"],
        pain_point    = (
            "perda de consultas por falta de agendamento online 24h — "
            "clientes ligam fora do horário e escolhem o concorrente"
        ),
        solution      = (
            "site com sistema de agendamento online integrado ao WhatsApp, "
            "disponível 24h sem sobrecarregar a secretária"
        ),
        subject_line  = "{company} perde consultas por não ter agendamento online",
    ),
    "oficina": NicheProfile(
        display_name  = "Oficinas Mecânicas",
        search_terms  = ["oficina mecânica", "auto center", "mecânico", "borracharia"],
        pain_point    = (
            "clientes não retornam por falta de lembretes e orçamentos feitos "
            "no papel sem registro digital"
        ),
        solution      = (
            "site com formulário de orçamento online e histórico de atendimento, "
            "aumentando a taxa de retorno"
        ),
        subject_line  = "Como fazer clientes voltarem sempre para {company}",
    ),
    "marmoraria": NicheProfile(
        display_name  = "Marmorarias e Pedras",
        search_terms  = ["marmoraria", "granito", "mármore", "quartzo", "pedras decorativas"],
        pain_point    = (
            "portfólio de trabalhos apenas em grupos de WhatsApp — "
            "clientes potenciais não conseguem avaliar a qualidade antes de visitar"
        ),
        solution      = (
            "galeria digital profissional organizada por tipo de material e projeto, "
            "gerando contatos qualificados antes mesmo da visita"
        ),
        subject_line  = "Seu portfólio de pedras merece mais que um grupo de WhatsApp",
    ),
    "petshop": NicheProfile(
        display_name  = "Pet Shops e Clínicas Veterinárias",
        search_terms  = ["pet shop", "clínica veterinária", "banho e tosa", "veterinário"],
        pain_point    = (
            "agenda de banho e tosa gerenciada manualmente — "
            "conflitos de horário e clientes que esquecem o agendamento"
        ),
        solution      = (
            "site com agenda online e lembretes automáticos por WhatsApp, "
            "reduzindo faltas e aumentando a frequência de retorno"
        ),
        subject_line  = "Reduza faltas no {company} com agendamento automático",
    ),
    "salao": NicheProfile(
        display_name  = "Salões de Beleza e Barbearias",
        search_terms  = ["salão de beleza", "barbearia", "cabeleireiro", "estética"],
        pain_point    = (
            "dependência de plataformas como Booksy e iFace com mensalidade cara, "
            "sem propriedade sobre a carteira de clientes"
        ),
        solution      = (
            "site próprio com agendamento integrado e lista de clientes sob seu controle, "
            "sem pagar comissão para terceiros"
        ),
        subject_line  = "{company} pode ter seu próprio sistema de agendamento",
    ),
    "academia": NicheProfile(
        display_name  = "Academias e Studios",
        search_terms  = ["academia", "crossfit", "pilates", "studio fitness"],
        pain_point    = (
            "captação de alunos feita apenas por indicação — "
            "sem presença online para alcançar novos clientes na região"
        ),
        solution      = (
            "site com página de turmas, horários e formulário de matrícula online, "
            "aparecendo no Google quando alguém busca academia na região"
        ),
        subject_line  = "Novos alunos procuram academia no Google — {company} aparece?",
    ),
    "construtora": NicheProfile(
        display_name  = "Construtoras e Reformas",
        search_terms  = ["construtora", "reforma", "empreiteiro", "mão de obra", "pintura"],
        pain_point    = (
            "portfólio de obras compartilhado só por foto de WhatsApp — "
            "dificulta fechar contratos de maior valor sem credibilidade visual"
        ),
        solution      = (
            "site portfólio com galeria de antes/depois, depoimentos e formulário "
            "de orçamento, aumentando o ticket médio dos contratos"
        ),
        subject_line  = "Obras como as da {company} merecem um portfólio profissional",
    ),
}


def get_niche(key: str) -> Optional[NicheProfile]:
    """Retorna o perfil do nicho pela chave (case-insensitive)."""
    return NICHES.get(key.lower().strip())


def list_niches() -> list[str]:
    """Lista todos os nichos disponíveis."""
    return list(NICHES.keys())


def match_niche(raw_type: str) -> Optional[str]:
    """
    Tenta identificar o nicho a partir do tipo retornado pelo Google Places.
    Ex: "restaurant" → "restaurante"
    """
    mapping = {
        "restaurant":       "restaurante",
        "food":             "restaurante",
        "meal_takeaway":    "restaurante",
        "doctor":           "clinica",
        "dentist":          "clinica",
        "health":           "clinica",
        "physiotherapist":  "clinica",
        "car_repair":       "oficina",
        "pet_store":        "petshop",
        "veterinary_care":  "petshop",
        "beauty_salon":     "salao",
        "hair_care":        "salao",
        "gym":              "academia",
        "general_contractor": "construtora",
    }
    return mapping.get(raw_type.lower())
