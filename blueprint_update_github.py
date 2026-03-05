import json
from pathlib import Path

REQUIRED_FIELDS = {"id", "name", "description", "language", "module"}

def load_registry(path: Path) -> dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("registry/capabilities.json must contain a JSON object")
                if "capabilities" not in data or not isinstance(data["capabilities"], list):
                    data["capabilities"] = []
                return data
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse {path}: {e}")
    else:
        return {"capabilities": []}

def save_registry(path: Path, registry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    registry["capabilities"].sort(key=lambda c: c.get("id", ""))
    with path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, sort_keys=True)
        f.write("\n")

def add_new_capabilities(registry: dict, new_capabilities: list) -> int:
    existing_ids = {c.get("id") for c in registry.get("capabilities", [])}
    added = 0
    for cap in new_capabilities:
        cap_id = cap.get("id")
        if cap_id and cap_id not in existing_ids:
            registry["capabilities"].append(cap)
            existing_ids.add(cap_id)
            added += 1
    return added

def main() -> None:
    new_capabilities = [
        {
            "id": "github_check_repo_initialized",
            "name": "GitHub: Check Repository Initialized",
            "type": "github",
            "description": "Check if a GitHub repository has been initialised (presence of an initial commit and essential files).",
            "function": "check_repo_initialized",
            "language": "python",
            "module": "capabilities.github.check_repo_initialized"
        },
        {
            "id": "github_compare_commits",
            "name": "GitHub: Compare Commits",
            "type": "github",
            "description": "Compare two commits or refs within a repository, returning per-file change statistics and metadata.",
            "function": "compare_commits",
            "language": "python",
            "module": "capabilities.github.compare_commits"
        },
        {
            "id": "github_fetch_file",
            "name": "GitHub: Fetch File",
            "type": "github",
            "description": "Fetch the contents of a file from a repository at a specific ref (branch, tag, or commit).",
            "function": "fetch_file",
            "language": "python",
            "module": "capabilities.github.fetch_file"
        },
        {
            "id": "github_fetch_commit",
            "name": "GitHub: Fetch Commit",
            "type": "github",
            "description": "Retrieve metadata and details of a specific commit within a repository.",
            "function": "fetch_commit",
            "language": "python",
            "module": "capabilities.github.fetch_commit"
        },
        {
            "id": "github_search_repository",
            "name": "GitHub: Search Repository Files",
            "type": "github",
            "description": "Search within a repository for files matching specific keywords or patterns.",
            "function": "search",
            "language": "python",
            "module": "capabilities.github.search"
        },
        {
            "id": "github_create_pull_request",
            "name": "GitHub: Create Pull Request",
            "type": "github",
            "description": "Create a new pull request to merge changes from one branch into another.",
            "function": "create_pull_request",
            "language": "python",
            "module": "capabilities.github.create_pull_request"
        },
        {
            "id": "github_merge_pull_request",
            "name": "GitHub: Merge Pull Request",
            "type": "github",
            "description": "Merge an existing pull request into its target branch, adhering to repository policies.",
            "function": "merge_pull_request",
            "language": "python",
            "module": "capabilities.github.merge_pull_request"
        }
    ]

    repo_root = Path(__file__).resolve().parent
    registry_path = repo_root / "registry" / "capabilities.json"
    registry = load_registry(registry_path)
    added = add_new_capabilities(registry, new_capabilities)
    if added:
        save_registry(registry_path, registry)
        print(f"Added {added} capabilities. Updated {registry_path}.")
    else:
        print("No new capabilities were added; the registry already contains all specified GitHub functions.")

if __name__ == "__main__":
    main()
