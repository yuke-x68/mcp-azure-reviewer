from client import AzureReposClient
from typing import Dict, List
from unified_diff_generator import UnifiedDiffGenerator

"""
AzureReposClient からの応答を加工して、MCPとしての結果を返す。
"""
class AzureReposArbiter:

    def __init__(self, client: AzureReposClient, diff_generator: UnifiedDiffGenerator = None):
        """
        Args:
            client: AzureReposClientのインスタンス
            diff_generator: UnifiedDiffGeneratorのインスタンス（省略時は新規作成）
        """
        self.client = client
        self.diff_generator = diff_generator or UnifiedDiffGenerator()
    
    def _normalize_change_type(self, change_type: str, source_server_item: str = None) -> str:
        """Azure DevOpsのchangeTypeを標準ステータスに変換
        
        Args:
            change_type: Azure DevOpsのchangeType（例: "edit", "add", "delete"）
            source_server_item: sourceServerItemフィールドの値（リネームの場合のみ存在）
            
        Returns:
            標準化されたステータス: "added", "deleted", "modified", "renamed"
            
        Note:
            changeTypeに"rename"が含まれていても、sourceServerItemがない場合は
            "modified"として扱います。これは、ファイルパスの変更を伴わない内部変更
            （例：namespace変更）をリネームと誤認しないためです。
        """
        change_type_lower = str(change_type).lower()
        
        if "add" in change_type_lower:
            return "added"
        elif "delete" in change_type_lower:
            return "deleted"
        elif ("rename" in change_type_lower or "source_rename" in change_type_lower) and source_server_item:
            # 実際にファイルパスが変更された場合のみ"renamed"とする
            return "renamed"
        elif "edit" in change_type_lower:
            return "modified"
        else:
            return "modified"  # デフォルト

    def get_pull_request(self, organization: str, project: str, repo_id: str, pr_id: int) -> Dict:
        """プルリクエストの詳細情報を取得し、必要な項目のみを抽出
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            pr_id: プルリクエストID
            
        Returns:
            抽出されたプルリクエスト情報の辞書
        """
        result = self.client.get_pull_request(organization, project, repo_id, pr_id)
        
        # 必要なフィールドのリスト
        # ※ AIの混乱を防ぐため、マージ済みと誤認させる日付情報や状態情報を除外し、
        #    PRの内容を理解するのに必要な情報のみに絞ります。
        key_map = {
            'description': ['description'],
            'pull_request_id': ['pull_request_id', 'pullRequestId'],
            'source_ref_name': ['source_ref_name', 'sourceRefName'],
            'target_ref_name': ['target_ref_name', 'targetRefName'],
            'title': ['title'],
            'url': ['url']
        }
        
        extracted = {}
        for target_key, possible_keys in key_map.items():
            for pk in possible_keys:
                if pk in result:
                    extracted[target_key] = result[pk]
                    break
        
        # リポジトリ名のみ追加
        repo_data = result.get('repository', {})
        extracted['repository_name'] = repo_data.get('name')
        
        return extracted

    def get_pull_request_change_summary(self, organization: str, project: str, repo_id: str, pr_id: int) -> Dict:
        """プルリクエストの変更概要（ファイル一覧と変更タイプ）を取得
        
        このメソッドは、PRに含まれるファイルの一覧と、それぞれの変更内容（追加、修正、削除など）
        のメタデータを返します。コードの行単位の差分（Unified Diff）は含みません。
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            pr_id: プルリクエストID
            
        Returns:
            フィルタリングされた変更概要情報の辞書
            
        Note:
            - フォルダ（tree）を除外します
            - .metaファイルを除外します
        """
        result = self.client.get_pull_request_diff(organization, project, repo_id, pr_id)
        
        # Filter out folders (trees) and .meta files
        if "changes" in result:
            filtered_changes = []
            renamed_files = {}  # リネームされたファイルを追跡: {新しいパス: 古いパス}
            
            # まず、リネームされたファイルを特定
            for change in result["changes"]:
                item = change.get("item", {})
                path = item.get("path", "")
                change_type_raw = change.get("changeType") or change.get("change_type") or ""
                change_type = str(change_type_raw).lower()
                
                # リネームの場合、元のパスを記録
                # sourceServerItemまたはoriginalPathから取得
                if "rename" in change_type or "source_rename" in change_type:
                    original_path = (change.get("sourceServerItem") or 
                                   change.get("source_server_item") or
                                   change.get("originalPath") or 
                                   change.get("original_path"))
                    if original_path:
                        renamed_files[path] = original_path
            
            for change in result["changes"]:
                item = change.get("item", {})
                path = item.get("path", "")
                
                # change_typeを文字列として取得し、結果を正規化
                change_type_raw = change.get("changeType") or change.get("change_type") or ""
                change_type = str(change_type_raw).lower()
                
                # git_object_typeはgitObjectTypeまたはgit_object_typeで返される可能性がある
                git_object_type = item.get("gitObjectType") or item.get("git_object_type", "")
                is_folder = item.get("isFolder", False)
                
                # フォルダ（tree）をスキップ
                if git_object_type == "tree" or is_folder:
                    continue
                
                # .metaファイルをスキップ
                if path.endswith(".meta"):
                    continue
                
                # sourceServerItemを取得してリネーム判定に使用
                source_server_item = (change.get("sourceServerItem") or 
                                     change.get("source_server_item"))
                
                # 標準化されたステータスを取得
                status = self._normalize_change_type(change_type, source_server_item)
                
                # リネームの古い場所のエントリ（status: "deleted"）を除外
                # リネームされたファイルの古いパスとして記録されている場合はスキップ
                if status == "deleted" and path in renamed_files.values():
                    continue
                
                # ファイルの存在状態を判定
                exists_in_base = status in ["modified", "deleted", "renamed"]
                exists_in_head = status in ["modified", "added", "renamed"]
                
                # AIが理解しやすいように変更内容を整理
                filtered_change = {
                    "path": path,
                    "change_type": change_type,  # 元のタイプを保持
                    "status": status,  # 標準化されたステータス
                    "exists_in_base": exists_in_base,  # baseブランチに存在するか
                    "exists_in_head": exists_in_head,  # headブランチに存在するか
                    "item": item
                }
                
                # 元のパスがある場合（リネーム等）はそれも追加
                # sourceServerItem、originalPath、original_pathの順に確認
                original_path = (change.get("sourceServerItem") or 
                               change.get("source_server_item") or
                               change.get("originalPath") or 
                               change.get("original_path"))
                if original_path:
                    filtered_change["original_path"] = original_path
                    filtered_change["previous_filename"] = original_path  # AIが分かりやすい名前でも追加
                
                filtered_changes.append(filtered_change)
            
            result["changes"] = filtered_changes
            
            # デバッグ情報（必要に応じてコメントを外す）
            # filtered_count = len(filtered_changes)
            # if original_count != filtered_count:
            #     print(f"[DEBUG] Filtered {original_count - filtered_count} items (folders/meta files) from diff")

        result.pop("change_counts", None)
        return result

    def get_comments(self, organization: str, project: str, repo_id: str, pr_id: int) -> List[Dict]:
        """プルリクエストのコメントを取得し、メタデータを加工
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            pr_id: プルリクエストID
            
        Returns:
            加工されたコメントスレッドのリスト
        """
        result = self.client.get_comments(organization, project, repo_id, pr_id)

        # 安全にキーを取得し、存在しない場合はNone（またはデフォルト値）を返す
        expected_keys = [
            'comments', 'id', 'last_updated_date', 'published_date',
            'thread_context', 'pull_request_thread_context'
        ]
        
        processed_comments = []
        for thread in result:
            # スレッド内のコメントをフィルタリング
            filtered_comments = []
            for comment in thread.get('comments', []):
                # システム生成のコメント（ブランチ更新通知など）を除外
                if comment.get('commentType') == 'system' or comment.get('comment_type') == 'system':
                    continue
                filtered_comments.append(comment)
            
            # コメントがないスレッドはスキップ
            if not filtered_comments:
                continue
                
            processed_thread = {key: thread.get(key) for key in expected_keys}
            # フィルタリングされたコメントをセット
            processed_thread['comments'] = filtered_comments
            processed_comments.append(processed_thread)
            
        return processed_comments

    def get_file_content(self, organization: str, project: str, repo_id: str, path: str, version: str = None) -> str:
        """ファイル内容を取得
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            path: ファイルパス
            version: バージョン情報（省略時はデフォルト）
            
        Returns:
            ファイル内容の文字列
        """
        result = self.client.get_file_content(organization, project, repo_id, path, version)
        return result

    def get_pull_request_unified_diff(self, organization: str, project: str, repo_id: str, pr_id: int) -> str:
        """プルリクエストの全ファイルのUnified Diffを取得
        
        Args:
            organization: Azure DevOps組織名
            project: プロジェクト名
            repo_id: リポジトリID
            pr_id: プルリクエストID
        
        Returns:
            全ファイルのUnified Diffを結合した文字列
            
        Note:
            - フォルダ（git_object_type == "tree"）は除外されます
            - .metaファイルは除外されます
            - 差分がないファイルは含まれません
        """
        # PR情報と差分情報を取得
        pr = self.client.get_pull_request(organization, project, repo_id, pr_id)
        diff_data = self.client.get_pull_request_diff(organization, project, repo_id, pr_id)
        
        # コミットIDを取得
        # as_dict()の結果なのでsnake_caseのはずだが、念のため両方チェック
        source_commit = pr.get("last_merge_source_commit", {}).get("commit_id") or \
                        pr.get("lastMergeSourceCommit", {}).get("commitId")
        target_commit = pr.get("last_merge_target_commit", {}).get("commit_id") or \
                        pr.get("lastMergeTargetCommit", {}).get("commitId")
        
        if not source_commit or not target_commit:
            return "# Error: Could not determine source/target commits for diff."
        
        # 変更ファイルのリストを取得
        changes = diff_data.get("changes", [])
        
        unified_diffs = []
        
        for change in changes:
            item = change.get("item", {})
            path = item.get("path", "")
            
            # change_typeはchangeTypeまたはchange_typeで返される可能性がある
            change_type_raw = change.get("changeType") or change.get("change_type") or ""
            # 文字列に変換（列挙型の場合があるため）
            change_type = str(change_type_raw).lower()
            
            # git_object_typeはgitObjectTypeまたはgit_object_typeで返される可能性がある
            git_object_type = item.get("gitObjectType") or item.get("git_object_type", "")
            is_folder = item.get("isFolder", False)
            
            # フォルダと.metaファイルをスキップ
            if git_object_type == "tree" or is_folder:
                continue
            if path.endswith(".meta"):
                continue
            
            # 変更前後のファイル内容を取得
            original_content = ""
            modified_content = ""
            
            # 元のパス（リネーム用）
            original_path = change.get("originalPath") or change.get("original_path") or path
            
            # 削除、編集、リネームの場合は元の内容が必要
            if any(t in change_type for t in ["edit", "delete", "rename", "source_rename"]):
                original_content = self.client.get_file_content_at_commit(
                    organization, project, repo_id, original_path, target_commit
                )
            
            # 追加、編集、リネームの場合は変更後の内容が必要
            if any(t in change_type for t in ["edit", "add", "rename", "target_rename"]):
                modified_content = self.client.get_file_content_at_commit(
                    organization, project, repo_id, path, source_commit
                )
            
            # Unified Diffを生成
            file_diff = self.diff_generator.generate_file_diff(
                original_content=original_content,
                modified_content=modified_content,
                file_path=path
            )
            
            if file_diff:  # 差分がある場合のみ追加
                unified_diffs.append(file_diff)
        
        # 全ファイルのdiffを結合
        return "\n".join(unified_diffs)
