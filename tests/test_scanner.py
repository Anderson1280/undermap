"""
Testes do módulo scanner.
Usa mocks para não depender da Google API nos testes.
"""

import pytest

from core.scanner import Scanner, mock_leads
from data.models import LeadRaw


# ── Testes do filtro de website ────────────────────────────────────────────────

def test_mock_leads_returns_correct_count():
    leads = mock_leads("marmoraria", "São Paulo", count=5)
    assert len(leads) == 5


def test_mock_leads_have_no_website():
    leads = mock_leads("marmoraria", "São Paulo", count=3)
    for lead in leads:
        assert lead.website is None


def test_mock_leads_correct_niche():
    leads = mock_leads("restaurante", "Campinas", count=2)
    for lead in leads:
        assert lead.niche == "restaurante"
        assert "Campinas" in lead.city


def test_lead_raw_validation():
    lead = LeadRaw(
        place_id="abc123",
        name="Marmoraria Teste",
        address="Rua X, 100",
        phone="(11) 99999-9999",
        rating=4.5,
        review_count=50,
        website=None,
        city="São Paulo",
        niche="marmoraria",
    )
    assert lead.rating == 4.5
    assert lead.website is None


def test_lead_raw_invalid_rating():
    with pytest.raises(Exception):
        LeadRaw(
            place_id="x", name="X", address="X", city="X", niche="X",
            rating=6.0,  # inválido: > 5
        )


def test_extract_city_from_components():
    """Testa a extração de cidade dos address_components do Google."""
    components = [
        {"types": ["street_number"], "long_name": "100"},
        {"types": ["administrative_area_level_2"], "long_name": "São Paulo"},
        {"types": ["country"], "long_name": "Brazil"},
    ]
    city = Scanner._extract_city(components)
    assert city == "São Paulo"


def test_extract_city_fallback_to_locality():
    components = [
        {"types": ["locality"], "long_name": "Campinas"},
    ]
    city = Scanner._extract_city(components)
    assert city == "Campinas"


def test_extract_city_unknown():
    city = Scanner._extract_city([])
    assert city == "Cidade desconhecida"
