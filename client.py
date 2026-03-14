from typing import List, Dict
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.git.models import GitBaseVersionDescriptor, GitTargetVersionDescriptor, GitVersionDescriptor
import chardet

class AzureReposClient:
    def __init__(self, pat: str):
        """AzureReposClientを初期化
        
        Args:
            pat: Azure DevOpsのPersonal Access Token (PAT)
        """
        self.pat = pat
        self.creds = BasicAuthentication("", pat)
        self._clients = {}
    
    def _decode_content(self, byte_content: bytes) -> str:
        """バイトデータを適切なエンコーディングでデコード
        
        Args:
            byte_content: デコードするバイトデータ
            
        Returns:
            デコードされた文字列
            
        Note:
            以下の順序でエンコーディングを試行します：
            1. chardetによる自動検出
            2. UTF-8
            3. Shift-JIS (cp932)
            4. Latin-1 (フォールバック、常に成功)
        """
        # 空データの場合
        if not byte_content:
            return ""
        
        # chardetで自動検出
        detected = chardet.detect(byte_content)
        if detected and detected.get('encoding'):
            try:
                return byte_content.decode(detected['encoding'])
            except (UnicodeDecodeError, LookupError):
                pass  # 次のエンコーディングを試す
        
        # UTF-8を試す
        try:
            return byte_content.decode('utf-8')
        except UnicodeDecodeError:
            pass
        
        # Shift-JIS (cp932)を試す
        try:
            return byte_content.decode('cp932')
        except UnicodeDecodeError:
            pass
        
        # 最終フォールバック: latin-1は常に成功する
        # （全バイト値が有効な文字にマップされるため）
        return byte_content.decode('latin-1', errors='replace')

    def _get_git_client(self, organization: str):
        """組織ごとのGitクライアントを取得または作成
        
        Args:
            organization: Azure DevOps組織名
            
        Returns:
            Azure DevOps Gitクライアント
        """
        if organization not in self._clients:
            organization_url = f"https://dev.azure.com/{organization}"
            connection = Connection(base_url=organization_url, creds=self.creds)
            self._clients[organization] = connection.clients.get_git_client()
        return self._clients[organization]

    def get_pull_request(self, organization: str, project: str, repo_id: str, pr_id: int) -> Dict:
        """プルリクエストの詳細情報を取得
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            pr_id: プルリクエストID
            
        Returns:
            プルリクエスト情報の辞書
        """
        client = self._get_git_client(organization)
        pr = client.get_pull_request(repo_id, pr_id, project=project)
        return pr.as_dict()

    def get_pull_request_diff(self, organization: str, project: str, repo_id: str, pr_id: int) -> Dict:
        """プルリクエストのコミット差分情報を取得
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            pr_id: プルリクエストID
            
        Returns:
            コミット差分情報の辞書
        """
        # Get PR details to find the source and target commits
        pr = self.get_pull_request(organization, project, repo_id, pr_id)
        
        source_commit = pr.get("last_merge_source_commit", {}).get("commit_id")
        target_commit = pr.get("last_merge_target_commit", {}).get("commit_id")

        if not source_commit or not target_commit:
             return {"error": "Could not determine source/target commits for diff."}

        client = self._get_git_client(organization)

        base_version = GitBaseVersionDescriptor(
            base_version=target_commit,
            base_version_type="commit"
        )
        target_version = GitTargetVersionDescriptor(
            target_version=source_commit,
            target_version_type="commit"
        )

        diffs = client.get_commit_diffs(
            repository_id=repo_id,
            project=project,
            diff_common_commit=True,
            base_version_descriptor=base_version,
            target_version_descriptor=target_version
        )
        
        data = diffs.as_dict()

        return data

    def get_comments(self, organization: str, project: str, repo_id: str, pr_id: int) -> List[Dict]:
        """プルリクエストのコメントスレッド一覧を取得
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            pr_id: プルリクエストID
            
        Returns:
            コメントスレッドの辞書のリスト
        """
        client = self._get_git_client(organization)
        threads = client.get_threads(repo_id, pr_id, project=project)
        return [t.as_dict() for t in threads]

    def get_file_content(self, organization: str, project: str, repo_id: str, path: str, version: str = None) -> str:
        """リポジトリのファイル内容を取得
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            path: ファイルパス
            version: バージョン情報（ブランチ名、コミットIDなど。省略時はデフォルトブランチ）
            
        Returns:
            ファイル内容の文字列
        """
        client = self._get_git_client(organization)
        
        version_descriptor = GitVersionDescriptor(version=version) if version else None

        content_generator = client.get_item_content(
            repository_id=repo_id,
            path=path,
            project=project,
            version_descriptor=version_descriptor
        )
        
        # バイトデータを結合
        byte_content = b"".join([chunk for chunk in content_generator])
        
        # エンコーディングを自動検出してデコード
        content = self._decode_content(byte_content)
        return content

    def get_file_content_at_commit(
        self,
        organization: str,
        project: str,
        repo_id: str,
        path: str,
        commit_id: str
    ) -> tuple[str, str | None]:
        """特定のコミットでのファイル内容を取得
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            path: ファイルパス
            commit_id: コミットID
        
        Returns:
            (ファイル内容, エラーメッセージ)のタプル
            - 成功時: (content, None)
            - ファイル不在時: ("", None)  # 404エラーの場合
            - その他のエラー時: ("", error_message)  # 取得失敗
            
        Note:
            ファイルが存在しない場合（404）とその他のエラーを区別するため、
            戻り値としてエラーメッセージも返します。
        """
        client = self._get_git_client(organization)
        
        version_descriptor = GitVersionDescriptor(
            version=commit_id,
            version_type="commit"
        )
        
        try:
            content_generator = client.get_item_content(
                repository_id=repo_id,
                path=path,
                project=project,
                version_descriptor=version_descriptor
            )
            
            # バイトデータを結合
            byte_content = b"".join([chunk for chunk in content_generator])
            
            # エンコーディングを自動検出してデコード
            content = self._decode_content(byte_content)
            return content, None
            
        except Exception as e:
            # 404エラー（ファイルが存在しない）の場合とその他のエラーを区別
            error_message = str(e)
            if "404" in error_message or "does not exist" in error_message.lower():
                # ファイルが存在しない場合（新規追加または削除されたファイル）
                return "", None
            else:
                # その他のエラー（ネットワークエラー、権限エラーなど）
                return "", f"Error fetching file: {error_message}"

    def get_file_commit_history(
        self,
        organization: str,
        project: str,
        repo_id: str,
        path: str,
        since: str = None
    ) -> List[Dict]:
        """特定ファイルのコミット履歴を取得

        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            path: ファイルパス
            since: 開始日（ISO 8601形式、例: "2025-09-15"）。省略時は制限なし

        Returns:
            コミット情報の辞書のリスト
        """
        from azure.devops.v7_1.git.models import GitQueryCommitsCriteria

        client = self._get_git_client(organization)

        search_criteria = GitQueryCommitsCriteria(
            item_path=path,
            from_date=since
        )

        commits = client.get_commits(
            repository_id=repo_id,
            search_criteria=search_criteria,
            project=project
        )

        return [c.as_dict() for c in commits]
