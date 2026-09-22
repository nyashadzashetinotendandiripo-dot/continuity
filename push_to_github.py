"""Push continuity to GitHub using GitHub API (no git needed)."""

import os
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path

REPO_NAME = "continuity"
DESCRIPTION = "AI conversation memory - never lose the thread. Works with any AI provider."
WORKSPACE = Path(r"C:\Users\lenovo\Documents\Default Project\continuity")

# Files to exclude
EXCLUDE = {
    "__pycache__",
    "*.pyc",
    ".git",
    "node_modules",
    "*.db",
    "*.db-journal",
    ".venv",
    "venv",
}

def get_github_token():
    """Try to get GitHub token from gh CLI or environment."""
    # Check environment
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    
    # Try gh CLI config
    gh_config = Path.home() / ".config" / "gh" / "hosts.yml"
    if gh_config.exists():
        content = gh_config.read_text()
        for line in content.split("\n"):
            if "oauth_token:" in line:
                return line.split("oauth_token:")[1].strip()
    
    return None

def api_request(url, data=None, token=None, method="GET"):
    """Make GitHub API request."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Continuity-Publisher",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    
    if data:
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        response = urllib.request.urlopen(req)
        return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"API Error {e.code}: {error_body}")
        return None

def create_repo(token):
    """Create GitHub repository."""
    print(f"Creating repository: {REPO_NAME}")
    result = api_request(
        "https://api.github.com/user/repos",
        data={"name": REPO_NAME, "description": DESCRIPTION, "private": False},
        token=token,
        method="POST"
    )
    if result:
        print(f"  Created: {result['html_url']}")
        return result
    return None

def get_files():
    """Get all files to upload."""
    files = []
    for root, dirs, filenames in os.walk(WORKSPACE):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE]
        
        for filename in filenames:
            filepath = Path(root) / filename
            relative = filepath.relative_to(WORKSPACE)
            
            # Skip excluded files
            if any(filename.endswith(ext.replace("*", "")) for ext in EXCLUDE if "*" in ext):
                continue
            
            # Skip large files
            if filepath.stat().st_size > 1000000:  # 1MB
                continue
            
            files.append((relative, filepath))
    
    return files

def upload_file(token, filepath, relative_path, repo_info):
    """Upload a single file to GitHub."""
    content = filepath.read_bytes()
    encoded = base64.b64encode(content).decode("utf-8")
    
    url = f"https://api.github.com/repos/{repo_info['full_name']}/contents/{relative_path.as_posix()}"
    
    data = {
        "message": f"Add {relative_path}",
        "content": encoded,
    }
    
    result = api_request(url, data=data, token=token, method="PUT")
    return result is not None

def main():
    print("=" * 50)
    print("  Pushing Continuity to GitHub")
    print("=" * 50)
    print()
    
    # Get token
    token = get_github_token()
    if not token:
        print("ERROR: No GitHub token found.")
        print()
        print("Run this first:")
        print("  gh auth login")
        print()
        print("Or set environment variable:")
        print("  $env:GITHUB_TOKEN = 'your_token_here'")
        return False
    
    print(f"GitHub token found: {token[:8]}...")
    print()
    
    # Create repo
    repo = create_repo(token)
    if not repo:
        print("Failed to create repository.")
        return False
    
    # Get files
    print("\nScanning files...")
    files = get_files()
    print(f"  Found {len(files)} files to upload")
    
    # Upload files
    print("\nUploading files...")
    success = 0
    failed = 0
    
    for relative, filepath in files:
        try:
            if upload_file(token, filepath, relative, repo):
                print(f"  OK {relative}")
                success += 1
            else:
                print(f"  FAIL {relative}")
                failed += 1
        except Exception as e:
            print(f"  FAIL {relative}: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"  Complete: {success} uploaded, {failed} failed")
    print(f"  Repository: {repo['html_url']}")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    main()
