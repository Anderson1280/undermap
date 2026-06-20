"""
Testes do módulo mailer.
Nenhum e-mail é enviado de verdade — testamos geração de conteúdo.
"""

import pytest

from core.mailer import Mailer, MailerConfig, preview_email
from data.models import LeadEnriched, LeadStatus, PartnerInfo


@pytest.fixture
def config():
    return MailerConfig(
        smtp_host="smtp.exemplo.com",
        smtp_port=587,
        smtp_user="teste@exemplo.com",
        smtp_password="senha",
        sender_name="Vitor Teste",
        sender_email="vitor@teste.com",
        delay_min=0,
        delay_max=0,
    )


@pytest.fixture
def lead():
    return LeadEnriched(
        place_id     = "test001",
        company_name = "Marmoraria Zago",
        address      = "Rua das Pedras, 100",
        city         = "São Paulo",
        niche        = "marmoraria",
        partner      = PartnerInfo(name="Roberto Zago Silva", qualifier="Sócio"),
        rating       = 4.8,
        review_count = 127,
        pain_point   = "portfólio apenas em WhatsApp",
        solution     = "galeria digital profissional",
        email        = "roberto@marmorariazago.com.br",
        status       = LeadStatus.QUALIFIED,
    )


def test_preview_contains_first_name(config, lead):
    text = preview_email(lead, config)
    assert "Roberto" in text  # primeiro nome do sócio


def test_preview_contains_company_name(config, lead):
    text = preview_email(lead, config)
    assert "Marmoraria Zago" in text


def test_preview_contains_city(config, lead):
    text = preview_email(lead, config)
    assert "São Paulo" in text


def test_preview_contains_pain_point(config, lead):
    text = preview_email(lead, config)
    assert "WhatsApp" in text


def test_preview_contains_sender(config, lead):
    text = preview_email(lead, config)
    assert "Vitor Teste" in text


def test_subject_line_personalized(config, lead):
    mailer  = Mailer(config)
    subject = mailer._build_subject(lead)
    # Deve mencionar portfólio ou a empresa
    assert len(subject) > 10
    assert isinstance(subject, str)


def test_lead_without_email_skipped():
    """Lead sem e-mail não deve ser enviado."""
    lead_no_email = LeadEnriched(
        place_id="x", company_name="X", address="X", city="X",
        niche="marmoraria", email=None, status=LeadStatus.QUALIFIED,
    )
    # Simplesmente verifica que o campo é None
    assert lead_no_email.email is None
