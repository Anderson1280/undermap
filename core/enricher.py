"""
Enricher — Pilar 2 do Undermap.

Dado um LeadRaw (sem site, vindo do scanner), o enricher:
1. Tenta descobrir o CNPJ da empresa via busca no nome + cidade
2. Consulta a API pública da Receita Federal (sem autenticação)
3. Valida se o CNPJ está ATIVO
4. Extrai porte (ME/EPP/DEMAIS) e nome do primeiro sócio (QSA)
5. Injeta pain_point e solution do nicho
6. Tenta descobrir e-mail de contato
7. Retorna LeadEnriched ou None se inelegível
"""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import quote

import httpx

from core.niches import NicheProfile, get_niche
from data.models import LeadEnriched, LeadRaw, LeadStatus, PartnerInfo

logger = logging.getLogger(__name__)

# API pública da Receita Federal (via proxy BrasilAPI — sem autenticação)
BRASIL_API = "https://brasilapi.com.br/api/cnpj/v1"

# Para buscar CNPJ pelo nome (ReceitaWS — gratuito com limite)
RECEITAWS_SEARCH = "https://receitaws.com.br/v1/cnpj"


class EnricherError(Exception):
    pass


class Enricher:
    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": "Undermap/0.1 (contato@undermap.com.br)"},
        )

    async def close(self):
        await self._client.aclose()

    # ── Busca de CNPJ pelo nome ────────────────────────────────────────────────

    async def _find_cnpj(self, company_name: str, city: str) -> Optional[str]:
        """
        Tenta encontrar o CNPJ da empresa usando a BrasilAPI de busca por razão social.
        Fallback: retorna None (lead sem CNPJ ainda pode receber e-mail).
        """
        try:
            query = quote(f"{company_name} {city}")
            r = await self._client.get(
                f"https://brasilapi.com.br/api/cnpj/v1/search?query={query}&municipio={city}"
            )
            if r.status_code == 200:
                results = r.json()
                if results:
                    return results[0].get("cnpj")
        except Exception as e:
            logger.debug(f"Busca de CNPJ falhou para '{company_name}': {e}")
        return None

    # ── Consulta de CNPJ ──────────────────────────────────────────────────────

    async def _fetch_cnpj_data(self, cnpj: str) -> Optional[dict]:
        """
        Consulta dados completos de um CNPJ na BrasilAPI.
        Sem autenticação, sem custo. Limite: ~3 req/min por IP.
        """
        # Remove caracteres não numéricos
        cnpj_clean = re.sub(r"\D", "", cnpj)
        if len(cnpj_clean) != 14:
            return None

        try:
            await asyncio.sleep(1.2)  # respeita rate limit da API pública
            r = await self._client.get(f"{BRASIL_API}/{cnpj_clean}")
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                logger.warning("Rate limit da BrasilAPI atingido — aguardando 30s...")
                await asyncio.sleep(30)
                r = await self._client.get(f"{BRASIL_API}/{cnpj_clean}")
                return r.json() if r.status_code == 200 else None
        except Exception as e:
            logger.debug(f"Erro ao consultar CNPJ {cnpj}: {e}")
        return None

    # ── Extração de e-mail de contato ─────────────────────────────────────────

    @staticmethod
    def _extract_email(cnpj_data: dict) -> Optional[str]:
        """Extrai e-mail do registro da Receita Federal, se disponível."""
        email = cnpj_data.get("email")
        if email and "@" in email and email.lower() not in ("", "null", "não informado"):
            return email.strip().lower()
        return None

    # ── Pipeline principal ─────────────────────────────────────────────────────

    async def enrich(self, lead: LeadRaw) -> Optional[LeadEnriched]:
        """
        Enriquece um LeadRaw.
        Retorna None se o lead for inelegível (CNPJ inativo, etc).
        Retorna LeadEnriched mesmo sem CNPJ (alguns leads valem o contato).
        """
        profile: Optional[NicheProfile] = get_niche(lead.niche)
        if not profile:
            return None

        # Tenta encontrar o CNPJ
        cnpj = await self._find_cnpj(lead.name, lead.city)

        cnpj_status   = None
        company_size  = None
        founded_year  = None
        partner       = None
        email         = None

        if cnpj:
            data = await self._fetch_cnpj_data(cnpj)
            if data:
                cnpj_status = data.get("descricao_situacao_cadastral", "").upper()

                # Rejeita CNPJs inativos
                if cnpj_status and cnpj_status not in ("ATIVA",):
                    logger.info(f"Rejeitado: {lead.name} — CNPJ {cnpj_status}")
                    return None

                # Porte
                porte_map = {
                    "MICRO EMPRESA":             "ME",
                    "EMPRESA DE PEQUENO PORTE":  "EPP",
                    "DEMAIS":                    "DEMAIS",
                }
                raw_porte  = data.get("porte", "")
                company_size = porte_map.get(raw_porte.upper(), raw_porte)

                # Ano de fundação
                abertura = data.get("data_inicio_atividade", "")
                if abertura and len(abertura) >= 4:
                    try:
                        founded_year = int(abertura[:4])
                    except ValueError:
                        pass

                # Sócio principal (QSA)
                qsa = data.get("qsa") or []
                if qsa:
                    first = qsa[0]
                    partner = PartnerInfo(
                        name      = first.get("nome_socio", "").title(),
                        qualifier = first.get("qualificacao_socio", "Sócio"),
                    )

                email = self._extract_email(data)

        # Monta o lead enriquecido
        enriched = LeadEnriched(
            place_id     = lead.place_id,
            company_name = lead.name,
            address      = lead.address,
            phone        = lead.phone,
            rating       = lead.rating,
            review_count = lead.review_count,
            city         = lead.city,
            niche        = lead.niche,
            cnpj         = cnpj,
            cnpj_status  = cnpj_status or "NÃO ENCONTRADO",
            company_size = company_size,
            founded_year = founded_year,
            partner      = partner,
            pain_point   = profile.pain_point,
            solution     = profile.solution,
            email        = email,
            status       = LeadStatus.QUALIFIED,
        )
        return enriched

    async def enrich_batch(
        self,
        leads: list[LeadRaw],
        on_progress=None,
    ) -> list[LeadEnriched]:
        """
        Enriquece uma lista de leads em sequência (respeitando rate limits).
        `on_progress(current, total, lead)` é chamado a cada lead processado.
        """
        results = []
        for i, lead in enumerate(leads):
            enriched = await self.enrich(lead)
            if enriched:
                results.append(enriched)
            if on_progress:
                on_progress(i + 1, len(leads), lead, enriched)
        return results
