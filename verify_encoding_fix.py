"""エンコーディング修正の詳細な検証スクリプト"""
import json
import os
from dotenv import load_dotenv
from client import AzureReposClient

# 環境変数を読み込む
load_dotenv()

# 設定を読み込む
MCP_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '.vscode/mcp.json')
with open(MCP_CONFIG_PATH, 'r') as f:
    data = json.load(f)
    config = data['servers']['azure-repos-review-support']['env']

# クライアントを作成
pat = config['AZURE_DEVOPS_PAT']
client = AzureReposClient(pat=pat)

# コンテキスト
organization = config['AZURE_DEVOPS_ORGANIZATION']
project = config['AZURE_DEVOPS_PROJECT']
repo_id = config['AZURE_DEVOPS_REPOSITORY_ID']

# PR 412の詳細を取得
print("PR 412の詳細を取得中...")
pr = client.get_pull_request(organization, project, repo_id, 412)

source_commit = pr.get("last_merge_source_commit", {}).get("commit_id")
target_commit = pr.get("last_merge_target_commit", {}).get("commit_id")

print(f"Source Commit: {source_commit}")
print(f"Target Commit: {target_commit}")

# 問題のファイルを直接テスト
test_files = [
    "/Robstar/Assets/RobstarScripts/DependencyInjector/Background/DistantSceneView.cs",
    "/Robstar/Assets/RobstarScripts/DependencyInjector/Main/Initializer.cs"
]

for file_path in test_files:
    print(f"\n{'='*60}")
    print(f"ファイル: {file_path}")
    print('='*60)
    
    # Baseバージョン（target_commit）を取得
    print(f"\n[Base版を取得中...]")
    try:
        content_base, error_base = client.get_file_content_at_commit(
            organization, project, repo_id, file_path, target_commit
        )
        if error_base:
            print(f"❌ Base版取得エラー: {error_base}")
        else:
            print(f"✅ Base版取得成功: {len(content_base)} 文字")
            # 日本語が含まれているか確認
            if any(ord(c) > 127 for c in content_base):
                print(f"   日本語文字を検出")
    except Exception as e:
        print(f"❌ Base版取得で例外発生: {e}")
    
    # Headバージョン（source_commit）を取得
    print(f"\n[Head版を取得中...]")
    try:
        content_head, error_head = client.get_file_content_at_commit(
            organization, project, repo_id, file_path, source_commit
        )
        if error_head:
            print(f"❌ Head版取得エラー: {error_head}")
        else:
            print(f"✅ Head版取得成功: {len(content_head)} 文字")
            # 日本語が含まれているか確認
            if any(ord(c) > 127 for c in content_head):
                print(f"   日本語文字を検出")
    except Exception as e:
        print(f"❌ Head版取得で例外発生: {e}")

print(f"\n{'='*60}")
print("検証完了！")
print('='*60)
