"""Shell integration for Continuity — watch mode, clipboard, aliases."""

from __future__ import annotations

import sys
import os
import subprocess
import json
from pathlib import Path


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard. Works on Windows, macOS, Linux."""
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            process.communicate(input=text.encode("utf-16-le"))
            return True
        elif sys.platform == "darwin":
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            process.communicate(input=text.encode())
            return True
        else:
            # Linux: try xclip, then xsel
            for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
                try:
                    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                    process.communicate(input=text.encode())
                    return True
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return False


def get_clipboard() -> str | None:
    """Get text from clipboard."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        elif sys.platform == "darwin":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else None
        else:
            for cmd in [["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]]:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return result.stdout.strip()
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return None


# Shell script for bash/zsh integration
SHELL_SCRIPT = '''#!/bin/bash
# Continuity shell integration
# Add to ~/.bashrc or ~/.zshrc: source ~/.continuity/continuity.sh

# Quick aliases
alias ci='continuity inject'
alias ciw='continuity inject --copy'  # inject and copy to clipboard
alias cs='continuity session new'
alias csl='continuity session list'
alias cm='continuity memory add'
alias cml='continuity memory list'
alias cms='continuity memory search'
alias cstats='continuity stats'

# Quick inject: type your message, it goes to clipboard
c() {
    continuity inject --copy "$*"
    echo "✓ Context copied to clipboard. Paste into your AI."
}

# Continue a session
cc() {
    local session_id="$1"
    shift
    continuity inject --session "$session_id" --copy "$*"
    echo "✓ Context copied to clipboard. Paste into your AI."
}

# Store a quick memory
m() {
    continuity memory add "$*"
}
'''


# PowerShell integration for Windows
POWERSHELL_SCRIPT = '''
# Continuity PowerShell integration
# Add to $PROFILE: Import-Module ~/.continuity/continuity.psm1

function ci { continuity inject @args }
function ciw { continuity inject --copy @args }
function cs { continuity session new @args }
function csl { continuity session list @args }
function cm { continuity memory add @args }
function cml { continuity memory list @args }
function cms { continuity memory search @args }
function cstats { continuity stats }

function c {
    param([Parameter(ValueFromRemainingArguments=$true)]$args)
    continuity inject --copy @args
    Write-Host "✓ Context copied to clipboard. Paste into your AI." -ForegroundColor Green
}

function m {
    param([Parameter(ValueFromRemainingArguments=$true)]$args)
    continuity memory add @args
}
'''


def install_shell_integration() -> None:
    """Install shell integration scripts."""
    config_dir = Path.home() / ".continuity"
    config_dir.mkdir(exist_ok=True)
    
    # Write bash script
    bash_script = config_dir / "continuity.sh"
    bash_script.write_text(SHELL_SCRIPT)
    print(f"✓ Bash/Zsh script: {bash_script}")
    print(f"  Add to ~/.bashrc or ~/.zshrc:")
    print(f"  source ~/.continuity/continuity.sh")
    
    # Write PowerShell module
    ps_module = config_dir / "continuity.psm1"
    ps_module.write_text(POWERSHELL_SCRIPT)
    print(f"✓ PowerShell module: {ps_module}")
    print(f"  Add to $PROFILE:")
    print(f"  Import-Module ~/.continuity/continuity.psm1")
    
    # Write fish function
    fish_dir = Path.home() / ".config" / "fish" / "functions"
    fish_dir.mkdir(parents=True, exist_ok=True)
    
    for func_name, func_body in [
        ("ci.fish", "continuity inject $argv"),
        ("ciw.fish", "continuity inject --copy $argv"),
        ("cs.fish", "continuity session new $argv"),
        ("cm.fish", "continuity memory add $argv"),
        ("c.fish", "continuity inject --copy $argv; echo '✓ Context copied to clipboard. Paste into your AI.'"),
        ("m.fish", "continuity memory add $argv"),
    ]:
        func_file = fish_dir / func_name
        func_file.write_text(f"function {func_name.replace('.fish', '')}\n    {func_body}\nend\n")
    
    print(f"✓ Fish functions: {fish_dir}")
    print(f"  Restart fish shell or run: source ~/.config/fish/functions/*.fish")


if __name__ == "__main__":
    install_shell_integration()
