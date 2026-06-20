"""
Scanner geolocalizado — Pilar 1 do Undermap.

Fluxo:
1. Geocodifica a região (texto → lat/lng)
2. Busca empresas do nicho na área (Places Nearby Search)
3. Busca detalhes de cada lugar (Place Details) para verificar site
4. Filtra somente os que NÃO têm website cadastrado
5. Retorna lista de LeadRaw prontos para enriquecimento
"""

import asyncio
import logging
from typing import Optional

import httpx

from core.niches import NicheProfile, get_niche
from data.models import LeadRaw

logger = logging.getLogger(__name__)

PLACES_BASE = "https://maps.googleapis.com/maps/api/place"
GEOCODE_BASE = "https://maps.googleapis.com/maps/api/geocode"


class ScannerError(Exception):
    pass


class Scanner:
    def __init__(self, api_key: str, radius_m: int = 5000):
        self.api_key  = api_key
        self.radius   = radius_m
        # Um único cliente HTTP assíncrono reutilizado em todas as chamadas
        self._client  = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        await self._client.aclose()

    # ── Geocodificação ─────────────────────────────────────────────────────────

    async def _geocode(self, region: str) -> tuple[float, float]:
        """Converte endereço/região em (latitude, longitude)."""
        r = await self._client.get(
            f"{GEOCODE_BASE}/json",
            params={"address": region, "key": self.api_key, "language": "pt-BR"},
        )
        r.raise_for_status()
        data = r.json()
        if data["status"] != "OK" or not data["results"]:
            raise ScannerError(f"Região não encontrada: '{region}'")
        loc = data["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]

    # ── Busca de lugares ───────────────────────────────────────────────────────

    async def _nearby_search(
        self, lat: float, lng: float, keyword: str, page_token: Optional[str] = None
    ) -> dict:
        """Uma chamada à Places Nearby Search API."""
        params = {
            "location": f"{lat},{lng}",
            "radius":   self.radius,
            "keyword":  keyword,
            "language": "pt-BR",
            "key":      self.api_key,
        }
        if page_token:
            params["pagetoken"] = page_token
            # Google exige delay antes de usar page_token
            await asyncio.sleep(2)

        r = await self._client.get(f"{PLACES_BASE}/nearbysearch/json", params=params)
        r.raise_for_status()
        return r.json()

    async def _place_details(self, place_id: str) -> dict:
        """Detalhes de um lugar específico — inclui website, phone, rating."""
        fields = "place_id,name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,address_components"
        r = await self._client.get(
            f"{PLACES_BASE}/details/json",
            params={"place_id": place_id, "fields": fields, "language": "pt-BR", "key": self.api_key},
        )
        r.raise_for_status()
        return r.json().get("result", {})

    # ── Extração de cidade ─────────────────────────────────────────────────────

    @staticmethod
    def _extract_city(address_components: list[dict]) -> str:
        for comp in address_components:
            if "administrative_area_level_2" in comp.get("types", []):
                return comp["long_name"]
            if "locality" in comp.get("types", []):
                return comp["long_name"]
        return "Cidade desconhecida"

    # ── Pipeline principal ─────────────────────────────────────────────────────

    async def scan(
        self,
        niche_key: str,
        region: str,
        max_results: int = 60,
    ) -> list[LeadRaw]:
        """
        Ponto de entrada principal.
        Retorna lista de LeadRaw sem website, prontos para enriquecimento.
        """
        profile: Optional[NicheProfile] = get_niche(niche_key)
        if not profile:
            raise ScannerError(f"Nicho '{niche_key}' não encontrado. Use: undermap nichos")

        logger.info(f"Geocodificando '{region}'...")
        lat, lng = await self._geocode(region)
        logger.info(f"Coordenadas: {lat:.4f}, {lng:.4f}")

        all_place_ids: set[str] = set()
        raw_leads: list[LeadRaw] = []

        # Busca por cada termo de busca do nicho
        for term in profile.search_terms:
            page_token = None
            for page in range(3):  # até 3 páginas = 60 resultados por termo
                data = await self._nearby_search(lat, lng, term, page_token)
                status = data.get("status")

                if status == "ZERO_RESULTS":
                    break
                if status not in ("OK", "NEXT_PAGE_TOKEN"):
                    logger.warning(f"Places API status: {status} para '{term}'")
                    break

                for place in data.get("results", []):
                    pid = place["place_id"]
                    if pid in all_place_ids:
                        continue
                    all_place_ids.add(pid)

                    # Busca detalhes (inclui website)
                    details = await self._place_details(pid)
                    if details.get("website"):
                        # Já tem site — não é nosso cliente
                        continue

                    city = self._extract_city(details.get("address_components", []))

                    lead = LeadRaw(
                        place_id     = pid,
                        name         = details.get("name", place.get("name", "")),
                        address      = details.get("formatted_address", ""),
                        phone        = details.get("formatted_phone_number"),
                        rating       = details.get("rating"),
                        review_count = details.get("user_ratings_total"),
                        website      = None,
                        city         = city,
                        niche        = niche_key,
                    )
                    raw_leads.append(lead)

                    if len(raw_leads) >= max_results:
                        return raw_leads

                page_token = data.get("next_page_token")
                if not page_token:
                    break

        return raw_leads


# ── Mock para desenvolvimento sem chave de API ────────────────────────────────

def mock_leads(niche_key: str, city: str, count: int = 5) -> list[LeadRaw]:
    """Gera leads falsos para testes locais sem gastar cota da API."""
    import random
    names = [
        "Marmoraria Zago", "Pedras & Arte Silva", "Granitos Costa",
        "Marmore Premium", "Arte em Pedras Oliveira",
    ]
    return [
        LeadRaw(
            place_id     = f"mock_{i:04d}",
            name         = names[i % len(names)],
            address      = f"Rua Exemplo, {100 + i} — {city}",
            phone        = f"(11) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}",
            rating       = round(random.uniform(3.8, 5.0), 1),
            review_count = random.randint(10, 200),
            website      = None,
            city         = city,
            niche        = niche_key,
        )
        for i in range(count)
    ]
