import pytest
import json
import os
import sys

# Add project root to sys.path so we can import client
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client import AzureReposClient
from azure_arbiter import AzureReposArbiter

MCP_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../.vscode/mcp.json'))

@pytest.fixture(scope="session")
def mcp_config():
    with open(MCP_CONFIG_PATH, 'r') as f:
        data = json.load(f)
    return data['servers']['azure-repos-review-support']['env']

@pytest.fixture(scope="session")
def client(mcp_config):
    pat = mcp_config['AZURE_DEVOPS_PAT']
    return AzureReposClient(pat=pat)

@pytest.fixture(scope="session")
def arbiter(client):
    return AzureReposArbiter(client)

@pytest.fixture(scope="session")
def context(mcp_config):
    return {
        "organization": mcp_config['AZURE_DEVOPS_ORGANIZATION'],
        "project": mcp_config['AZURE_DEVOPS_PROJECT'],
        "repo_id": mcp_config['AZURE_DEVOPS_REPOSITORY_ID']
    }

@pytest.fixture(scope="session")
def pr_id():
    return 354
