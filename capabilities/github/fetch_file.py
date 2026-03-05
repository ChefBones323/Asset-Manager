def fetch_file(owner: str, repo: str, path: str, ref: str, token: str) -> dict:
    """Fetch the contents of a file from a repository at a specific ref.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path within the repository.
        ref: Branch name, tag, or commit SHA.
        token: GitHub personal access token or app token.

    Returns:
        dict with keys:
            content (str): Decoded file content.
            encoding (str): Content encoding (e.g. "utf-8").
            size (int): File size in bytes.
            sha (str): Blob SHA.
    """
    raise NotImplementedError("GitHub API integration pending")
