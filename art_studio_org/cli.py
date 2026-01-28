from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.table import Table

from art_studio_org.db import DB, default_db_path

app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()


# ----------------------------
# Helpers
# ----------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def header():
    console.print(Panel.fit("[bold]Studio Inventory CLI[/bold]\nVersion 1.0", border_style="cyan"))


def pause():
    console.print()
    input("Press Enter to continue...")


def get_db(db_path: Optional[Path] = None) -> DB:
    return DB(path=db_path or default_db_path())


def safe_str(v) -> str:
    return "" if v is None else str(v)


def shorten(s: str, n: int = 54) -> str:
    s = safe_str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


# ----------------------------
# Menu-first entry
# ----------------------------
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Menu-first launcher. If you later pass subcommands, it won't show the menu.
    """
    if ctx.invoked_subcommand is None:
        run_menu()


def run_menu():
    while True:
        console.clear()
        header()

        menu = Table(show_header=False, box=None)
        menu.add_row("1.", "[bold]Ingest[/bold] receipts / packing lists [dim](hook in next)[/dim]")
        menu.add_row("2.", "[bold]Export[/bold] data (CSV / reports) [dim](hook in next)[/dim]")
        menu.add_row("3.", "[bold]Inventory[/bold] browse / search / receive / remove")
        menu.add_row("4.", "[bold]Vendors[/bold] enrich (DigiKey / McMaster) [dim](coming soon)[/dim]")
        menu.add_row("5.", "[bold]Labels[/bold] generate PDFs [dim](coming soon)[/dim]")
        menu.add_row("6.", "DB diagnostics")
        menu.add_row("0.", "Quit")
        console.print(menu)

        choice = Prompt.ask("\nChoose", choices=["1", "2", "3", "4", "5", "6", "0"], default="3")

        if choice == "1":
            menu_ingest()
        elif choice == "2":
            menu_export()
        elif choice == "3":
            menu_inventory()
        elif choice == "4":
            menu_vendors()
        elif choice == "5":
            menu_labels()
        elif choice == "6":
            menu_db_diagnostics()
        elif choice == "0":
            console.print("\nBye.\n")
            return


# ----------------------------
# Stubs (wire to your existing logic later)
# ----------------------------
def menu_ingest():
    console.clear()
    header()
    console.print("[bold]Ingest[/bold]\n")
    console.print("TODO: call your existing ingest flow (ingest_all.py / main.py).")
    pause()


def menu_export():
    console.clear()
    header()
    console.print("[bold]Export[/bold]\n")
    console.print("TODO: export inventory_view / orders / line_items as CSVs.")
    pause()


def menu_vendors():
    console.clear()
    header()
    console.print("[bold]Vendors[/bold]\n")
    console.print("Next: DigiKey OAuth + product/media enrichment, then McMaster cert-based API enrichment.")
    pause()


def menu_labels():
    console.clear()
    header()
    console.print("[bold]Labels[/bold]\n")
    console.print("Paused for now. Once vendor enrichment is in, labels become DB-driven.")
    pause()


# ----------------------------
# Inventory (REAL)
# ----------------------------
def menu_inventory():
    db = get_db()
    if not db.path.exists():
        console.clear()
        header()
        console.print(f"[red]DB not found:[/red] {db.path}")
        pause()
        return

    while True:
        console.clear()
        header()
        console.print("[bold]Inventory[/bold] (from [cyan]inventory_view[/cyan])\n")

        menu = Table(show_header=False, box=None)
        menu.add_row("1.", "List (top 30)")
        menu.add_row("2.", "Search")
        menu.add_row("3.", "Show details (by part_key)")
        menu.add_row("4.", "Receive stock (manual)")
        menu.add_row("5.", "Remove stock (log usage)")
        menu.add_row("6.", "Edit label fields (line1/line2/short/QR/url)")
        menu.add_row("0.", "Back")
        console.print(menu)

        choice = Prompt.ask("\nChoose", choices=["1", "2", "3", "4", "5", "6", "0"], default="2")
        if choice == "0":
            return
        if choice == "1":
            inv_list(db)
        elif choice == "2":
            inv_search(db)
        elif choice == "3":
            inv_show(db)
        elif choice == "4":
            inv_receive(db)
        elif choice == "5":
            inv_remove(db)
        elif choice == "6":
            inv_edit_labels(db)


def inv_list(db: DB):
    console.clear()
    header()
    console.print("[bold]Inventory list[/bold]\n")

    rows = db.rows("""
        SELECT part_key, vendor, sku, label_short, on_hand, avg_unit_cost, last_invoice
        FROM inventory_view
        ORDER BY last_invoice DESC
        LIMIT 30
    """)

    t = Table(show_header=True, header_style="bold magenta")
    t.add_column("part_key", style="dim")
    t.add_column("vendor", width=10)
    t.add_column("sku", width=14)
    t.add_column("label_short")
    t.add_column("on_hand", justify="right", width=8)
    t.add_column("avg_cost", justify="right", width=10)

    for r in rows:
        t.add_row(
            safe_str(r["part_key"]),
            safe_str(r["vendor"]),
            safe_str(r["sku"]),
            shorten(r["label_short"], 56),
            safe_str(r["on_hand"]),
            safe_str(r["avg_unit_cost"]),
        )
    console.print(t)
    pause()


def inv_search(db: DB):
    console.clear()
    header()
    console.print("[bold]Search inventory[/bold]\n")

    term = Prompt.ask("Search (part_key / sku / description / label_short / vendor)", default="").strip()
    if not term:
        return

    like = f"%{term}%"
    rows = db.rows("""
        SELECT part_key, vendor, sku, label_short, on_hand
        FROM inventory_view
        WHERE part_key LIKE ? COLLATE NOCASE
           OR sku LIKE ? COLLATE NOCASE
           OR vendor LIKE ? COLLATE NOCASE
           OR description LIKE ? COLLATE NOCASE
           OR label_short LIKE ? COLLATE NOCASE
        ORDER BY on_hand DESC, vendor, sku
        LIMIT 60
    """, [like, like, like, like, like])

    t = Table(show_header=True, header_style="bold magenta")
    t.add_column("part_key", style="dim")
    t.add_column("vendor", width=10)
    t.add_column("sku", width=14)
    t.add_column("label_short")
    t.add_column("on_hand", justify="right", width=8)

    for r in rows:
        t.add_row(
            safe_str(r["part_key"]),
            safe_str(r["vendor"]),
            safe_str(r["sku"]),
            shorten(r["label_short"], 60),
            safe_str(r["on_hand"]),
        )

    console.print(t)
    pause()


def inv_show(db: DB):
    console.clear()
    header()
    console.print("[bold]Show inventory item[/bold]\n")

    part_key = Prompt.ask("part_key (e.g. mcmaster:1234K56)").strip()
    if not part_key:
        return

    rows = db.rows("SELECT * FROM inventory_view WHERE part_key = ?", [part_key])
    if not rows:
        console.print("[yellow]No item found in inventory_view.[/yellow]")
        pause()
        return

    r = rows[0]
    t = Table(show_header=False, box=None)
    for k in r.keys():
        t.add_row(f"[dim]{k}[/dim]", safe_str(r[k]))
    console.print(t)

    console.print("\n[bold]Recent removals[/bold]")
    rem = db.rows("""
        SELECT ts_utc, qty_removed, project, note
        FROM parts_removed
        WHERE part_key = ?
        ORDER BY ts_utc DESC
        LIMIT 10
    """, [part_key])

    if not rem:
        console.print("[dim](none)[/dim]")
    else:
        rt = Table(show_header=True, header_style="bold cyan")
        rt.add_column("ts_utc", style="dim")
        rt.add_column("qty_removed", justify="right", width=10)
        rt.add_column("project", width=18)
        rt.add_column("note")
        for rr in rem:
            rt.add_row(safe_str(rr["ts_utc"]), safe_str(rr["qty_removed"]), shorten(rr["project"], 18), shorten(rr["note"], 60))
        console.print(rt)

    pause()


def inv_remove(db: DB):
    console.clear()
    header()
    console.print("[bold]Remove stock[/bold] (logs to parts_removed)\n")

    part_key = Prompt.ask("part_key").strip()
    if not part_key:
        return

    # confirm exists
    exists = db.scalar("SELECT 1 FROM parts_received WHERE part_key = ? LIMIT 1", [part_key])
    if not exists:
        console.print("[red]part_key not found in parts_received.[/red]")
        pause()
        return

    qty = FloatPrompt.ask("Qty removed", default=1.0)
    if qty <= 0:
        console.print("[yellow]Qty must be > 0[/yellow]")
        pause()
        return

    project = Prompt.ask("Project (optional)", default="").strip()
    note = Prompt.ask("Note (optional)", default="").strip()

    ts = utc_now_iso()
    removal_uid = str(uuid4())

    db.execute("""
        INSERT INTO parts_removed (removal_uid, part_key, qty_removed, ts_utc, project, note, updated_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [removal_uid, part_key, qty, ts, project, note, ts])

    console.print("[green]Logged removal.[/green] inventory_view on_hand will update automatically.")
    pause()


def inv_receive(db: DB):
    console.clear()
    header()
    console.print("[bold]Receive stock (manual)[/bold] (upserts parts_received)\n")

    part_key = Prompt.ask("part_key (recommended format: vendor:sku)").strip()
    if not part_key:
        return

    qty = FloatPrompt.ask("Qty received", default=1.0)
    if qty <= 0:
        console.print("[yellow]Qty must be > 0[/yellow]")
        pause()
        return

    unit_cost = Prompt.ask("Unit cost (optional)", default="").strip()
    try:
        unit_cost_f = float(unit_cost) if unit_cost else 0.0
    except ValueError:
        unit_cost_f = 0.0

    added_spend = qty * unit_cost_f

    # Only ask metadata if new part_key
    exists = db.scalar("SELECT 1 FROM parts_received WHERE part_key = ? LIMIT 1", [part_key])
    ts = utc_now_iso()

    if exists:
        # Increment units_received and (optionally) total_spend; recompute avg_unit_cost if we have spend
        db.execute("""
            UPDATE parts_received
            SET
              units_received = COALESCE(units_received, 0) + ?,
              total_spend = COALESCE(total_spend, 0) + ?,
              avg_unit_cost =
                CASE
                  WHEN (COALESCE(units_received, 0) + ?) > 0 AND (COALESCE(total_spend, 0) + ?) > 0
                  THEN (COALESCE(total_spend, 0) + ?) / (COALESCE(units_received, 0) + ?)
                  ELSE avg_unit_cost
                END,
              updated_utc = ?
            WHERE part_key = ?
        """, [qty, added_spend, qty, added_spend, added_spend, qty, ts, part_key])

        console.print("[green]Updated parts_received.[/green]")
        pause()
        return

    console.print("\n[bold]New part_key[/bold] — enter basic metadata (you can refine later).")
    vendor = Prompt.ask("vendor", default=part_key.split(":", 1)[0] if ":" in part_key else "")
    sku = Prompt.ask("sku", default=part_key.split(":", 1)[1] if ":" in part_key else "")
    description = Prompt.ask("description", default="")
    label_short = Prompt.ask("label_short", default=description or part_key)

    label_line1 = Prompt.ask("label_line1 (optional)", default="")
    label_line2 = Prompt.ask("label_line2 (optional)", default="")
    purchase_url = Prompt.ask("purchase_url (optional)", default="")
    airtable_url = Prompt.ask("airtable_url (optional)", default="")
    label_qr_url = Prompt.ask("label_qr_url (optional)", default="")
    label_qr_text = Prompt.ask("label_qr_text (optional)", default="")

    desc_clean = description.strip()

    avg_unit_cost = (added_spend / qty) if (qty > 0 and added_spend > 0) else 0.0

    db.execute("""
        INSERT INTO parts_received (
            part_key, vendor, sku, description, desc_clean,
            label_line1, label_line2, label_short,
            purchase_url, airtable_url, label_qr_url, label_qr_text,
            units_received, total_spend, last_invoice, avg_unit_cost, updated_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        part_key, vendor, sku, description, desc_clean,
        label_line1, label_line2, label_short,
        purchase_url, airtable_url, label_qr_url, label_qr_text,
        qty, added_spend, None, avg_unit_cost, ts
    ])

    console.print("[green]Inserted new part into parts_received.[/green]")
    pause()


def inv_edit_labels(db: DB):
    console.clear()
    header()
    console.print("[bold]Edit label fields[/bold] (updates parts_received)\n")

    part_key = Prompt.ask("part_key").strip()
    if not part_key:
        return

    rows = db.rows("SELECT * FROM parts_received WHERE part_key = ?", [part_key])
    if not rows:
        console.print("[yellow]No row found in parts_received for that part_key.[/yellow]")
        pause()
        return

    r = rows[0]
    console.print("[dim]Leave blank to keep current values.[/dim]\n")

    def ask_keep(field: str) -> Optional[str]:
        cur = safe_str(r[field])
        val = Prompt.ask(f"{field}", default=cur).strip()
        return val

    label_line1 = ask_keep("label_line1")
    label_line2 = ask_keep("label_line2")
    label_short = ask_keep("label_short")
    purchase_url = ask_keep("purchase_url")
    airtable_url = ask_keep("airtable_url")
    label_qr_url = ask_keep("label_qr_url")
    label_qr_text = ask_keep("label_qr_text")

    ts = utc_now_iso()
    db.execute("""
        UPDATE parts_received
        SET
          label_line1 = ?,
          label_line2 = ?,
          label_short = ?,
          purchase_url = ?,
          airtable_url = ?,
          label_qr_url = ?,
          label_qr_text = ?,
          updated_utc = ?
        WHERE part_key = ?
    """, [label_line1, label_line2, label_short, purchase_url, airtable_url, label_qr_url, label_qr_text, ts, part_key])

    console.print("[green]Updated label fields.[/green]")
    pause()


# ----------------------------
# DB diagnostics (REAL)
# ----------------------------
def menu_db_diagnostics():
    db_path = default_db_path()

    console.clear()
    header()
    console.print("[bold]DB diagnostics[/bold]\n")
    console.print(f"DB path: [cyan]{db_path}[/cyan]")
    console.print(f"DB exists: {'✅' if db_path.exists() else '❌'}\n")

    if not db_path.exists():
        pause()
        return

    db = get_db()

    tables = db.rows("""
        SELECT name, type
        FROM sqlite_master
        WHERE type IN ('table','view')
          AND name NOT LIKE 'sqlite_%'
        ORDER BY type, name
    """)

    t = Table(show_header=True, header_style="bold magenta")
    t.add_column("type", width=6)
    t.add_column("name")
    t.add_column("rows", justify="right", width=8)

    for row in tables:
        name = row["name"]
        typ = row["type"]
        count = ""
        if typ == "table":
            try:
                count = str(db.scalar(f"SELECT COUNT(*) FROM {name}") or 0)
            except Exception:
                count = "?"
        t.add_row(typ, name, count)

    console.print(t)

    if Confirm.ask("\nShow schema for a table/view?", default=False):
        name = Prompt.ask("Name (e.g. parts_received)", default="inventory_view").strip()
        if name:
            info = db.rows(f"PRAGMA table_info({name})")
            st = Table(title=f"Schema: {name}", show_header=True, header_style="bold cyan")
            st.add_column("cid", justify="right", width=4)
            st.add_column("name")
            st.add_column("type", width=10)
            st.add_column("pk", justify="right", width=3)
            for c in info:
                st.add_row(str(c["cid"]), safe_str(c["name"]), safe_str(c["type"]), str(c["pk"]))
            console.print(st)

    pause()


# ----------------------------
# Future subcommands (placeholders)
# ----------------------------
@app.command()
def inventory():
    """Non-interactive entrypoint later: inventory ..."""
    console.print("Use the menu for now. (Subcommands coming soon.)")


@app.command()
def ingest():
    console.print("Use the menu for now. (Subcommands coming soon.)")


@app.command()
def export():
    console.print("Use the menu for now. (Subcommands coming soon.)")


@app.command()
def vendors():
    console.print("Use the menu for now. (Subcommands coming soon.)")


@app.command()
def labels():
    console.print("Use the menu for now. (Subcommands coming soon.)")


if __name__ == "__main__":
    app()
