"""
Startup banner display for legacy and v3 modes.
"""

from datetime import datetime

from rich import box
from rich.panel import Panel
from rich.text import Text

from .core import LOGO, console


def show_banner(
    project: str,
    tool: str,
    model: str | None,
    plan_path: str,
    template_path: str,
    total: int,
    done: int,
    remaining: int,
    use_proxy: bool,
    work_dir: str,
):
    """Display the startup banner with full configuration info (legacy mode)."""
    console.print(Text(LOGO, style="bold cyan"), highlight=False)

    tool_str = f"[green]{tool}[/green]"
    if model:
        tool_str += f"  [dim]model:[/dim] [yellow]{model}[/yellow]"

    proxy_str = "[green]✓ enabled[/green]" if use_proxy else "[dim]✗ disabled[/dim]"

    info_lines = [
        f"[bold]Project[/bold]    │ [cyan]{project}[/cyan]",
        f"[bold]Tool[/bold]       │ {tool_str}",
        f"[bold]Plan[/bold]       │ {plan_path}",
        f"[bold]Template[/bold]   │ {template_path}",
        f"[bold]Work Dir[/bold]   │ {work_dir}",
        f"[bold]Tasks[/bold]      │ {total} total  ·  [green]{done} done[/green] "
        f" ·  [yellow]{remaining} remaining[/yellow]",
        f"[bold]Proxy[/bold]      │ {proxy_str}",
        f"[bold]Started[/bold]    │ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    panel = Panel(
        "\n".join(info_lines),
        title="[bold] 🚀 Auto Task Runner [/bold]",
        subtitle="[dim]CTRL+C to stop gracefully[/dim]",
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def show_banner_v3(
    project: str,
    task_set: str,
    tool: str,
    model: str | None,
    workspace: str,
    run_id: str,
    total: int,
    done: int,
    remaining: int,
    to_execute: int,
    use_proxy: bool,
):
    """Display the v3 startup banner."""
    console.print(Text(LOGO, style="bold cyan"), highlight=False)

    tool_str = f"[green]{tool}[/green]"
    if model:
        tool_str += f"  [dim]model:[/dim] [yellow]{model}[/yellow]"

    proxy_str = "[green]✓ enabled[/green]" if use_proxy else "[dim]✗ disabled[/dim]"

    info_lines = [
        f"[bold]Project[/bold]    │ [cyan]{project}[/cyan]",
        f"[bold]Task Set[/bold]   │ [magenta]{task_set}[/magenta]",
        f"[bold]Tool[/bold]       │ {tool_str}",
        f"[bold]Workspace[/bold]  │ {workspace}",
        f"[bold]Run ID[/bold]     │ [dim]{run_id}[/dim]",
        f"[bold]Tasks[/bold]      │ {total} total  ·  [green]{done} done[/green] "
        f" ·  [yellow]{remaining} remaining[/yellow]  ·  [cyan]{to_execute} to execute[/cyan]",
        f"[bold]Proxy[/bold]      │ {proxy_str}",
        f"[bold]Started[/bold]    │ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    panel = Panel(
        "\n".join(info_lines),
        title="[bold] 🚀 Auto Task Runner v3.0 [/bold]",
        subtitle="[dim]CTRL+C to stop gracefully[/dim]",
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )
    console.print(panel)
    console.print()
