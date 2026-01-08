import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from typing import List
from client import AzureReposClient
from azure_arbiter import AzureReposArbiter

# Load environment variables
load_dotenv()

ORGANIZATION = os.getenv("AZURE_DEVOPS_ORGANIZATION")
PROJECT = os.getenv("AZURE_DEVOPS_PROJECT")
REPOSITORY_ID = os.getenv("AZURE_DEVOPS_REPOSITORY_ID")

# Create an MCP server
mcp = FastMCP("azure-repos-review-support")

def get_client() -> AzureReposArbiter:
    pat = os.environ.get("AZURE_DEVOPS_PAT")
    if not pat:
        raise ValueError("AZURE_DEVOPS_PAT environment variable not set")
    return AzureReposArbiter(AzureReposClient(pat))

def validate_config():
    if not all([ORGANIZATION, PROJECT, REPOSITORY_ID]):
        raise ValueError("Server configuration missing: AZURE_DEVOPS_ORGANIZATION, AZURE_DEVOPS_PROJECT, or AZURE_DEVOPS_REPOSITORY_ID not set.")

@mcp.tool()
def get_pull_request(id: int) -> dict:
    """
    Get detailed information for a specific pull request.
    This includes the PR title, description, and status.

    Note on status:
    - 'status': Can be 'active' (open), 'completed' (merged), or 'abandoned'.
      An 'active' status means the PR is still open and needs review.

    Args:
        id (int): The ID of the pull request.

    Returns:
        dict: A dictionary containing pull request details.
    """
    validate_config()
    client = get_client()
    return client.get_pull_request(ORGANIZATION, PROJECT, REPOSITORY_ID, id)

@mcp.tool()
def get_pull_request_change_summary(id: int) -> dict:
    """
    Get a summary of changes in a specific pull request, including the list of changed files and their change types.
    This does not include the actual code diff.

    Args:
        id (int): The ID of the pull request.

    Returns:
        dict: A dictionary containing:
            - changes: List of file changes with:
                - path: File path in the PR (new location for renamed files)
                - change_type: Raw Azure DevOps change type
                - status: Normalized status ("added", "deleted", "modified", "renamed")
                - exists_in_base: Boolean indicating if file exists in base branch
                - exists_in_head: Boolean indicating if file exists in head branch
                - original_path: Original path (only for renamed files)
                - previous_filename: Same as original_path, clearer naming for AI
            
            Note: For renamed files, only the new location entry is included.
            The old location entry (with status="deleted") is automatically filtered out.
    """
    validate_config()
    client = get_client()
    return client.get_pull_request_change_summary(ORGANIZATION, PROJECT, REPOSITORY_ID, id)

@mcp.tool()
def get_pull_request_comments(id: int) -> List[dict]:
    """
    Get the comment threads for a specific pull request.

    Args:
        id (int): The ID of the pull request.

    Returns:
        List[dict]: A list of comment threads associated with the pull request.
    """
    validate_config()
    client = get_client()
    return client.get_comments(ORGANIZATION, PROJECT, REPOSITORY_ID, id)

@mcp.tool()
def get_file_content(path: str, version: str = None) -> str:
    """
    Get the content of a file from the repository.

    Args:
        path (str): The path to the file.
        version (str, optional): The version string (e.g. branch name or commit info). Defaults to None (default branch).

    Returns:
        str: The content of the file.
    """
    validate_config()
    client = get_client()
    return client.get_file_content(ORGANIZATION, PROJECT, REPOSITORY_ID, path, version)

@mcp.tool()
def get_pull_request_unified_diff(id: int) -> str:
    """
    Get the unified diff format for a specific pull request.

    Args:
        id (int): The ID of the pull request.

    Returns:
        str: The unified diff format of all changed files in the pull request.
             This format is compatible with standard diff tools and AI code review systems.
    """
    validate_config()
    client = get_client()
    return client.get_pull_request_unified_diff(ORGANIZATION, PROJECT, REPOSITORY_ID, id)

if __name__ == "__main__":
    mcp.run()
