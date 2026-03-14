"""エンコーディング処理のテスト"""
import pytest
from client import AzureReposClient


class TestEncodingHandling:
    """AzureReposClientのエンコーディング処理に関するテスト"""
    
    def setup_method(self):
        """各テストの前に実行される初期化"""
        # PATは不要（_decode_contentメソッドのみテスト）
        self.client = AzureReposClient(pat="dummy_pat")
    
    def test_decode_utf8_content(self):
        """UTF-8エンコードされたコンテンツのデコード"""
        # 日本語を含むUTF-8テキスト
        original_text = "Hello, 世界！\nこれはテストです。"
        byte_content = original_text.encode('utf-8')
        
        decoded = self.client._decode_content(byte_content)
        
        assert decoded == original_text
        assert "世界" in decoded
        assert "テスト" in decoded
    
    def test_decode_shift_jis_content(self):
        """Shift-JIS (cp932)エンコードされたコンテンツのデコード"""
        # 日本語を含むShift-JISテキスト
        original_text = "// コメント：初期化処理\nvar name = \"テスト\";"
        byte_content = original_text.encode('cp932')
        
        decoded = self.client._decode_content(byte_content)
        
        assert decoded == original_text
        assert "コメント" in decoded
        assert "初期化処理" in decoded
        assert "テスト" in decoded
    
    def test_decode_empty_content(self):
        """空のコンテンツのデコード"""
        byte_content = b""
        
        decoded = self.client._decode_content(byte_content)
        
        assert decoded == ""
    
    def test_decode_ascii_content(self):
        """ASCII（英語のみ）コンテンツのデコード"""
        original_text = "public class TestClass {\n    // Comment\n}"
        byte_content = original_text.encode('ascii')
        
        decoded = self.client._decode_content(byte_content)
        
        assert decoded == original_text
    
    def test_decode_mixed_encoding_safe(self):
        """デコード不可能なバイト列でもエラーにならないことを確認"""
        # 不正なバイト列（どのエンコーディングでも正しくデコードできない）
        byte_content = b'\x80\x81\x82\x83\xff\xfe'
        
        # エラーなくデコードできることを確認（latin-1フォールバック）
        decoded = self.client._decode_content(byte_content)
        
        assert decoded is not None
        assert isinstance(decoded, str)
    
    def test_decode_c_sharp_file_with_japanese_comments(self):
        """C#ファイル（日本語コメント含む）のデコード"""
        # 実際のC#ファイルに近い内容
        csharp_code = """using System;

namespace TestNamespace
{
    /// <summary>
    /// 初期化処理を行うクラス
    /// </summary>
    public class Initializer
    {
        // コメント：セットアップ処理
        public void Initialize()
        {
            Console.WriteLine("初期化完了");
        }
    }
}"""
        
        # Shift-JISでエンコード（Windowsの日本語環境でよく使われる）
        byte_content = csharp_code.encode('cp932')
        
        decoded = self.client._decode_content(byte_content)
        
        assert "初期化処理" in decoded
        assert "セットアップ処理" in decoded
        assert "初期化完了" in decoded
        assert "class Initializer" in decoded
    
    def test_decode_preserves_line_breaks(self):
        """改行コードが保持されることを確認"""
        original_text = "Line 1\nLine 2\r\nLine 3\n"
        
        # UTF-8
        byte_content_utf8 = original_text.encode('utf-8')
        decoded_utf8 = self.client._decode_content(byte_content_utf8)
        assert decoded_utf8 == original_text
        
        # Shift-JIS
        byte_content_sjis = original_text.encode('cp932')
        decoded_sjis = self.client._decode_content(byte_content_sjis)
        assert decoded_sjis == original_text
    
    def test_decode_large_file_content(self):
        """大きなファイルのデコード"""
        # 大きなコンテンツを作成（約10KB）
        original_text = "日本語テキスト\n" * 500
        byte_content = original_text.encode('cp932')
        
        decoded = self.client._decode_content(byte_content)
        
        assert len(decoded) == len(original_text)
        assert decoded.count("日本語テキスト") == 500
    
    def test_decode_special_characters(self):
        """特殊文字を含むコンテンツのデコード"""
        # Shift-JISで問題になりやすい文字を含む
        original_text = "表示\\処理//構築―ソ能"
        byte_content = original_text.encode('cp932')
        
        decoded = self.client._decode_content(byte_content)
        
        assert "表示" in decoded
        assert "処理" in decoded
        assert "構築" in decoded
