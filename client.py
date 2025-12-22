from typing import List, Dict
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.git.models import GitBaseVersionDescriptor, GitTargetVersionDescriptor, GitVersionDescriptor

class AzureReposClient:
    def __init__(self, pat: str):
        """AzureReposClientを初期化
        
        Args:
            pat: Azure DevOpsのPersonal Access Token (PAT)
        """
        self.pat = pat
        self.creds = BasicAuthentication("", pat)
        self._clients = {}

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
        
        content = "".join([chunk.decode("utf-8") for chunk in content_generator])
        return content

    def get_file_content_at_commit(
        self,
        organization: str,
        project: str,
        repo_id: str,
        path: str,
        commit_id: str
    ) -> str:
        """特定のコミットでのファイル内容を取得
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            path: ファイルパス
            commit_id: コミットID
        
        Returns:
            ファイル内容（ファイルが存在しない場合は空文字列）
            
        Note:
            ファイルが存在しない場合（新規追加または削除されたファイル）は
            空文字列を返します。これにより、呼び出し側で新規/削除の判定が可能です。
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
            
            content = "".join([chunk.decode("utf-8") for chunk in content_generator])
            return content
            
        except Exception as e:
            # ファイルが存在しない場合（404など）は空文字列を返す
            # これは新規追加または削除されたファイルの場合に発生する
            return ""
