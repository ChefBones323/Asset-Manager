def fetch_commit(owner: str, repo: str, sha: str, token: str) -> dict:
    """Retrieve metadata and details of a specific commit.

    Args:
        owner: Repository owner.
        repo: Repository name.
        sha: Full or abbreviated commit SHA.
        token: GitHub personal access token or app token.

    Returns:
        dict with keys:
            sha (str): Full commit SHA.
            message (str): Commit message.
            author (str): Author name.
            date (str): ISO-8601 commit date.
            files_changed (int): Number of files changed.
    """
    raise NotImplementedError("GitHub API integration pending")
