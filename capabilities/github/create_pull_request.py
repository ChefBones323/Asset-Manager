def create_pull_request(owner: str, repo: str, title: str, head: str, base: str, body: str, token: str) -> dict:
    """Create a new pull request to merge changes from one branch into another.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: Pull request title.
        head: The branch containing the changes.
        base: The branch to merge into.
        body: Pull request description.
        token: GitHub personal access token or app token.

    Returns:
        dict with keys:
            number (int): PR number.
            url (str): URL of the created pull request.
            state (str): PR state (e.g. "open").
    """
    raise NotImplementedError("GitHub API integration pending")
