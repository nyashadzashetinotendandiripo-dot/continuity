# Continuity + OpenCode Integration

## Quick Setup

### 1. Install Continuity

```bash
cd "C:\Users\lenovo\Documents\Default Project\continuity"
pip install -e .
```

### 2. Add to OpenCode Config

Add this to your `opencode.jsonc` (in your project root or `~/.config/opencode/`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "continuity": {
      "type": "local",
      "command": ["python", "-m", "continuity.mcp.server"],
      "enabled": true
    }
  }
}
```

### 3. Use It

Once configured, Continuity tools are available in OpenCode:

```
Store this decision in memory: use PostgreSQL for the database. use continuity
```

```
What did we decide about the authentication system? use continuity
```

```
Start a new session for the frontend work. use continuity
```

## How It Works in OpenCode

When you type `use continuity` in your prompt, OpenCode calls the Continuity MCP server which:

1. **Searches your memory** for relevant past conversations
2. **Injects context** into the current conversation
3. **Stores new information** automatically

## Available Tools

| Tool | What It Does | When to Use |
|------|--------------|-------------|
| `start_session` | Start a new conversation | Beginning new work |
| `get_context` | Get relevant past context | Before responding |
| `store_memory` | Save important info | After decisions, facts |
| `search_memory` | Find past memories | When you need context |
| `list_sessions` | See past conversations | Reviewing work |
| `build_prompt` | Create system prompt with memory | Before long responses |

## Example Prompts

```
Store in memory: We decided to use React with TypeScript for the frontend. use continuity
```

```
What database did we choose? use continuity
```

```
Start a new session and remember everything from our last conversation. use continuity
```

```
Build me a system prompt that includes all our past decisions. use continuity
```

## Files

- Config: `opencode.jsonc` (project root)
- Database: `~/.continuity/continuity.db`
- MCP Server: `continuity/mcp/server.py`
