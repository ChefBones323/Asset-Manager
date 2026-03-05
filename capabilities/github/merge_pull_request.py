def merge_pull_request(owner: str, repo: str, pull_number: int, merge_method: str, token: str) -> dict:
    """Merge an existing pull request into its target branch.

    Adheres to repository merge policies (squash, rebase, or merge commit).

    Args:
        owner: Repository owner.
        repo: Repository name.
        pull_number: Pull request number.
        merge_method: One of "merge", "squash", or "rebase".
        token: GitHub personal access token or app token.

    Returns:
        dict with keys:
            merged (bool): Whether the merge succeeded.
            sha (str): Merge commit SHA.
            message (str): Merge status message.
    """
    raise NotImplementedError("GitHub API integration pending")
