"""
Tests for text utilities.
"""

import pytest

from src.utils.text import clean_llm_output, _PREFIXES_TO_STRIP


class TestCleanLlmOutput:
    """Tests for clean_llm_output function."""

    def test_clean_no_changes_needed(self):
        """Tests clean output that needs no changes."""
        text = "This is a clean output"
        
        result = clean_llm_output(text)
        
        assert result == text

    def test_clean_strips_whitespace(self):
        """Tests whitespace stripping."""
        text = "   \n\t  trimmed text  \t\n   "
        
        result = clean_llm_output(text)
        
        assert result == "trimmed text"

    def test_clean_remove_output_prefix(self):
        """Tests removal of 'Output:' prefix."""
        text = "Output: cleaned text"
        
        result = clean_llm_output(text)
        
        assert result == "cleaned text"

    def test_clean_remove_result_prefix(self):
        """Tests removal of 'Result:' prefix."""
        text = "Result: cleaned text"
        
        result = clean_llm_output(text)
        
        assert result == "cleaned text"

    def test_clean_remove_russian_prefixs(self):
        """Tests removal of Russian prefixes."""
        text1 = "Выход: очищенный текст"
        text2 = "Ответ: очищенный текст"
        
        result1 = clean_llm_output(text1)
        result2 = clean_llm_output(text2)
        
        assert result1 == "очищенный текст"
        assert result2 == "очищенный текст"

    def test_clean_remove_markdown_code_block(self):
        """Tests removal of markdown code blocks."""
        text = "```python\nsome code\n```"
        
        result = clean_llm_output(text)
        
        # Function only strips trailing ``` and leading ```json
        assert result == "python\nsome code"

    def test_clean_remove_json_markdown(self):
        """Tests removal of JSON markdown blocks."""
        text = "```json\n{\"key\": \"value\"}\n```"
        
        result = clean_llm_output(text)
        
        assert result == "{\"key\": \"value\"}"

    def test_clean_remove_trailing_backticks(self):
        """Tests removal of trailing backticks."""
        text = "cleaned text```"
        
        result = clean_llm_output(text)
        
        assert result == "cleaned text"

    def test_clean_remove_quotes(self):
        """Tests removal of surrounding quotes."""
        text = '"quoted text"'
        
        result = clean_llm_output(text)
        
        assert result == "quoted text"

    def test_clean_combined_issues(self):
        """Tests combined cleaning issues."""
        text = '  Output: "result text```"  '
        
        result = clean_llm_output(text)
        
        # Function strips whitespace, removes Output: prefix
        # Then removes surrounding quotes if present
        assert result == 'result text```'

    def test_clean_empty_string(self):
        """Tests empty string."""
        text = ""
        
        result = clean_llm_output(text)
        
        assert result == ""

    def test_clean_only_prefix(self):
        """Tests string with only prefix."""
        text = "Output:"
        
        result = clean_llm_output(text)
        
        assert result == ""

    def test_clean_multiple_prefixes(self):
        """Tests multiple prefixes (all matching prefixes are removed in order)."""
        text = "Result: Output: text"
        
        result = clean_llm_output(text)
        
        # Function removes all matching prefixes in sequence
        assert result == "text"

    def test_clean_single_quote_not_removed(self):
        """Tests that single quote is not removed."""
        text = "text with 'single quote'"
        
        result = clean_llm_output(text)
        
        assert result == text

    def test_clean_unicode_content(self):
        """Tests unicode content."""
        text = 'Результат: "Привет мир 🌍"'
        
        result = clean_llm_output(text)
        
        # "Результат:" is not in the prefixes list, only "Result:" is
        # But quotes should be stripped
        assert result == 'Результат: "Привет мир 🌍"'

    def test_clean_prefixes_list_defined(self):
        """Tests that prefixes list is properly defined."""
        assert isinstance(_PREFIXES_TO_STRIP, list)
        assert len(_PREFIXES_TO_STRIP) > 0
        assert "Output:" in _PREFIXES_TO_STRIP
        assert "Result:" in _PREFIXES_TO_STRIP
        assert "Выход:" in _PREFIXES_TO_STRIP
        assert "Ответ:" in _PREFIXES_TO_STRIP
