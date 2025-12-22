import pytest
from unified_diff_generator import UnifiedDiffGenerator


class TestUnifiedDiffGenerator:
    """UnifiedDiffGeneratorのユニットテスト"""
    
    def setup_method(self):
        """各テストの前に実行される初期化"""
        self.generator = UnifiedDiffGenerator()
    
    def test_basic_modification(self):
        """基本的な変更のテスト"""
        original = "line1\nline2\nline3\n"
        modified = "line1\nline2 modified\nline3\n"
        
        diff = self.generator.generate_file_diff(original, modified, "test.py")
        
        assert diff != ""
        assert "--- a/test.py" in diff
        assert "+++ b/test.py" in diff
        assert "-line2" in diff
        assert "+line2 modified" in diff
    
    def test_addition_only(self):
        """新規ファイルの追加のテスト"""
        original = ""
        modified = "new line 1\nnew line 2\n"
        
        diff = self.generator.generate_file_diff(original, modified, "new_file.py")
        
        assert diff != ""
        assert "--- a/new_file.py" in diff
        assert "+++ b/new_file.py" in diff
        assert "+new line 1" in diff
        assert "+new line 2" in diff
    
    def test_deletion_only(self):
        """ファイル削除のテスト"""
        original = "line to delete 1\nline to delete 2\n"
        modified = ""
        
        diff = self.generator.generate_file_diff(original, modified, "deleted_file.py")
        
        assert diff != ""
        assert "--- a/deleted_file.py" in diff
        assert "+++ b/deleted_file.py" in diff
        assert "-line to delete 1" in diff
        assert "-line to delete 2" in diff
    
    def test_no_changes(self):
        """変更がない場合のテスト"""
        content = "line1\nline2\nline3\n"
        
        diff = self.generator.generate_file_diff(content, content, "unchanged.py")
        
        assert diff == ""
    
    def test_empty_files(self):
        """両方空ファイルの場合のテスト"""
        diff = self.generator.generate_file_diff("", "", "empty.py")
        
        assert diff == ""
    
    def test_multiple_hunks(self):
        """複数の変更ブロック（hunks）のテスト"""
        original = "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\n"
        modified = "line1\nline2 modified\nline3\nline4\nline5\nline6\nline7\nline8 modified\nline9\nline10\n"
        
        diff = self.generator.generate_file_diff(original, modified, "multi_hunk.py")
        
        assert diff != ""
        assert "-line2" in diff
        assert "+line2 modified" in diff
        assert "-line8" in diff
        assert "+line8 modified" in diff
    
    def test_file_path_normalization(self):
        """ファイルパスの正規化のテスト（先頭の/を除去）"""
        original = "line1\n"
        modified = "line1 modified\n"
        
        diff = self.generator.generate_file_diff(original, modified, "/path/to/file.py")
        
        assert "--- a/path/to/file.py" in diff
        assert "+++ b/path/to/file.py" in diff
    
    def test_custom_labels(self):
        """カスタムラベルのテスト"""
        original = "line1\n"
        modified = "line1 modified\n"
        
        diff = self.generator.generate_file_diff(
            original, 
            modified, 
            "test.py",
            original_label="original",
            modified_label="modified"
        )
        
        assert "--- original/test.py" in diff
        assert "+++ modified/test.py" in diff
    
    def test_custom_context_lines(self):
        """カスタムコンテキスト行数のテスト"""
        generator = UnifiedDiffGenerator(context_lines=1)
        
        original = "line1\nline2\nline3\nline4\nline5\n"
        modified = "line1\nline2\nline3 modified\nline4\nline5\n"
        
        diff = generator.generate_file_diff(original, modified, "test.py")
        
        assert diff != ""
        # コンテキスト行数が1なので、変更行の前後1行のみが含まれる
        assert "line3" in diff
    
    def test_no_trailing_newline(self):
        """末尾に改行がないファイルのテスト"""
        original = "line1\nline2"
        modified = "line1\nline2 modified"
        
        diff = self.generator.generate_file_diff(original, modified, "no_newline.py")
        
        assert diff != ""
        assert "--- a/no_newline.py" in diff
        assert "+++ b/no_newline.py" in diff
    
    def test_single_line_file(self):
        """1行のみのファイルのテスト"""
        original = "single line"
        modified = "single line modified"
        
        diff = self.generator.generate_file_diff(original, modified, "single.py")
        
        assert diff != ""
        assert "-single line" in diff
        assert "+single line modified" in diff
