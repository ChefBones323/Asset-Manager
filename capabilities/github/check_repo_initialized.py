def check_repo_initialized(owner: str, repo: str, token: str) -> dict:
    """Check if a GitHub repository has been initialised.

    Verifies the presence of an initial commit and essential files
    (e.g. README, .gitignore) in the repository.

    Args:
        owner: Repository owner (user or organisation).
        repo: Repository name.
        token: GitHub personal access token or app token.

    Returns:
        dict with keys:
            initialized (bool): Whether the repo has at least one commit.
            has_readme (bool): Whether a README file exists.
            default_branch (str | None): The default branch name.
    """
    raise NotImplementedError("GitHub API integration pending")
