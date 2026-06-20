"""
Testes da matriz de nichos.
"""

import pytest
from core.niches import get_niche, list_niches, match_niche, NICHES


def test_all_niches_have_required_fields():
    for key, profile in NICHES.items():
        assert profile.display_name,  f"{key}: display_name vazio"
        assert profile.search_terms,  f"{key}: search_terms vazio"
        assert profile.pain_point,    f"{key}: pain_point vazio"
        assert profile.solution,      f"{key}: solution vazio"
        assert profile.subject_line,  f"{key}: subject_line vazio"


def test_get_niche_case_insensitive():
    assert get_niche("RESTAURANTE") is not None
    assert get_niche("Marmoraria") is not None
    assert get_niche("  clinica  ") is not None


def test_get_niche_not_found():
    assert get_niche("nicho_inexistente") is None


def test_list_niches_returns_all():
    keys = list_niches()
    assert len(keys) == len(NICHES)
    assert "restaurante" in keys
    assert "marmoraria"  in keys


def test_match_niche_google_types():
    assert match_niche("restaurant")  == "restaurante"
    assert match_niche("car_repair")  == "oficina"
    assert match_niche("dentist")     == "clinica"
    assert match_niche("pet_store")   == "petshop"
    assert match_niche("gym")         == "academia"


def test_match_niche_unknown():
    assert match_niche("bank") is None


def test_subject_line_format():
    profile = get_niche("clinica")
    # subject_line com placeholder deve formatar corretamente
    formatted = profile.subject_line.format(company="Clínica ABC")
    assert "Clínica ABC" in formatted or "{company}" not in formatted
