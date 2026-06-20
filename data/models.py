"""
Modelos de dados do Undermap.
- LeadRaw:    dados brutos vindos do Google Places
- LeadEnrich: lead enriquecido com CNPJ + gargalo
- EmailLog:   registro de e-mails enviados (anti-duplicata)
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session


# ─── Enums ────────────────────────────────────────────────────────────────────

class LeadStatus(str, Enum):
    PENDING   = "pending"    # encontrado, não enriquecido
    QUALIFIED = "qualified"  # enriquecido e aprovado
    EMAILED   = "emailed"    # e-mail enviado
    REJECTED  = "rejected"   # CNPJ inativo ou site encontrado


# ─── Pydantic (validação de dados em memória) ─────────────────────────────────

class LeadRaw(BaseModel):
    """Dados brutos do Google Places API."""
    place_id:    str
    name:        str
    address:     str
    phone:       Optional[str]  = None
    rating:      Optional[float] = None
    review_count: Optional[int] = None
    website:     Optional[str]  = None
    city:        str
    niche:       str

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 <= v <= 5):
            raise ValueError("Rating deve ser entre 0 e 5")
        return v


class PartnerInfo(BaseModel):
    """Informação de sócio (QSA) da Receita Federal."""
    name:        str
    qualifier:   str  # ex: "Sócio-Administrador"


class LeadEnriched(BaseModel):
    """Lead completo, pronto para abordagem."""
    # Dados do Google Places
    place_id:    str
    company_name: str
    address:     str
    phone:       Optional[str]    = None
    rating:      Optional[float]  = None
    review_count: Optional[int]   = None
    city:        str
    niche:       str

    # Dados da Receita Federal
    cnpj:        Optional[str]     = None
    cnpj_status: Optional[str]     = None   # "ATIVA", "BAIXADA", etc.
    company_size: Optional[str]    = None   # "ME", "EPP", "DEMAIS"
    founded_year: Optional[int]    = None
    partner:     Optional[PartnerInfo] = None

    # Inteligência de nicho
    pain_point:  Optional[str]     = None
    solution:    Optional[str]     = None

    # Contato
    email:       Optional[str]     = None
    status:      LeadStatus        = LeadStatus.PENDING


# ─── SQLAlchemy (persistência local SQLite) ───────────────────────────────────

class Base(DeclarativeBase):
    pass


class LeadRecord(Base):
    """Tabela de leads persistidos localmente."""
    __tablename__ = "leads"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    place_id     = Column(String(100), unique=True, index=True)
    company_name = Column(String(200))
    niche        = Column(String(100))
    city         = Column(String(100))
    cnpj         = Column(String(20), nullable=True)
    partner_name = Column(String(200), nullable=True)
    email        = Column(String(200), nullable=True)
    pain_point   = Column(Text, nullable=True)
    status       = Column(String(20), default=LeadStatus.PENDING)
    created_at   = Column(DateTime, default=datetime.utcnow)
    emailed_at   = Column(DateTime, nullable=True)


def get_engine(db_url: str):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def get_session(engine) -> Session:
    return Session(engine)