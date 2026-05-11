import json
import logging
from openai import OpenAI

from backend.src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


def build_prompt(stocks: list) -> str:
    """Build screening prompt from stock fundamentals data."""
    lines = [
        "你是一个专业的A股量化分析师。请基于以下股票的基本面数据，",
        "从多维度（估值、成长性、盈利能力、财务健康、技术面）进行综合分析，",
        "选出你认为最具投资价值的3-5只股票。返回JSON格式。",
        "",
        "股票数据如下：",
    ]
    for s in stocks:
        lines.append(
            f"- {s.get('stock_code', '')} {s.get('stock_name', '')}: "
            f"PE={s.get('pe_ratio', 'N/A')}, PB={s.get('pb_ratio', 'N/A')}, "
            f"市值={s.get('market_cap', 'N/A')}亿, EPS={s.get('eps', 'N/A')}"
        )

    lines.append("")
    lines.append(
        '请返回JSON: {"recommendations": [{"stock_code": "...", "stock_name": "...", '
        '"reason": "...", "score": 0-100}]}'
    )
    return "\n".join(lines)


def parse_response(content: str) -> list:
    """Parse AI response JSON into list of recommendations."""
    try:
        data = json.loads(content)
        return data.get("recommendations", [])
    except (json.JSONDecodeError, TypeError):
        # Try to extract JSON from markdown code blocks
        try:
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                return json.loads(content[start:end]).get("recommendations", [])
            if "```" in content:
                start = content.index("```") + 3
                end = content.index("```", start)
                return json.loads(content[start:end]).get("recommendations", [])
        except (ValueError, json.JSONDecodeError):
            pass
        logger.warning(f"Failed to parse AI response: {content[:200]}")
        return []


def call_deepseek(stocks: list) -> list:
    """Call DeepSeek API and return parsed recommendations."""
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set; returning empty list")
        return []

    prompt = build_prompt(stocks)
    try:
        response = _get_client().chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        content = response.choices[0].message.content
        return parse_response(content)
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return []
