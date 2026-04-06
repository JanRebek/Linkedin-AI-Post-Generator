"""
LinkedIn Post Generator — Multi-Agent Pipeline
Stages: discover → summarize → fact-check → write
"""

from __future__ import annotations

import json
import re
import time
from typing import Callable

import anthropic

# ---------------------------------------------------------------------------
# Model & tool constants
# ---------------------------------------------------------------------------
MODEL = "claude-sonnet-4-6"
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}

# ---------------------------------------------------------------------------
# Style prompts
# ---------------------------------------------------------------------------
STYLE_INSTRUCTIONS: dict[str, str] = {
    "🧠 Thought Leader": (
        "Write with authority and conviction. Make bold, opinionated statements. "
        "State your POV in the first sentence. Use short punchy paragraphs. "
        "Challenge conventional thinking. Sound like someone who has deep expertise and isn't afraid to say something controversial."
    ),
    "📚 Educator": (
        "Write to inform and teach. Break complex ideas into simple, digestible chunks. "
        "Use analogies and real-world comparisons. Structure the post so readers learn something concrete. "
        "Be encouraging and approachable — assume the reader is smart but new to the topic."
    ),
    "🛠️ Practitioner": (
        "Write from a practitioner's perspective — someone who works with AI tools daily. "
        "Focus on real-world implications: what does this mean for actual teams and workflows? "
        "Be specific and actionable. Share what you would actually do with this knowledge."
    ),
    "⚡ Contrarian": (
        "Push back on the prevailing narrative. Ask hard questions. Point out what everyone else is missing. "
        "Be nuanced — not cynical for its own sake, but genuinely skeptical. "
        "Challenge assumptions. The best contrarian posts make people stop and reconsider something they took for granted."
    ),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_with_status(
    client: anthropic.Anthropic,
    stage: str,
    message: str,
    messages: list[dict],
    tools: list[dict] | None,
    status_callback: Callable | None,
    max_tokens: int = 2048,
) -> str:
    """Make an Anthropic API call, handle tool_use loops, return final text."""
    if status_callback:
        status_callback(stage, message)

    kwargs: dict = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    response = client.messages.create(**kwargs)

    # Agentic loop: keep going while the model wants to use tools
    while response.stop_reason == "tool_use":
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        tool_results = []
        for tu in tool_uses:
            # web_search results come back as content blocks automatically;
            # for other tools we'd handle here, but web_search is handled by the API
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps({"error": "Tool not supported in this context"}),
            })

        messages = messages + [
            {"role": "assistant", "content": response.content},
            {"role": "user", "content": tool_results},
        ]
        response = client.messages.create(**kwargs | {"messages": messages})

    # Extract text from final response
    text_parts = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(text_parts).strip()


def _extract_json(text: str, fallback: dict) -> dict:
    """Try to parse JSON from a text block that may have markdown fences."""
    # Try to find a JSON block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try raw JSON anywhere in the string
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return fallback


# ---------------------------------------------------------------------------
# Stage 1: Discovery
# ---------------------------------------------------------------------------

def _stage_discovery(
    client: anthropic.Anthropic,
    topic: str,
    sources: list[str],
    creators: list[str],
    youtube_api_key: str | None,
    status_callback: Callable | None,
) -> str:
    """Search the web for relevant AI content and return a context blob."""
    sources_str = ", ".join(sources) if sources else "the web"
    creators_str = (
        f" Pay special attention to posts or statements by: {', '.join(creators)}."
        if creators
        else ""
    )

    prompt = f"""You are a research assistant helping create a LinkedIn post about AI.

Topic: {topic}
Sources to search: {sources_str}
{creators_str}

Please search the web to find:
1. The most relevant, recent content about this topic (last 7 days preferred)
2. Key facts, statistics, or announcements
3. Interesting perspectives or debates in the AI community
4. Any viral or widely-shared content on this topic

Search multiple angles — news articles, GitHub repos, Reddit threads, YouTube videos where relevant.
Compile everything into a rich research summary with:
- Main findings (3–5 bullet points)
- Key facts and numbers
- Interesting quotes or takes
- URLs of the best sources found

Be thorough. The better the research, the better the LinkedIn post."""

    text = _call_with_status(
        client=client,
        stage="discovery",
        message=f"🔍 Searching {sources_str} for: {topic}...",
        messages=[{"role": "user", "content": prompt}],
        tools=[WEB_SEARCH_TOOL],
        status_callback=status_callback,
        max_tokens=3000,
    )
    return text


# ---------------------------------------------------------------------------
# Stage 2: Summarization
# ---------------------------------------------------------------------------

def _stage_summarize(
    client: anthropic.Anthropic,
    research: str,
    topic: str,
    status_callback: Callable | None,
) -> dict:
    """Extract key insights and claims from research."""
    prompt = f"""You are a content strategist. Based on this research about "{topic}", extract:

RESEARCH:
{research}

Extract and return a JSON object with:
{{
  "key_insight": "The single most interesting/surprising finding in 1-2 sentences",
  "supporting_facts": ["fact 1", "fact 2", "fact 3"],
  "top_claims": ["claim 1", "claim 2", "claim 3"],  // the 3 most specific, verifiable claims
  "narrative_angle": "The most compelling angle for a LinkedIn post in 1 sentence",
  "best_source_urls": ["url1", "url2", "url3"],
  "sources_summary": "Brief description of sources found"
}}

Return ONLY the JSON object, no other text."""

    text = _call_with_status(
        client=client,
        stage="summarize",
        message="📄 Extracting key insights and claims...",
        messages=[{"role": "user", "content": prompt}],
        tools=None,
        status_callback=status_callback,
        max_tokens=1500,
    )

    return _extract_json(text, {
        "key_insight": research[:300] if research else "No insight extracted",
        "supporting_facts": [],
        "top_claims": [],
        "narrative_angle": topic,
        "best_source_urls": [],
        "sources_summary": "Web research",
    })


# ---------------------------------------------------------------------------
# Stage 3: Fact-check
# ---------------------------------------------------------------------------

def _stage_fact_check(
    client: anthropic.Anthropic,
    claims: list[str],
    status_callback: Callable | None,
) -> list[dict]:
    """Verify the top claims with web search and return structured results."""
    if not claims:
        return []

    claims_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims[:3]))

    prompt = f"""You are a fact-checker. Please verify these claims using web search:

{claims_text}

For each claim, search the web to determine if it's accurate, partially accurate, or inaccurate.

Return a JSON array:
[
  {{
    "claim": "the claim text",
    "status": "verified" | "partially_verified" | "unverified" | "inaccurate",
    "explanation": "Brief explanation of your finding",
    "source": "URL or source name if found"
  }}
]

Return ONLY the JSON array."""

    text = _call_with_status(
        client=client,
        stage="fact_check",
        message="✓ Verifying key claims with web search...",
        messages=[{"role": "user", "content": prompt}],
        tools=[WEB_SEARCH_TOOL],
        status_callback=status_callback,
        max_tokens=1500,
    )

    # Try to parse as array
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback
    return [{"claim": c, "status": "unverified", "explanation": "Could not verify", "source": ""} for c in claims[:3]]


# ---------------------------------------------------------------------------
# Stage 4: Writing
# ---------------------------------------------------------------------------

def _stage_write(
    client: anthropic.Anthropic,
    research: str,
    summary: dict,
    style: str,
    post_length: int,
    creators: list[str],
    topic: str,
    status_callback: Callable | None,
) -> dict:
    """Write the final LinkedIn post and alternatives."""
    style_instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["🧠 Thought Leader"])
    creators_str = (
        f"\nCreator style influences (mimic their TONE, not their content): {', '.join(creators)}"
        if creators
        else ""
    )

    prompt = f"""You are an expert LinkedIn content writer specializing in AI topics.

TOPIC: {topic}

KEY INSIGHT: {summary.get('key_insight', '')}

SUPPORTING FACTS:
{chr(10).join('- ' + f for f in summary.get('supporting_facts', []))}

NARRATIVE ANGLE: {summary.get('narrative_angle', '')}

WRITING STYLE: {style}
Style instructions: {style_instruction}
{creators_str}

TARGET LENGTH: approximately {post_length} words

LINKEDIN POST BEST PRACTICES:
- Start with a scroll-stopping hook (first line must make people stop scrolling)
- Use line breaks generously — short paragraphs, white space
- No corporate jargon
- End with a clear call-to-action or question that invites engagement
- Personal voice, not brand voice

Please write a complete LinkedIn post and return a JSON object:
{{
  "post_draft": "The complete LinkedIn post text, with \\n for line breaks",
  "hook_alternatives": [
    "Alternative opening line 1",
    "Alternative opening line 2",
    "Alternative opening line 3"
  ],
  "hashtags": "#AI #ArtificialIntelligence #MachineLearning #Tech",
  "word_count": 150
}}

The post_draft should be the COMPLETE post (not just the opening). Make it polished and ready to publish.
Return ONLY the JSON object."""

    text = _call_with_status(
        client=client,
        stage="writing",
        message="✍️ Crafting your LinkedIn post...",
        messages=[{"role": "user", "content": prompt}],
        tools=None,
        status_callback=status_callback,
        max_tokens=2000,
    )

    result = _extract_json(text, {})

    if not result.get("post_draft"):
        # Fallback: use the raw text as the post
        result = {
            "post_draft": text,
            "hook_alternatives": [],
            "hashtags": "#AI #ArtificialIntelligence #MachineLearning",
            "word_count": len(text.split()),
        }

    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    anthropic_api_key: str,
    youtube_api_key: str | None,
    topic: str,
    sources: list[str],
    style: str,
    post_length: int,
    creators: list[str],
    status_callback: Callable | None = None,
) -> dict:
    """
    Run the full LinkedIn post generation pipeline.

    Returns dict with keys:
      post_draft, hook_alternatives, hashtags,
      fact_check, references, query_summary
    """
    client = anthropic.Anthropic(api_key=anthropic_api_key)

    try:
        # Stage 1: Discovery
        research = _stage_discovery(
            client=client,
            topic=topic,
            sources=sources,
            creators=creators,
            youtube_api_key=youtube_api_key,
            status_callback=status_callback,
        )

        # Stage 2: Summarize
        summary = _stage_summarize(
            client=client,
            research=research,
            topic=topic,
            status_callback=status_callback,
        )

        # Stage 3: Fact-check
        fact_check_results = _stage_fact_check(
            client=client,
            claims=summary.get("top_claims", []),
            status_callback=status_callback,
        )

        # Stage 4: Write
        writing = _stage_write(
            client=client,
            research=research,
            summary=summary,
            style=style,
            post_length=post_length,
            creators=creators,
            topic=topic,
            status_callback=status_callback,
        )

        if status_callback:
            status_callback("done", "✅ Post ready!")

        return {
            "post_draft": writing.get("post_draft", ""),
            "hook_alternatives": writing.get("hook_alternatives", []),
            "hashtags": writing.get("hashtags", "#AI #ArtificialIntelligence"),
            "fact_check": fact_check_results,
            "references": summary.get("best_source_urls", []),
            "query_summary": summary.get("sources_summary", ""),
            "key_insight": summary.get("key_insight", ""),
        }

    except anthropic.AuthenticationError:
        raise ValueError(
            "Invalid Anthropic API key. Please check your key at console.anthropic.com"
        )
    except anthropic.RateLimitError:
        raise ValueError(
            "Rate limit reached. Please wait a moment and try again."
        )
    except anthropic.APIError as e:
        raise ValueError(f"API error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Pipeline error: {str(e)}")
