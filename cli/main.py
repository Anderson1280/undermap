"""
Undermap CLI — Interface de terminal.

Comandos disponíveis:
  undermap scan      — Varredura + enriquecimento + envio
  undermap nichos    — Lista nichos disponíveis
  undermap preview   — Visualiza e-mail antes de enviar (dry-run)
  undermap leads     — Lista leads salvos localmente
  undermap version   — Versão atual
"""

import asyncio
import logging
import os
import sys
from typing import Optional

import typer
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

# Carrega .env antes de qualquer import do projeto
load_dotenv()

from core.enricher import Enricher
from core.mailer import MailerConfig, Mailer, preview_email
from core.niches import NICHES, list_niches
from core.scanner import Scanner, mock_leads
from data.models import LeadEnriched, LeadRecord, LeadStatus, get_engine, get_session

# ── Setup ──────────────────────────────────────────────────────────────────────

console = Console()
app     = typer.Typer(
    name="undermap",
    help="[bold green]Undermap[/] — Prospecção B2B automatizada para devs web.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
logging.basicConfig(level=logging.WARNING)  # silencia libs verbose no terminal


# ── Banner ─────────────────────────────────────────────────────────────────────

BANNER = """[bold green]
  _   _           _                                
 | | | |_ __   __| | ___ _ __ _ __ ___   __ _ _ __  
 | | | | '_ \\ / _` |/ _ \\ '__| '_ ` _ \\ / _` | '_ \\ 
 | |_| | | | | (_| |  __/ |  | | | | | | (_| | |_) |
  \\___/|_| |_|\\__,_|\\___|_|  |_| |_| |_|\\__,_| .__/ 
                                               |_|   
[/bold green][dim]Prospecção B2B automatizada — v0.1.0[/dim]
"""


def _check_env(*keys: str):
    """Verifica se variáveis de ambiente obrigatórias estão definidas."""
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        console.print(f"[red]✗ Variáveis de ambiente não configuradas: {', '.join(missing)}[/]")
        console.print("[dim]Copie .env.example para .env e preencha os valores.[/]")
        raise typer.Exit(1)


def _get_mailer_config() -> MailerConfig:
    return MailerConfig(
        smtp_host     = os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port     = int(os.getenv("SMTP_PORT", "587")),
        smtp_user     = os.getenv("SMTP_USER", ""),
        smtp_password = os.getenv("SMTP_PASSWORD", ""),
        sender_name   = os.getenv("SENDER_NAME", ""),
        sender_email  = os.getenv("SENDER_EMAIL", ""),
    )


def _persist_leads(leads: list[LeadEnriched], session):
    """Salva leads no banco local, ignorando duplicatas por place_id."""
    for lead in leads:
        exists = session.query(LeadRecord).filter_by(place_id=lead.place_id).first()
        if not exists:
            rec = LeadRecord(
                place_id     = lead.place_id,
                company_name = lead.company_name,
                niche        = lead.niche,
                city         = lead.city,
                cnpj         = lead.cnpj,
                partner_name = lead.partner.name if lead.partner else None,
                email        = lead.email,
                pain_point   = lead.pain_point,
                status       = lead.status,
            )
            session.add(rec)
    session.commit()


# ── Comando: scan ──────────────────────────────────────────────────────────────

@app.command()
def scan(
    nicho:  str = typer.Argument(..., help="Nicho a prospectar. Ex: marmoraria"),
    regiao: str = typer.Argument(..., help="Região. Ex: 'Zona Leste São Paulo'"),
    limite: int = typer.Option(30, "--limite", "-l", help="Máx. de leads a buscar"),
    enviar: bool = typer.Option(False, "--enviar", "-e", help="Enviar e-mails ao final"),
    mock:   bool = typer.Option(False, "--mock", "-m", help="Usar dados fictícios (sem API)"),
    radius: int  = typer.Option(5000, "--raio", "-r", help="Raio de busca em metros"),
):
    """
    [bold]Varre o mercado[/], enriquece leads e (opcionalmente) envia cold emails.

    [dim]Exemplos:[/]
      undermap scan marmoraria "Zona Leste SP"
      undermap scan restaurante "Centro Campinas" --limite 50 --enviar
      undermap scan clinica "Curitiba" --mock
    """
    console.print(BANNER)

    # Valida nicho
    if nicho.lower() not in NICHES and not mock:
        console.print(f"[red]Nicho '{nicho}' não encontrado.[/] Use [bold]undermap nichos[/] para ver a lista.")
        raise typer.Exit(1)

    # Verifica credenciais necessárias
    if not mock:
        _check_env("GOOGLE_API_KEY")
    if enviar:
        _check_env("SMTP_USER", "SMTP_PASSWORD", "SENDER_NAME", "SENDER_EMAIL")

    engine  = get_engine(os.getenv("DATABASE_URL", "sqlite:///undermap.db"))
    session = get_session(engine)

    # ── Etapa 1: Scanner ────────────────────────────────────────────────────────
    console.rule(f"[bold green]Etapa 1[/] · Varredura geolocalizada — {nicho.upper()} em {regiao}")

    raw_leads = []

    async def run_scan():
        if mock:
            console.print("[yellow]⚡ Modo mock ativado — sem chamadas à API[/]")
            return mock_leads(nicho, regiao, count=min(limite, 10))
        scanner = Scanner(api_key=os.getenv("GOOGLE_API_KEY"), radius_m=radius)
        try:
            return await scanner.scan(nicho, regiao, max_results=limite)
        finally:
            await scanner.close()

    with console.status("[bold green]Varrendo Google Maps...", spinner="dots"):
        raw_leads = asyncio.run(run_scan())

    if not raw_leads:
        console.print("[yellow]Nenhum lead encontrado. Tente outro nicho ou região.[/]")
        raise typer.Exit(0)

    console.print(f"[green]✔[/] {len(raw_leads)} empresas sem site encontradas\n")

    # ── Etapa 2: Enriquecimento ─────────────────────────────────────────────────
    console.rule("[bold green]Etapa 2[/] · Enriquecimento de dados (Receita Federal)")

    enriched_leads: list[LeadEnriched] = []
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    table.add_column("Empresa",       style="white",       max_width=30)
    table.add_column("⭐ Nota",        style="yellow",      justify="center", max_width=8)
    table.add_column("Porte",         style="cyan",        justify="center", max_width=8)
    table.add_column("Sócio",         style="green",       max_width=22)
    table.add_column("E-mail",        style="blue",        max_width=30)
    table.add_column("Status",        justify="center",    max_width=12)

    async def run_enrich():
        enricher = Enricher()
        results  = []

        def on_progress(current, total, lead, enriched):
            rating_str = f"{lead.rating}" if lead.rating else "—"
            if enriched:
                porte  = enriched.company_size or "—"
                socio  = enriched.partner.name.split()[0] if enriched.partner else "—"
                email  = enriched.email or "[dim]não encontrado[/]"
                status = "[green]✔ qualificado[/]"
                table.add_row(lead.name[:28], rating_str, porte, socio, email, status)
                results.append(enriched)
            else:
                table.add_row(lead.name[:28], rating_str, "—", "—", "—", "[red]✗ inelegível[/]")

        with Live(table, console=console, refresh_per_second=4):
            await enricher.enrich_batch(raw_leads, on_progress=on_progress)
        await enricher.close()
        return results

    enriched_leads = asyncio.run(run_enrich())
    _persist_leads(enriched_leads, session)

    console.print(f"\n[green]✔[/] {len(enriched_leads)} leads qualificados — salvos localmente\n")

    # ── Etapa 3: Envio de e-mails ───────────────────────────────────────────────
    if not enviar:
        console.print(
            Panel(
                f"[bold]Pronto![/] {len(enriched_leads)} leads qualificados.\n"
                f"Para enviar os e-mails, rode novamente com [bold green]--enviar[/]:\n\n"
                f"  [dim]undermap scan {nicho} \"{regiao}\" --enviar[/]",
                title="Próximo passo",
                border_style="green",
            )
        )
        raise typer.Exit(0)

    leads_with_email = [l for l in enriched_leads if l.email]
    if not leads_with_email:
        console.print("[yellow]Nenhum lead com e-mail encontrado nesta varredura.[/]")
        raise typer.Exit(0)

    console.rule(f"[bold green]Etapa 3[/] · Cold mailing — {len(leads_with_email)} e-mails")
    mail_cfg = _get_mailer_config()
    mailer   = Mailer(mail_cfg)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    )

    async def run_mail():
        sent = failed = 0

        def on_progress(current, total, lead, ok):
            nonlocal sent, failed
            symbol = "[green]✔[/]" if ok else "[red]✗[/]"
            task_desc = f"{symbol} {lead.company_name[:25]}"
            progress.update(mail_task, advance=1, description=task_desc)
            if ok:
                sent += 1
            else:
                failed += 1

        with progress:
            mail_task = progress.add_task("Enviando...", total=len(leads_with_email))
            await mailer.send_batch(leads_with_email, on_progress=on_progress)
        return sent, failed

    sent, failed = asyncio.run(run_mail())

    console.print(
        Panel(
            f"[bold green]✔ {sent} e-mails enviados[/]"
            + (f"   [red]✗ {failed} falhas[/]" if failed else ""),
            title="[bold]Campanha finalizada",
            border_style="green",
        )
    )


# ── Comando: nichos ────────────────────────────────────────────────────────────

@app.command()
def nichos():
    """Lista todos os [bold]nichos disponíveis[/] e suas dores mapeadas."""
    console.print(BANNER)
    table = Table(title="Nichos disponíveis", box=box.ROUNDED, header_style="bold green")
    table.add_column("Chave",        style="bold cyan",  max_width=16)
    table.add_column("Nome",         style="white",      max_width=30)
    table.add_column("Gargalo",      style="dim",        max_width=50)

    for key, profile in NICHES.items():
        table.add_row(key, profile.display_name, profile.pain_point[:80] + "...")

    console.print(table)
    console.print("\n[dim]Uso: [bold]undermap scan <nicho> \"<região>\"[/][/]")


# ── Comando: preview ───────────────────────────────────────────────────────────

@app.command()
def preview(
    nicho:   str = typer.Argument(..., help="Nicho para gerar preview"),
    empresa: str = typer.Option("Marmoraria Zago",      "--empresa", help="Nome da empresa"),
    cidade:  str = typer.Option("São Paulo",            "--cidade",  help="Cidade"),
    socio:   str = typer.Option("Roberto Zago",         "--socio",   help="Nome do sócio"),
    email:   str = typer.Option("roberto@empresa.com",  "--email",   help="E-mail destino"),
):
    """
    Gera um [bold]preview do e-mail[/] sem enviar nada — perfeito para ajustar o texto.
    """
    _check_env("SENDER_NAME", "SENDER_EMAIL")

    from data.models import PartnerInfo
    lead = LeadEnriched(
        place_id     = "preview",
        company_name = empresa,
        address      = f"Rua Exemplo, 100 — {cidade}",
        city         = cidade,
        niche        = nicho,
        partner      = PartnerInfo(name=socio, qualifier="Sócio"),
        rating       = 4.8,
        review_count = 127,
        pain_point   = NICHES.get(nicho, list(NICHES.values())[0]).pain_point,
        solution     = NICHES.get(nicho, list(NICHES.values())[0]).solution,
        email        = email,
        status       = LeadStatus.QUALIFIED,
    )

    mail_cfg = _get_mailer_config()
    text     = preview_email(lead, mail_cfg)
    console.print(Panel(text, title=f"[bold green]Preview — {empresa}[/]", border_style="green"))


# ── Comando: leads ─────────────────────────────────────────────────────────────

@app.command()
def leads(
    status: Optional[str] = typer.Option(None, "--status", help="Filtrar por status: qualified, emailed"),
    limite: int = typer.Option(20, "--limite", help="Quantidade máxima a exibir"),
):
    """Lista os [bold]leads salvos localmente[/] no banco de dados."""
    engine  = get_engine(os.getenv("DATABASE_URL", "sqlite:///undermap.db"))
    session = get_session(engine)

    query = session.query(LeadRecord)
    if status:
        query = query.filter(LeadRecord.status == status)
    records = query.order_by(LeadRecord.created_at.desc()).limit(limite).all()

    if not records:
        console.print("[yellow]Nenhum lead encontrado. Rode [bold]undermap scan[/] primeiro.[/]")
        raise typer.Exit(0)

    table = Table(box=box.SIMPLE, header_style="bold dim")
    table.add_column("Empresa",  max_width=28)
    table.add_column("Nicho",    max_width=14)
    table.add_column("Cidade",   max_width=18)
    table.add_column("Sócio",    max_width=18)
    table.add_column("E-mail",   max_width=28)
    table.add_column("Status",   justify="center")

    status_styles = {
        "qualified": "[green]qualificado[/]",
        "emailed":   "[blue]enviado[/]",
        "rejected":  "[red]rejeitado[/]",
        "pending":   "[dim]pendente[/]",
    }

    for r in records:
        table.add_row(
            r.company_name[:26],
            r.niche,
            r.city[:16],
            (r.partner_name or "—").split()[0],
            r.email or "[dim]—[/]",
            status_styles.get(r.status, r.status),
        )

    console.print(table)
    console.print(f"\n[dim]{len(records)} leads exibidos[/]")


# ── Comando: version ───────────────────────────────────────────────────────────

@app.command()
def version():
    """Exibe a [bold]versão[/] do Undermap."""
    console.print("[bold green]Undermap[/] v0.1.0")


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
