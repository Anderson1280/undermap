"""
Mailer — Pilar 4 do Undermap.

Gera e envia e-mails altamente personalizados usando:
- Jinja2 para templates por nicho
- SMTP com TLS (Gmail, Outlook, etc.)
- Rate limiting com delay aleatório anti-spam
- Registro de envios para evitar duplicatas
"""

import asyncio
import logging
import random
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.niches import get_niche
from data.models import LeadEnriched, LeadStatus

logger = logging.getLogger(__name__)

# ── Templates de e-mail ───────────────────────────────────────────────────────
# Definidos inline como strings Jinja2 (evita dependência de arquivos externos)

TEXT_TEMPLATE = """\
Olá, {{ first_name }},

Vi que {{ company_name }} é muito bem avaliada {{ location_phrase }} — \
{% if rating %}nota {{ rating }} com {{ review_count }} avaliações no Google.{% else %}bastante conhecida na região.{% endif %}

Porém, notamos um gargalo comum em {{ niche_name }}: {{ pain_point }}.

Desenvolvemos um projeto focado exatamente nisso: {{ solution }}.

Posso te apresentar em 15 minutos? Sem custo e sem compromisso.

Att,
{{ sender_name }}
{{ sender_email }}

---
Para não receber mais e-mails, responda "remover" neste e-mail.
"""

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;padding:40px;border:1px solid #e8e8e8">
        <tr><td>
          <p style="font-size:15px;color:#333;line-height:1.7">
            Olá, <strong>{{ first_name }}</strong>,
          </p>
          <p style="font-size:15px;color:#333;line-height:1.7">
            Vi que <strong>{{ company_name }}</strong> é muito bem avaliada
            {{ location_phrase }}
            {% if rating %}
            — nota <strong>{{ rating }}</strong> com
            <strong>{{ review_count }}</strong> avaliações no Google.
            {% else %}
            e bastante conhecida na região.
            {% endif %}
          </p>
          <p style="font-size:15px;color:#333;line-height:1.7">
            Porém, notamos um gargalo comum em empresas como a sua:
          </p>
          <blockquote style="border-left:3px solid #e74c3c;margin:16px 0;
                             padding:12px 16px;background:#fff5f5;
                             color:#c0392b;font-size:14px;border-radius:0 6px 6px 0">
            {{ pain_point }}
          </blockquote>
          <p style="font-size:15px;color:#333;line-height:1.7">
            Desenvolvemos um projeto focado exatamente nisso:
            <strong>{{ solution }}</strong>.
          </p>
          <p style="margin:28px 0">
            <a href="mailto:{{ sender_email }}?subject=Quero saber mais — {{ company_name }}"
               style="background:#2ecc71;color:#fff;padding:12px 24px;
                      border-radius:6px;text-decoration:none;font-weight:bold;
                      font-size:15px">
              Quero conhecer →
            </a>
          </p>
          <p style="font-size:13px;color:#999;margin-top:32px">
            {{ sender_name }}<br>
            <a href="mailto:{{ sender_email }}" style="color:#999">{{ sender_email }}</a>
          </p>
          <p style="font-size:11px;color:#ccc;margin-top:16px;border-top:1px solid #eee;padding-top:16px">
            Para não receber mais e-mails, responda "remover" nesta mensagem.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


class MailerConfig:
    def __init__(
        self,
        smtp_host:    str,
        smtp_port:    int,
        smtp_user:    str,
        smtp_password: str,
        sender_name:  str,
        sender_email: str,
        delay_min:    float = 4.0,
        delay_max:    float = 12.0,
    ):
        self.smtp_host     = smtp_host
        self.smtp_port     = smtp_port
        self.smtp_user     = smtp_user
        self.smtp_password = smtp_password
        self.sender_name   = sender_name
        self.sender_email  = sender_email
        self.delay_min     = delay_min
        self.delay_max     = delay_max


class Mailer:
    def __init__(self, config: MailerConfig):
        self.cfg = config
        env = Environment(autoescape=select_autoescape(["html"]))
        self._text_tmpl = env.from_string(TEXT_TEMPLATE)
        self._html_tmpl = env.from_string(HTML_TEMPLATE)

    # ── Contexto do template ───────────────────────────────────────────────────

    def _build_context(self, lead: LeadEnriched) -> dict:
        """Monta as variáveis para preencher o template."""
        profile = get_niche(lead.niche)
        niche_name = profile.display_name if profile else lead.niche.title()

        # Nome do sócio (só primeiro nome para tom pessoal)
        partner_name = lead.partner.name if lead.partner else None
        first_name = partner_name.split()[0].title() if partner_name else "tudo bem"

        # Frase de localização
        location_phrase = f"em {lead.city}" if lead.city else "na sua região"

        return {
            "first_name":       first_name,
            "company_name":     lead.company_name,
            "location_phrase":  location_phrase,
            "niche_name":       niche_name,
            "rating":           lead.rating,
            "review_count":     lead.review_count,
            "pain_point":       lead.pain_point or "falta de presença digital",
            "solution":         lead.solution or "site profissional sob medida",
            "sender_name":      self.cfg.sender_name,
            "sender_email":     self.cfg.sender_email,
        }

    def _build_subject(self, lead: LeadEnriched) -> str:
        profile = get_niche(lead.niche)
        if profile:
            return profile.subject_line.format(company=lead.company_name)
        return f"{lead.company_name} — uma oportunidade que vale 15 minutos"

    # ── Envio ──────────────────────────────────────────────────────────────────

    def _send_smtp(self, to_email: str, subject: str, text: str, html: str) -> bool:
        """Envia via SMTP com TLS. Retorna True se bem-sucedido."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{self.cfg.sender_name} <{self.cfg.sender_email}>"
        msg["To"]      = to_email
        msg["Reply-To"] = self.cfg.sender_email

        msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.cfg.smtp_host, self.cfg.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.cfg.smtp_user, self.cfg.smtp_password)
                server.sendmail(self.cfg.sender_email, to_email, msg.as_string())
            return True
        except smtplib.SMTPException as e:
            logger.error(f"SMTP erro para {to_email}: {e}")
            return False

    async def send(self, lead: LeadEnriched) -> bool:
        """
        Envia e-mail para um lead.
        Retorna True se enviado com sucesso.
        """
        if not lead.email:
            logger.info(f"Sem e-mail para {lead.company_name} — pulando")
            return False

        ctx     = self._build_context(lead)
        subject = self._build_subject(lead)
        text    = self._text_tmpl.render(**ctx)
        html    = self._html_tmpl.render(**ctx)

        # Executa o envio SMTP (síncrono) em thread separada
        loop    = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, self._send_smtp, lead.email, subject, text, html
        )

        if success:
            lead.status = LeadStatus.EMAILED
            logger.info(f"✔ E-mail enviado: {lead.company_name} → {lead.email}")
        return success

    async def send_batch(
        self,
        leads: list[LeadEnriched],
        on_progress=None,
    ) -> tuple[int, int]:
        """
        Envia e-mails para uma lista de leads com delay entre cada envio.
        Retorna (enviados, falhas).
        """
        sent = failed = 0
        for i, lead in enumerate(leads):
            ok = await self.send(lead)
            if ok:
                sent += 1
            else:
                failed += 1

            if on_progress:
                on_progress(i + 1, len(leads), lead, ok)

            # Delay aleatório anti-spam (exceto no último)
            if i < len(leads) - 1:
                delay = random.uniform(self.cfg.delay_min, self.cfg.delay_max)
                logger.debug(f"Aguardando {delay:.1f}s antes do próximo envio...")
                await asyncio.sleep(delay)

        return sent, failed


def preview_email(lead: LeadEnriched, config: MailerConfig) -> str:
    """Retorna o texto do e-mail sem enviar — útil para dry-run."""
    mailer  = Mailer(config)
    ctx     = mailer._build_context(lead)
    subject = mailer._build_subject(lead)
    body    = mailer._text_tmpl.render(**ctx)
    return f"ASSUNTO: {subject}\n\n{body}"
