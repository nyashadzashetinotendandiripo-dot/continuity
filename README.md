# Continuity

**AI conversation memory — never lose the thread.**

> "An AI that can solve Olympiad mathematics but cannot remember what you were talking about twenty minutes ago is not displaying superior intelligence. It is displaying intelligence without continuity."

---

## What is Continuity?

Continuity is a local-first tool that gives you **memory** across AI conversations. It sits between you and any AI provider (OpenAI, Anthropic, Google, Meta, xAI, Ollama, or any OpenAI-compatible API) and remembers everything — so you never have to re-explain context again.

**The problem it solves:** AI models forget what you were talking about. This breaks your chain of thought. Continuity restores it.

---

## Quick Start

```bash
# Install
pip install continuity

# Initialize
continuity init

# Store a memory
continuity memory add "The project uses PostgreSQL as the primary database"

# Search memories
continuity memory search "what database are we using"

# Start a session
continuity session new --provider openai --model gpt-4o

# See stats
continuity stats
```

---

## How It Works

1. **You talk to AI** through any provider
2. **Continuity stores** your conversations locally in SQLite
3. **It extracts** important facts, decisions, and context
4. **Next session**, it automatically loads relevant past context
5. **The AI feels like it remembers** — because Continuity feeds it your history

### Storage

Everything stays on your machine:

- **Location:** `~/.continuity/continuity.db` (or custom path)
- **Size:** ~1 MB per 100 conversations (very lightweight)
- **Format:** SQLite database with vector embeddings
- **Backup:** Just copy the `.db` file

---

## Providers

Works with virtually any AI provider:

| Provider | Models | Setup |
|----------|--------|-------|
| **OpenAI** | GPT-4, GPT-4o, o1 | `export OPENAI_API_KEY=sk-...` |
| **Anthropic** | Claude 3.5, Claude 3 | `export ANTHROPIC_API_KEY=sk-ant-...` |
| **Google** | Gemini 1.5, 2.0 | `export GOOGLE_API_KEY=...` |
| **xAI** | Grok | `export XAI_API_KEY=...` |
| **Ollama** | Any local model | Just install Ollama |
| **Any OpenAI-compatible** | Together, Fireworks, DeepSeek, Groq, LM Studio, vLLM | Set base URL |

---

## CLI Commands

```bash
# Sessions
continuity session new -p openai -m gpt-4o -t "Project planning"
continuity session list
continuity session resume <session-id>

# Memories
continuity memory add "Important decision: use Redis for caching"
continuity memory search "caching strategy"
continuity memory list --type semantic
continuity memory forget <memory-id>

# Provider info
continuity providers

# Stats
continuity stats
```

---

## MCP Server

Continuity runs as an MCP server, integrating with:

- Claude Desktop
- Cursor
- Windsurf
- Zed
- Any MCP-compatible tool

### Setup for Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "continuity": {
      "command": "continuity",
      "args": ["mcp"]
    }
  }
}
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `start_session` | Start a new conversation with memory |
| `get_context` | Get relevant past context |
| `store_memory` | Store important information |
| `search_memory` | Search memories by semantic similarity |
| `list_sessions` | List past conversations |
| `add_message` | Add message to current session |
| `build_prompt` | Build system prompt with memory |
| `get_stats` | Get storage statistics |

---

## Python API

```python
from continuity.core.memory import MemoryEngine

engine = MemoryEngine()

# Start a session
conv = engine.start_session("openai", "gpt-4o", title="My project")

# Store memories
engine.store_memory("We decided to use TypeScript for the frontend")

# Get context
context = engine.get_context(messages, query="frontend technology")

# Build enhanced prompt
prompt = engine.build_system_prompt(context, base_prompt="You are a helpful assistant")
```

---

## Privacy & Security

- **100% local** — data never leaves your machine
- **No cloud required** — works fully offline
- **Your data** — just a SQLite file you can backup/move/delete
- **Open source** — MIT license, audit the code yourself

---

## Architecture

```
continuity/
├── core/
│   ├── models.py        # Data models
│   ├── memory.py        # Memory engine
│   └── embeddings.py    # Local embedding service
├── providers/           # Multi-provider support
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   ├── google_provider.py
│   ├── xai_provider.py
│   ├── ollama_provider.py
│   └── openai_compat_provider.py
├── storage/
│   └── sqlite.py        # SQLite storage
├── cli/
│   └── main.py          # CLI interface
└── mcp/
    └── server.py        # MCP server
```

---

## License

MIT — Free forever, open source.

---

## The Philosophy

> They keep extending the model's chain of thought while breaking the human chain of thought.

Continuity exists because **the human's ability to think matters more than the model's ability to compute**. When context breaks, thought breaks. When thought breaks, understanding breaks.

This tool restores the chain.
