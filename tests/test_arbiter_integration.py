import pytest
import json

def test_get_pull_request_details(arbiter, context, pr_id):
    print(f"\n[TEST] Fetching details for PR ID: {pr_id}")
    pr = arbiter.get_pull_request(
        context['organization'],
        context['project'],
        context['repo_id'],
        pr_id
    )
    print(f"[RESPONSE] PR Details:\n{json.dumps(pr, indent=2)}")
    assert pr is not None
    assert 'pull_request_id' in pr
    assert pr['pull_request_id'] == pr_id
    
    # Verify only expected keys are present
    expected_keys = {
        'creation_date', 'description', 'pull_request_id', 'source_ref_name', 
        'target_ref_name', 'title', 'url', 'status', 'repository_name'
    }
    assert set(pr.keys()) == expected_keys, f"Unexpected keys in response: {set(pr.keys()) - expected_keys}"
    print(f"[SUCCESS] PR Status: {pr.get('status')}, Repository: {pr.get('repository_name')}")

def test_get_pull_request_change_summary(arbiter, context, pr_id):
    print(f"\n[TEST] Fetching change summary for PR ID: {pr_id}")
    summary = arbiter.get_pull_request_change_summary(
        context['organization'],
        context['project'],
        context['repo_id'],
        pr_id
    )
    # print(f"[RESPONSE] Change Summary:\n{json.dumps(summary, indent=2)}")
    assert summary is not None
    assert 'changes' in summary
    
    # Verify filtering - .meta files and folders should be filtered out
    print(f"\n[VALIDATION] Checking {len(summary['changes'])} changes for filtering...")
    
    meta_files_found = []
    folders_found = []
    
    for idx, change in enumerate(summary['changes']):
        item = change.get('item', {})
        path = item.get('path', '')
        
        # git_object_typeはgitObjectTypeまたはgit_object_typeで返される可能性がある
        git_object_type = item.get('gitObjectType') or item.get('git_object_type', '')
        is_folder = item.get('isFolder', False)
        
        print(f"  Change {idx + 1}: path='{path}', gitObjectType='{git_object_type}', isFolder={is_folder}")
        
        # Check for .meta files
        if path.endswith('.meta'):
            meta_files_found.append(path)
        
        # Check for trees (folders)
        if git_object_type == 'tree' or is_folder:
            folders_found.append(path)
    
    # Assert no .meta files
    assert len(meta_files_found) == 0, f"Found {len(meta_files_found)} .meta file(s): {meta_files_found}"
    
    # Assert no trees (folders)
    assert len(folders_found) == 0, f"Found {len(folders_found)} folder(s): {folders_found}"
    
    print(f"[SUCCESS] All {len(summary['changes'])} changes are valid (no .meta files or folders)")
    
    # Verify change_counts is removed
    assert 'change_counts' not in summary, "change_counts should be removed"


def test_get_comments(arbiter, context, pr_id):
    print(f"\n[TEST] Fetching comments for PR ID: {pr_id}")
    comments = arbiter.get_comments(
        context['organization'],
        context['project'],
        context['repo_id'],
        pr_id
    )
    print(f"[RESPONSE] Comments count: {len(comments)}")
    
    for idx, thread in enumerate(comments):
        thread_id = thread.get('id')
        comments_list = thread.get('comments', [])
        num_comments = len(comments_list)
        
        # Determine if it's a code comment or a system comment
        thread_context = thread.get('thread_context')
        comment_type = "Code Comment" if thread_context else "System/Other Comment"
        
        print(f"  Thread {idx + 1}: ID={thread_id}, Type={comment_type}, Comments={num_comments}")
        if thread_context:
            print(f"    Path: {thread_context.get('file_path')}")
            
    assert isinstance(comments, list)

    
    # Verify only expected keys are present in each comment
    expected_keys = {
        'comments', 'id', 'last_updated_date', 'published_date',
        'thread_context', 'pull_request_thread_context'
    }
    for comment in comments:
        assert set(comment.keys()) == expected_keys, f"Unexpected keys in comment: {set(comment.keys()) - expected_keys}"

def test_get_file_content(arbiter, context, pr_id):
    # まずPRの変更概要から存在するファイル名を取得して、確実に存在するファイルでテストする
    summary = arbiter.get_pull_request_change_summary(
        context['organization'],
        context['project'],
        context['repo_id'],
        pr_id
    )
    
    test_path = "README.md" # デフォルト
    if summary and 'changes' in summary and len(summary['changes']) > 0:
        # 最初のファイルのパスを使用
        test_path = summary['changes'][0]['item']['path']
    
    print(f"\n[TEST] Fetching file content for: {test_path}")
    
    # ここではtry-exceptを使わず、失敗した場合はテスト自体を失敗させる
    content = arbiter.get_file_content(
        context['organization'],
        context['project'],
        context['repo_id'],
        test_path
    )
    
    print(f"[RESPONSE] File Content length: {len(content)} characters")
    if len(content) > 0:
        print(f"[RESPONSE] File Content (first 100 chars):\n{content[:100]}...")
    
    assert content is not None
    assert len(content) > 0, f"File content for {test_path} is empty"


def test_get_pull_request_unified_diff(arbiter, context, pr_id):
    print(f"\n[TEST] Fetching unified diff for PR ID: {pr_id}")
    unified_diff = arbiter.get_pull_request_unified_diff(
        context['organization'],
        context['project'],
        context['repo_id'],
        pr_id
    )
    
    print(f"[RESPONSE] Unified Diff Length: {len(unified_diff)} characters")
    if unified_diff:
        print(f"[RESPONSE] Unified Diff (first 500 chars):\n{unified_diff[:500]}...")
    
    assert unified_diff is not None
    assert isinstance(unified_diff, str)
    
    # エラーメッセージでないことを確認
    assert not unified_diff.startswith("# Error:"), f"Error in response: {unified_diff}"
    
    # PRに何らかの変更があるはずなので、空であってはならない
    assert len(unified_diff) > 0, "Unified diff should not be empty for a PR with changes"
    
    # Unified Diff形式の基本的な検証
    lines = unified_diff.splitlines()
    
    # ヘッダーの存在を確認 (--- a/... and +++ b/...)
    has_minus_header = any(line.startswith("--- a/") for line in lines)
    has_plus_header = any(line.startswith("+++ b/") for line in lines)
    has_hunk_header = any(line.startswith("@@ ") for line in lines)
    
    assert has_minus_header, "Missing '--- a/' header"
    assert has_plus_header, "Missing '+++ b/' header"
    assert has_hunk_header, "Missing '@@ ' hunk header"
    
    print("[SUCCESS] Unified Diff format validated successfully")

