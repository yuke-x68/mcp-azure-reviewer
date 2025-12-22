import difflib
from typing import Optional


class UnifiedDiffGenerator:
    """Unified Diff形式への変換を担当するクラス
    
    このクラスはファイル内容の差分をUnified Diff形式に変換します。
    Azure DevOps APIやその他の外部依存を持たず、純粋な変換ロジックのみを担当します。
    """
    
    def __init__(self, context_lines: int = 3):
        """
        Args:
            context_lines: 変更箇所の前後に含めるコンテキスト行数（デフォルト: 3）
        """
        self.context_lines = context_lines
    
    def generate_file_diff(
        self,
        original_content: str,
        modified_content: str,
        file_path: str,
        original_label: str = "a",
        modified_label: str = "b"
    ) -> str:
        """1ファイルのUnified Diffを生成
        
        Args:
            original_content: 変更前のファイル内容（空文字列の場合は新規ファイル）
            modified_content: 変更後のファイル内容（空文字列の場合は削除ファイル）
            file_path: ファイルパス（先頭の/は除く）
            original_label: 変更前のラベル（デフォルト: "a"）
            modified_label: 変更後のラベル（デフォルト: "b"）
        
        Returns:
            Unified Diff形式の文字列
            
        Example:
            >>> generator = UnifiedDiffGenerator()
            >>> original = "line1\\nline2\\nline3\\n"
            >>> modified = "line1\\nline2 modified\\nline3\\n"
            >>> diff = generator.generate_file_diff(original, modified, "test.py")
            >>> print(diff)
            --- a/test.py
            +++ b/test.py
            @@ -1,3 +1,3 @@
             line1
            -line2
            +line2 modified
             line3
        """
        # ファイルパスの正規化（先頭の/を除去）
        normalized_path = file_path
        if normalized_path.startswith('/'):
            normalized_path = normalized_path[1:]
        
        # 行単位に分割（改行を保持）
        original_lines = original_content.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)
        
        # 改行がない場合の処理
        if original_content and not original_lines:
            original_lines = [original_content]
        if modified_content and not modified_lines:
            modified_lines = [modified_content]
        
        # difflib.unified_diffを使用して差分を生成
        diff_lines = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"{original_label}/{normalized_path}",
            tofile=f"{modified_label}/{normalized_path}",
            n=self.context_lines,
            lineterm=''
        )
        
        # 結果を結合
        result = '\n'.join(diff_lines)
        
        # 差分がない場合は空文字列を返す
        if not result:
            return ""
        
        return result + '\n'
