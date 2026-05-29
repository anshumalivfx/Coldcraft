"""
Cold Outreach Agent — Week 1 MVP
Usage: python main.py [--csv leads.csv] [--your-name "Your Name"] [--your-product "..."]

Reads leads from CSV, scrapes each company site, extracts a hook,
writes a personalized cold email with Claude, and prints results.
"""

import csv
import os
import sys
import argparse
import time
import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text
from rich.rule import Rule

from src.agent.scraper import scrape_website, format_context_for_claude
from src.agent.writer import extract_hook, write_email

load_dotenv()
console = Console()


def load_leads(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def score_color(score) -> str:
    try:
        s = float(score)
        if s >= 8:
            return "green"
        if s >= 6:
            return "yellow"
        return "red"
    except (TypeError, ValueError):
        return "white"


def print_result(lead: dict, hook: dict, email: dict, idx: int, total: int):
    console.print()
    console.print(Rule(f"[bold]Lead {idx}/{total}: {lead['name']} · {lead['role']} @ {lead['company']}[/bold]"))

    # Hook
    hook_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    hook_table.add_column("key", style="dim", width=18)
    hook_table.add_column("val")
    hook_table.add_row("Hook", hook.get("hook", "—"))
    hook_table.add_row("Hook type", hook.get("hook_type", "—"))
    hook_table.add_row(
        "Hook confidence",
        Text(str(hook.get("confidence", "?")), style=score_color(hook.get("confidence")))
    )
    console.print(hook_table)

    # Email
    score = email.get("personalization_score", "?")
    retried = email.get("retried", False)
    subject = email.get("subject", "")
    body = email.get("body", "")

    score_text = Text(f"{score}/10", style=score_color(score))
    if retried:
        score_text.append(" (auto-retried)", style="dim")

    email_panel = Panel(
        f"[bold]Subject:[/bold] {subject}\n\n{body}",
        title=f"[bold]Personalization score: [/bold]{score_text}",
        border_style="bright_black",
        padding=(1, 2),
    )
    console.print(email_panel)


def print_summary(results: list[dict], elapsed: float):
    console.print()
    console.print(Rule("[bold]Run summary[/bold]"))

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    table.add_column("Name", width=18)
    table.add_column("Company", width=16)
    table.add_column("Hook type", width=16)
    table.add_column("Score", justify="center", width=8)
    table.add_column("Retried", justify="center", width=8)

    scores = []
    for r in results:
        s = r["email"].get("personalization_score", 0)
        scores.append(float(s) if s else 0)
        table.add_row(
            r["lead"]["name"],
            r["lead"]["company"],
            r["hook"].get("hook_type", "—"),
            Text(str(s), style=score_color(s)),
            "yes" if r["email"].get("retried") else "no",
        )

    console.print(table)
    avg = sum(scores) / len(scores) if scores else 0
    console.print(f"\n  Leads processed : [bold]{len(results)}[/bold]")
    console.print(f"  Avg personalization score : [bold]{avg:.1f}/10[/bold]")
    console.print(f"  Total time : [bold]{elapsed:.1f}s[/bold]")
    console.print(f"  Approx cost : [bold]~${len(results) * 0.006:.3f}[/bold] (est. at $0.006/lead)\n")


def main():
    parser = argparse.ArgumentParser(description="AI Cold Outreach Agent — Week 1 MVP")
    parser.add_argument("--csv", default="leads.csv", help="Path to leads CSV")
    parser.add_argument("--your-name", default="Anshi", help="Your name for email sign-off")
    parser.add_argument("--your-product", default="Humanoid — AI marketing automation for SaaS teams", help="One-line product description")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip website scraping (faster, less personalized)")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Add it to .env or environment.[/red]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    try:
        leads = load_leads(args.csv)
    except FileNotFoundError:
        console.print(f"[red]Error: {args.csv} not found.[/red]")
        sys.exit(1)

    console.print()
    console.print(Panel(
        f"[bold]AI Cold Outreach Agent[/bold]\n"
        f"Leads: [cyan]{len(leads)}[/cyan]  |  "
        f"Sender: [cyan]{args.your_name}[/cyan]  |  "
        f"Product: [cyan]{args.your_product}[/cyan]",
        border_style="cyan",
        padding=(0, 2),
    ))

    start = time.time()
    results = []

    for idx, lead in enumerate(leads, 1):
        console.print(f"\n[dim]→ Processing {lead['name']} ({idx}/{len(leads)})...[/dim]")

        # Step 1: scrape
        if args.skip_scrape:
            context = f"PROSPECT: {lead['name']}\nROLE: {lead['role']} at {lead['company']}\nNo website scraped."
        else:
            console.print(f"  [dim]Scraping {lead['website']}...[/dim]")
            scraped = scrape_website(lead["website"])
            context = format_context_for_claude(lead, scraped)

        # Step 2: extract hook
        console.print("  [dim]Extracting hook...[/dim]")
        hook = extract_hook(client, context)

        # Step 3: write email
        console.print("  [dim]Writing email...[/dim]")
        email = write_email(
            client,
            lead,
            hook,
            your_name=args.your_name,
            your_product=args.your_product,
        )

        results.append({"lead": lead, "hook": hook, "email": email})
        print_result(lead, hook, email, idx, len(leads))

    elapsed = time.time() - start
    print_summary(results, elapsed)


if __name__ == "__main__":
    main()
