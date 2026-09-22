"""CLI for Continuity — works in any terminal, any IDE, any workflow."""

from __future__ import annotations

import sys
import os
import subprocess
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from continuity import __version__
from continuity.core.memory import MemoryEngine
from continuity.core.models import MemoryType, Role
from continuity.storage.sqlite import Storage

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="continuity")
def cli() -> None:
    """Continuity — AI conversation memory. Never lose the thread."""
    pass


# ── INIT ──────────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=None, help="Database path (default: ~/.continuity/continuity.db)")
def init(db: str | None) -> None:
    """Initialize continuity storage."""
    engine = MemoryEngine(Storage(db))
    stats = engine.storage.get_stats()
    console.print(Panel(
        f"[green]Initialized![/green]\n\n"
        f"Database: {stats['db_path']}\n"
        f"Size: {stats['db_size_bytes']} bytes\n\n"
        f"Next steps:\n"
        f"  continuity memory add \"Your first memory\"\n"
        f"  continuity session new -p openai -m gpt-4o\n"
        f"  continuity inject \"What am I working on?\"",
        title="Continuity",
        border_style="green",
    ))


# ── INJECT (for web UIs: ChatGPT, Claude web, Gemini web) ─────────

@cli.command()
@click.argument("message", required=False)
@click.option("--session", "-s", default=None, help="Session ID to continue")
@click.option("--max-tokens", "-t", default=1500, help="Max context tokens")
@click.option("--copy", "-c", is_flag=True, help="Copy to clipboard")
@click.option("--format", "-f", "fmt", default="text", type=click.Choice(["text", "markdown", "json"]), help="Output format")
def inject(message: str | None, session: str | None, max_tokens: int, copy: bool, fmt: str) -> None:
    """Generate context snippet for web UIs (ChatGPT, Claude, Gemini).
    
    Usage:
      continuity inject "What should I work on next?"
      continuity inject --session abc123 "Continue the auth discussion"
      continuity inject --copy "Tell me about the project"
    
    Then paste the output into your AI chat.
    """
    engine = MemoryEngine()
    
    # Get existing messages if continuing a session
    messages = []
    if session:
        messages = engine.storage.get_messages(session)
    
    # Get relevant context
    context = engine.get_context(messages, query=message, max_tokens=max_tokens)
    
    # Format output
    if fmt == "json":
        output = {
            "memories": [{"content": m.content, "type": m.memory_type.value} for m in context.relevant_memories],
            "recent_topics": [{"title": c.title, "provider": c.provider} for c in context.relevant_conversations],
            "recent_messages": [{"role": m.role.value, "content": m.content[:200]} for m in context.recent_messages[-5:]],
            "query": message,
        }
        import json
        result = json.dumps(output, indent=2)
    elif fmt == "markdown":
        result = _format_markdown(context, message)
    else:
        result = _format_text(context, message)
    
    # Output
    if copy:
        try:
            # Try multiple clipboard methods
            if sys.platform == "win32":
                subprocess.run(["clip"], input=result.encode(), check=True)
            elif sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=result.encode(), check=True)
            else:
                subprocess.run(["xclip", "-selection", "clipboard"], input=result.encode(), check=True)
            console.print("[green]Copied to clipboard![/green]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[yellow]Could not copy to clipboard. Copy manually:[/yellow]")
            console.print()
    
    console.print(result)


def _format_text(context, message: str | None) -> str:
    parts = []
    
    if context.relevant_memories:
        parts.append("## PAST CONTEXT")
        for mem in context.relevant_memories[:8]:
            parts.append(f"- {mem.content}")
        parts.append("")
    
    if context.recent_conversations:
        parts.append("## RECENT TOPICS")
        for conv in context.recent_conversations[:3]:
            title = conv.title or "Untitled"
            parts.append(f"- {title} ({conv.provider}/{conv.model})")
        parts.append("")
    
    if context.recent_messages:
        parts.append("## RECENT MESSAGES")
        for msg in context.recent_messages[-5:]:
            parts.append(f"[{msg.role.value}]: {msg.content[:200]}")
        parts.append("")
    
    if message:
        parts.append("## YOUR MESSAGE")
        parts.append(message)
    
    return "\n".join(parts)


def _format_markdown(context, message: str | None) -> str:
    parts = []
    
    if context.relevant_memories:
        parts.append("### Past Context")
        for mem in context.relevant_memories[:8]:
            parts.append(f"- {mem.content}")
        parts.append("")
    
    if context.recent_messages:
        parts.append("### Conversation History")
        for msg in context.recent_messages[-5:]:
            role = "**You**" if msg.role == Role.USER else "**AI**"
            parts.append(f"{role}: {msg.content[:200]}")
        parts.append("")
    
    if message:
        parts.append(f"### Current Message\n{message}")
    
    return "\n".join(parts)


# ── SESSION ───────────────────────────────────────────────────────

@cli.group()
def session() -> None:
    """Manage conversation sessions."""
    pass


@session.command("new")
@click.option("--provider", "-p", default="openai", help="AI provider")
@click.option("--model", "-m", default=None, help="Model name")
@click.option("--title", "-t", default=None, help="Session title")
def session_new(provider: str, model: str | None, title: str | None) -> None:
    """Start a new conversation session."""
    engine = MemoryEngine()
    conv = engine.start_session(provider, model or "default", title)
    console.print(f"[green]Session started![/green] ID: [cyan]{conv.id}[/cyan]")
    if title:
        console.print(f"Title: {title}")
    console.print(f"Provider: {provider}/{model or 'default'}")
    console.print(f"\nUse: continuity inject --session {conv.id[:8]} \"your message\"")


@session.command("list")
@click.option("--limit", "-n", default=10, help="Number of sessions to show")
def session_list(limit: int) -> None:
    """List conversation sessions."""
    engine = MemoryEngine()
    convs = engine.storage.list_conversations(limit=limit)
    if not convs:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    table = Table(title="Sessions")
    table.add_column("ID", style="cyan", max_width=12)
    table.add_column("Title", style="white")
    table.add_column("Provider", style="green")
    table.add_column("Messages", justify="right")
    table.add_column("Created", style="dim")

    for c in convs:
        table.add_row(
            c.id[:12],
            c.title or "[dim]Untitled[/dim]",
            f"{c.provider}/{c.model}",
            str(c.message_count),
            c.created_at.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@session.command("resume")
@click.argument("session_id")
def session_resume(session_id: str) -> None:
    """Resume a conversation session and show context."""
    engine = MemoryEngine()
    conv = engine.storage.get_conversation(session_id)
    if not conv:
        console.print(f"[red]Session not found: {session_id}[/red]")
        return

    messages = engine.storage.get_messages(session_id)
    console.print(Panel(
        f"[cyan]{conv.title or 'Untitled'}[/cyan]\n"
        f"Provider: {conv.provider}/{conv.model}\n"
        f"Messages: {conv.message_count}\n"
        f"Created: {conv.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Use: continuity inject --session {conv.id[:8]} \"your message\"",
        title=f"Session {session_id[:12]}",
        border_style="cyan",
    ))

    if messages:
        console.print("\n[bold]Recent messages:[/bold]")
        for msg in messages[-10:]:
            role_style = "green" if msg.role == Role.USER else "blue"
            console.print(f"[{role_style}]{msg.role.value}[/{role_style}]: {msg.content[:200]}")


@session.command("add")
@click.argument("session_id")
@click.option("--role", "-r", required=True, type=click.Choice(["user", "assistant", "system"]))
@click.option("--content", "-c", required=True)
def session_add(session_id: str, role: str, content: str) -> None:
    """Add a message to a session."""
    engine = MemoryEngine()
    msg = engine.add_message(session_id, Role(role), content)
    console.print(f"[green]Message added![/green] ID: {msg.id[:12]}")


# ── MEMORY ────────────────────────────────────────────────────────

@cli.group()
def memory() -> None:
    """Manage memories."""
    pass


@memory.command("add")
@click.argument("content")
@click.option("--type", "mem_type", default="semantic", help="Memory type (episodic/semantic/procedural)")
@click.option("--confidence", "-c", default=1.0, help="Confidence (0-1)")
def memory_add(content: str, mem_type: str, confidence: float) -> None:
    """Store a new memory."""
    engine = MemoryEngine()
    memory_type = MemoryType(mem_type)
    mem = engine.store_memory(content, memory_type=memory_type, confidence=confidence)
    console.print(f"[green]Memory stored![/green] ID: [cyan]{mem.id}[/cyan]")
    console.print(f"Type: {mem_type} | Confidence: {confidence}")


@memory.command("search")
@click.argument("query")
@click.option("--limit", "-n", default=5, help="Max results")
def memory_search(query: str, limit: int) -> None:
    """Search memories by semantic similarity."""
    engine = MemoryEngine()
    results = engine.search_memories(query, limit=limit)
    if not results:
        console.print("[yellow]No memories found.[/yellow]")
        return

    for i, (mem, score) in enumerate(results, 1):
        console.print(Panel(
            f"{mem.content}\n\n"
            f"[dim]Score: {score:.3f} | Type: {mem.memory_type.value} | "
            f"Confidence: {mem.confidence}[/dim]",
            title=f"Memory {i}",
            border_style="blue",
        ))


@memory.command("list")
@click.option("--type", "mem_type", default=None, help="Filter by type")
@click.option("--limit", "-n", default=20, help="Max results")
def memory_list(mem_type: str | None, limit: int) -> None:
    """List stored memories."""
    engine = MemoryEngine()
    mt = MemoryType(mem_type) if mem_type else None
    memories = engine.storage.list_memories(memory_type=mt, limit=limit)
    if not memories:
        console.print("[yellow]No memories found.[/yellow]")
        return

    table = Table(title="Memories")
    table.add_column("ID", style="cyan", max_width=12)
    table.add_column("Content", max_width=60)
    table.add_column("Type", style="green")
    table.add_column("Conf", justify="right")
    table.add_column("Created", style="dim")

    for m in memories:
        table.add_row(
            m.id[:12],
            m.content[:60] + ("..." if len(m.content) > 60 else ""),
            m.memory_type.value,
            f"{m.confidence:.1f}",
            m.created_at.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@memory.command("forget")
@click.argument("memory_id")
def memory_forget(memory_id: str) -> None:
    """Delete a memory."""
    engine = MemoryEngine()
    engine.storage.delete_memory(memory_id)
    console.print(f"[green]Memory deleted: {memory_id}[/green]")


@memory.command("consolidate")
def memory_consolidate() -> None:
    """Merge duplicate memories."""
    engine = MemoryEngine()
    merged = engine.consolidate_memories()
    console.print(f"[green]Consolidated {merged} duplicate memories.[/green]")


# ── STATS ─────────────────────────────────────────────────────────

@cli.command()
def stats() -> None:
    """Show storage statistics."""
    engine = MemoryEngine()
    s = engine.storage.get_stats()
    size_kb = s["db_size_bytes"] / 1024
    size_mb = size_kb / 1024

    console.print(Panel(
        f"Conversations: {s['conversations']}\n"
        f"Messages: {s['messages']}\n"
        f"Memories: {s['memories']}\n"
        f"Temporal Facts: {s['temporal_facts']}\n\n"
        f"Database: {s['db_path']}\n"
        f"Size: {size_mb:.2f} MB ({size_kb:.1f} KB)",
        title="Continuity Stats",
        border_style="green",
    ))


# ── PROVIDERS ─────────────────────────────────────────────────────

@cli.command()
def providers() -> None:
    """List available AI providers."""
    from continuity.providers.registry import list_providers

    table = Table(title="Available Providers")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")

    descriptions = {
        "openai": "OpenAI (GPT-4, GPT-4o, o1)",
        "anthropic": "Anthropic (Claude)",
        "google": "Google (Gemini)",
        "xai": "xAI (Grok)",
        "ollama": "Ollama (local models)",
        "openai-compatible": "Any OpenAI-compatible API",
    }

    for p in list_providers():
        table.add_row(p, descriptions.get(p, ""))
    console.print(table)


# ── SHELL SETUP ───────────────────────────────────────────────────

@cli.command()
def setup() -> None:
    """Show setup instructions for different tools."""
    
    console.print(Panel(
        """[bold]ChatGPT / Claude Web / Gemini Web[/bold]

  1. Run: continuity inject "your question"
  2. Copy the output
  3. Paste into the AI chat
  
  Or use --copy flag:
  continuity inject --copy "your question"

[bold]Claude Desktop / Cursor / Windsurf (MCP)[/bold]

  Add to claude_desktop_config.json:
  
  {
    "mcpServers": {
      "continuity": {
        "command": "continuity",
        "args": ["mcp"]
      }
    }
  }

[bold]VS Code / Any IDE[/bold]

  1. Run: continuity mcp
  2. Configure your IDE to use MCP
  3. Or use the CLI in the terminal

[bold]Python Scripts[/bold]

  from continuity.core.memory import MemoryEngine
  engine = MemoryEngine()
  
  # Store memories
  engine.store_memory("Important fact")
  
  # Get context
  context = engine.get_context(messages)

[bold]Shell Aliases (add to .bashrc/.zshrc)[/bold]

  alias ci='continuity inject'
  alias cs='continuity session new'
  alias cm='continuity memory add'
  alias cml='continuity memory list'
  alias cstats='continuity stats'""",
        title="Setup Guide",
        border_style="green",
    ))


# ── MCP SERVER ────────────────────────────────────────────────────

@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=3000, help="Port to bind to")
def mcp(host: str, port: int) -> None:
    """Start the MCP server for Claude Desktop, Cursor, etc."""
    from continuity.mcp.server import mcp as mcp_server
    console.print(f"[green]Starting MCP server...[/green]")
    console.print(f"Configure your tool to connect to this server.")
    mcp_server.run()


# ── EXPORT/IMPORT ─────────────────────────────────────────────────

@cli.command()
@click.option("--format", "-f", "fmt", default="json", type=click.Choice(["json", "markdown"]))
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def export(fmt: str, output: str | None) -> None:
    """Export all memories and sessions."""
    engine = MemoryEngine()
    
    data = {
        "stats": engine.storage.get_stats(),
        "memories": [
            {"content": m.content, "type": m.memory_type.value, "confidence": m.confidence}
            for m in engine.storage.list_memories(limit=10000)
        ],
        "conversations": [
            {"id": c.id, "title": c.title, "provider": c.provider, "model": c.model}
            for c in engine.storage.list_conversations(limit=1000)
        ],
    }
    
    if fmt == "json":
        import json
        result = json.dumps(data, indent=2)
    else:
        parts = ["# Continuity Export\n"]
        parts.append(f"## Stats\n- Conversations: {data['stats']['conversations']}")
        parts.append(f"- Memories: {data['stats']['memories']}\n")
        parts.append("## Memories")
        for m in data["memories"]:
            parts.append(f"- [{m['type']}] {m['content']}")
        result = "\n".join(parts)
    
    if output:
        with open(output, "w") as f:
            f.write(result)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(result)


if __name__ == "__main__":
    cli()
