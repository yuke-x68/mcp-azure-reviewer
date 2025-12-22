# Azure Repos MCP Server

Azure ReposのプルリクエストレビューをサポートするMCPサーバーです。

## 機能

- プルリクエストの詳細情報取得
- プルリクエストの変更概要取得（JSON形式）
- プルリクエストの差分取得（Unified Diff形式）
- プルリクエストのコメント取得
- ファイル内容の取得

## Configuration

以下の環境変数を設定してください:

- `AZURE_DEVOPS_PAT`: Azure DevOps Personal Access Token
- `AZURE_DEVOPS_ORGANIZATION`: Azure DevOps組織名
- `AZURE_DEVOPS_PROJECT`: プロジェクト名
- `AZURE_DEVOPS_REPOSITORY_ID`: リポジトリID

## Running

```bash
python main.py
```

## MCP Tools

### `get_pull_request`
プルリクエストの詳細情報を取得します。

**引数:**
- `id` (int): プルリクエストID

**戻り値:**
- プルリクエストの詳細情報（JSON）

### `get_pull_request_change_summary`
プルリクエストの変更概要（ファイルリストと変更タイプ）を取得します。コードの行単位の差分は含みません。

**引数:**
- `id` (int): プルリクエストID

**戻り値:**
- 変更ファイルのリストとメタデータ（JSON）

### `get_pull_request_unified_diff`
プルリクエストの差分をUnified Diff形式で取得します。

**引数:**
- `id` (int): プルリクエストID

**戻り値:**
- Unified Diff形式の文字列

**使用例:**
```
--- a/src/main.py
+++ b/src/main.py
@@ -10,7 +10,7 @@ def main():
     print("Hello, World!")
     
     # Process data
-    result = process_data(old_param)
+    result = process_data(new_param)
     
     return result
```

### `get_pull_request_comments`
プルリクエストのコメントスレッドを取得します。

**引数:**
- `id` (int): プルリクエストID

**戻り値:**
- コメントスレッドのリスト（JSON）

### `get_file_content`
リポジトリからファイル内容を取得します。

**引数:**
- `path` (str): ファイルパス
- `version` (str, optional): バージョン文字列（ブランチ名やコミット情報）

**戻り値:**
- ファイル内容（文字列）

## Testing

### ユニットテスト
```bash
python -m pytest tests/test_unified_diff_generator.py -v
```

### 統合テスト
```bash
python -m pytest tests/test_arbiter_integration.py -v
```

### 全テスト実行
```bash
python -m pytest tests/ -v
```

## アーキテクチャ

### UnifiedDiffGenerator
Unified Diff形式への変換を担当するクラス。外部依存を持たず、純粋な変換ロジックのみを実装。

### AzureReposClient
Azure DevOps APIとの通信を担当するクラス。

### AzureReposArbiter
複数のコンポーネントを統合し、MCPとしての結果を返すクラス。
