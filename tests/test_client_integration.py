import pytest
import json

def test_get_pull_request_details(client, context, pr_id):
    print(f"\n[TEST] Fetching details for PR ID: {pr_id}")
    pr = client.get_pull_request(
        context['organization'],
        context['project'],
        context['repo_id'],
        pr_id
    )
    print(f"[RESPONSE] PR Details:\n{json.dumps(pr, indent=2)}")
    assert pr is not None
    assert 'pull_request_id' in pr
    assert pr['pull_request_id'] == pr_id

def test_get_pull_request_diff(client, context, pr_id):
    print(f"\n[TEST] Fetching diff for PR ID: {pr_id}")
    diff = client.get_pull_request_diff(
        context['organization'],
        context['project'],
        context['repo_id'],
        pr_id
    )
    print(f"[RESPONSE] Diff:\n{json.dumps(diff, indent=2)}")
    assert diff is not None
    assert 'changes' in diff

def test_get_comments(client, context, pr_id):
    print(f"\n[TEST] Fetching comments for PR ID: {pr_id}")
    comments = client.get_comments(
        context['organization'],
        context['project'],
        context['repo_id'],
        pr_id
    )
    print(f"[RESPONSE] Comments:\n{json.dumps(comments, indent=2)}")
    assert isinstance(comments, list)

def test_get_file_content(client, context, pr_id):
    # まずPRのディフから存在するファイル名を取得
    diff = client.get_pull_request_diff(
        context['organization'],
        context['project'],
        context['repo_id'],
        pr_id
    )
    
    test_path = "README.md"
    if diff and 'changes' in diff and len(diff['changes']) > 0:
        test_path = diff['changes'][0]['item']['path']

    print(f"\n[TEST] Fetching file content for: {test_path}")
    content = client.get_file_content(
        context['organization'],
        context['project'],
        context['repo_id'],
        test_path
    )
    print(f"[RESPONSE] File Content (first 100 chars):\n{content[:100]}...")
    assert content is not None
    assert len(content) > 0

