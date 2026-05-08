import json
from unittest.mock import MagicMock, patch

import pytest


class TestAIScreening:
    """Unit tests for DeepSeek AI screening client."""

    def test_build_prompt_includes_stock_data(self):
        """build_prompt() should include stock fundamentals and indicators in the prompt."""
        from backend.src.services.ai_screening import build_prompt

        stocks = [
            {"stock_code": "000001.SZ", "stock_name": "平安银行", "pe_ratio": 5.2, "pb_ratio": 0.7},
        ]
        prompt = build_prompt(stocks)

        assert "000001.SZ" in prompt
        assert "平安银行" in prompt

    def test_build_prompt_includes_instruction(self):
        """build_prompt() should include screening instructions."""
        from backend.src.services.ai_screening import build_prompt

        prompt = build_prompt([])
        assert len(prompt) > 0

    def test_parse_response_extracts_recommendations(self):
        """parse_response() should extract stock recommendations from AI JSON response."""
        from backend.src.services.ai_screening import parse_response

        ai_output = json.dumps({
            "recommendations": [
                {"stock_code": "000001.SZ", "reason": "低估值蓝筹", "score": 85},
            ]
        })
        result = parse_response(ai_output)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["stock_code"] == "000001.SZ"
        assert "score" in result[0]

    def test_parse_response_handles_malformed_json(self):
        """parse_response() should handle malformed AI output gracefully."""
        from backend.src.services.ai_screening import parse_response

        result = parse_response("not valid json {{{")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_call_deepseek_returns_parsed_results(self):
        """call_deepseek() should call API and return parsed recommendations."""
        from backend.src.services.ai_screening import call_deepseek

        stocks = [{"stock_code": "000001.SZ", "stock_name": "平安银行", "pe_ratio": 5.2}]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "recommendations": [{"stock_code": "000001.SZ", "reason": "测试", "score": 80}]
            })))
        ]

        with patch('openai.OpenAI') as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response
            result = call_deepseek(stocks)

        assert isinstance(result, list)
