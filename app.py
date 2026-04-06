"""
LinkedIn AI Post Generator — Streamlit App
Turn AI trends into ready-to-publish posts in seconds.
"""

from __future__ import annotations

import os
import threading
import time
from queue import Queue
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="LinkedIn AI Post Generator",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — LinkedIn blue palette
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Primary accent */
    :root {
        --linkedin-blue: #0A66C2;
        --linkedin-dark: #004182;
        --linkedin-bg: #F3F2EF;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E0DEDA;
    }

    /* Card-like containers */
    div[data-testid="stExpander"] {
        background: #FFFFFF;
        border: 1px solid #E0DEDA;
        border-radius: 8px;
        margin-bottom: 12px;
    }

    /* Generate button */
    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #0A66C2 !important;
        border: none !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        height: 3rem !important;
        border-radius: 24px !important;
        transition: background 0.2s;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #004182 !important;
    }

    /* Tab styling */
    button[data-baseweb="tab"] {
        font-weight: 600;
    }

    /* Post text area */
    textarea {
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    }

    /* App title */
    .app-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0A66C2;
        margin-bottom: 0;
    }
    .app-tagline {
        font-size: 0.85rem;
        color: #666;
        margin-top: 2px;
    }

    /* Section labels */
    .card-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #666;
        margin-bottom: 6px;
    }

    /* Metric badge */
    .accuracy-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOPIC_OPTIONS = [
    "🔥 Hottest AI content this week",
    "🎥 Trending YouTube video",
    "💻 Trending GitHub repo",
    "🐦 Viral AI tweets",
    "📰 Biggest AI news",
    "✏️ Custom topic...",
]

SOURCE_OPTIONS = ["YouTube", "GitHub", "Twitter/X", "Reddit", "HackerNews"]

STYLE_OPTIONS = [
    "🧠 Thought Leader",
    "📚 Educator",
    "🛠️ Practitioner",
    "⚡ Contrarian",
]

CREATOR_OPTIONS = [
    "Andrej Karpathy",
    "Yann LeCun",
    "Sam Altman",
    "Boris Cherny",
    "Garry Tan",
    "Ethan Mollick",
    "Simon Willison",
    "swyx",
    "Greg Brockman",
]

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
def _init_state() -> None:
    defaults = {
        "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "youtube_api_key": "",
        "generation_result": None,
        "generation_error": None,
        "is_generating": False,
        "status_messages": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<p class="app-header">💼 LinkedIn AI Post Generator</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-tagline">Turn AI trends into posts in seconds</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # API keys
    st.markdown("### 🔑 API Keys")
    api_key_input = st.text_input(
        "Anthropic API Key",
        type="password",
        value=st.session_state.anthropic_api_key,
        placeholder="sk-ant-...",
        help="Required to generate posts",
    )
    if api_key_input:
        st.session_state.anthropic_api_key = api_key_input

    yt_key_input = st.text_input(
        "YouTube API Key (optional)",
        type="password",
        value=st.session_state.youtube_api_key,
        placeholder="AIza...",
        help="Needed to search YouTube videos directly",
    )
    if yt_key_input:
        st.session_state.youtube_api_key = yt_key_input

    st.caption("🔗 Get your API key at [console.anthropic.com](https://console.anthropic.com)")

    st.divider()

    with st.expander("ℹ️ About this app", expanded=False):
        st.markdown(
            """
**LinkedIn AI Post Generator** uses a 4-stage AI pipeline:

1. **🔍 Discover** — Searches YouTube, GitHub, Reddit, HackerNews & more for the latest AI content
2. **📄 Summarize** — Extracts the key insight and narrative angle
3. **✓ Fact-check** — Verifies top claims using web search
4. **✍️ Write** — Crafts a polished LinkedIn post in your chosen style

Built with [Claude claude-sonnet-4-6](https://anthropic.com) and Streamlit.
            """
        )

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.markdown("## Create Your LinkedIn Post")
st.markdown("Configure below, then hit **Generate** — your draft will be ready in ~30 seconds.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Config cards
# ---------------------------------------------------------------------------
col_left, col_right = st.columns(2, gap="large")

with col_left:
    # Card 1: Topic
    with st.expander("📌 **Card 1 — Topic**", expanded=True):
        topic_choice = st.selectbox(
            "What do you want to post about?",
            options=TOPIC_OPTIONS,
            index=0,
        )

        custom_topic = ""
        if topic_choice == "✏️ Custom topic...":
            custom_topic = st.text_input(
                "Describe your topic",
                placeholder="e.g. GPT-4o's new voice mode capabilities",
            )

    # Card 2: Sources
    with st.expander("🌐 **Card 2 — Sources**", expanded=True):
        st.markdown("Which platforms should Claude search?")
        selected_sources = st.multiselect(
            "Sources",
            options=SOURCE_OPTIONS,
            default=SOURCE_OPTIONS,
            label_visibility="collapsed",
        )

with col_right:
    # Card 3: Writing Style
    with st.expander("✍️ **Card 3 — Writing Style**", expanded=True):
        style = st.radio(
            "Choose your voice:",
            options=STYLE_OPTIONS,
            index=0,
        )

        style_descriptions = {
            "🧠 Thought Leader": "Bold takes, opinionated, confident assertions",
            "📚 Educator": "Clear, accessible — teach something valuable",
            "🛠️ Practitioner": "Hands-on, what this means in practice",
            "⚡ Contrarian": "Challenge the hype, ask the hard questions",
        }
        st.caption(f"_{style_descriptions.get(style, '')}_")

        st.markdown("**Post length**")
        post_length = st.slider(
            "Target word count",
            min_value=100,
            max_value=400,
            value=200,
            step=50,
            label_visibility="collapsed",
        )
        st.caption(f"Target: ~{post_length} words")

    # Card 4: Creators
    with st.expander("👥 **Card 4 — Creator Style (optional)**", expanded=False):
        st.markdown("Whose tone should we study?")
        selected_creators = st.multiselect(
            "Select creators",
            options=CREATOR_OPTIONS,
            default=[],
            label_visibility="collapsed",
        )

        custom_creators = st.text_input(
            "Add custom creator handles",
            placeholder="e.g. @karpathy, @sama",
        )

        if custom_creators:
            extra = [c.strip() for c in custom_creators.replace(",", " ").split() if c.strip()]
            all_creators = selected_creators + extra
        else:
            all_creators = selected_creators

st.markdown("---")

# ---------------------------------------------------------------------------
# Resolve topic
# ---------------------------------------------------------------------------
def _resolve_topic() -> str:
    if topic_choice == "✏️ Custom topic...":
        return custom_topic.strip() if custom_topic.strip() else "Latest AI trends"
    topic_map = {
        "🔥 Hottest AI content this week": "The hottest AI content, announcements, and discussions this week",
        "🎥 Trending YouTube video": "A trending YouTube video about AI from the past week",
        "💻 Trending GitHub repo": "A trending GitHub repository related to AI or machine learning",
        "🐦 Viral AI tweets": "Viral tweets and discussions about AI from the past week",
        "📰 Biggest AI news": "The biggest AI news story from the past week",
    }
    return topic_map.get(topic_choice, topic_choice)


# ---------------------------------------------------------------------------
# Generate button
# ---------------------------------------------------------------------------
has_api_key = bool(st.session_state.anthropic_api_key.strip())

if not has_api_key:
    st.info("👈 Enter your **Anthropic API Key** in the sidebar to enable generation.")

generate_btn = st.button(
    "✨ Generate LinkedIn Post",
    type="primary",
    use_container_width=True,
    disabled=not has_api_key or st.session_state.is_generating,
)

# ---------------------------------------------------------------------------
# Generation logic
# ---------------------------------------------------------------------------
if generate_btn and has_api_key:
    st.session_state.generation_result = None
    st.session_state.generation_error = None
    st.session_state.is_generating = True
    st.session_state.status_messages = []

    topic = _resolve_topic()
    api_key = st.session_state.anthropic_api_key.strip()
    yt_key = st.session_state.youtube_api_key.strip() or None

    # Import here so the app still loads if anthropic isn't installed yet
    try:
        from pipeline import run_pipeline
    except ImportError as e:
        st.session_state.generation_error = f"Import error: {e}. Run `pip install -r requirements.txt`."
        st.session_state.is_generating = False
        st.rerun()

    # Run pipeline with live status updates
    result_holder: dict[str, Any] = {}
    error_holder: dict[str, str] = {}

    with st.status("🚀 Running AI pipeline...", expanded=True) as status_widget:
        stage_display = {
            "discovery": "🔍 Discovery — searching sources...",
            "summarize": "📄 Content — fetching and summarizing...",
            "fact_check": "✓ Fact-check — verifying claims...",
            "writing": "✍️ Writing — crafting your post...",
            "done": "✅ Complete!",
        }

        completed_stages: list[str] = []
        current_detail = {"text": ""}

        def _status_cb(stage: str, message: str) -> None:
            label = stage_display.get(stage, stage)
            if stage not in completed_stages:
                completed_stages.append(stage)
            current_detail["text"] = message
            status_widget.update(label=label)
            st.write(message)

        try:
            result = run_pipeline(
                anthropic_api_key=api_key,
                youtube_api_key=yt_key,
                topic=topic,
                sources=selected_sources,
                style=style,
                post_length=post_length,
                creators=all_creators,
                status_callback=_status_cb,
            )
            result_holder["data"] = result
            status_widget.update(label="✅ Post generated!", state="complete", expanded=False)
        except ValueError as e:
            error_holder["msg"] = str(e)
            status_widget.update(label="❌ Generation failed", state="error", expanded=False)
        except Exception as e:
            error_holder["msg"] = f"Unexpected error: {str(e)}"
            status_widget.update(label="❌ Generation failed", state="error", expanded=False)

    if error_holder:
        st.session_state.generation_error = error_holder["msg"]
    else:
        st.session_state.generation_result = result_holder.get("data")

    st.session_state.is_generating = False
    st.rerun()

# ---------------------------------------------------------------------------
# Error display
# ---------------------------------------------------------------------------
if st.session_state.generation_error:
    st.error(f"**Generation failed:** {st.session_state.generation_error}")
    if st.button("🔄 Try Again", type="secondary"):
        st.session_state.generation_error = None
        st.rerun()

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------
if st.session_state.generation_result:
    result: dict = st.session_state.generation_result

    st.markdown("---")
    st.markdown("## 🎉 Your LinkedIn Post")

    tabs = st.tabs(["📝 Post Draft", "🔀 Alternatives", "✓ Fact Check", "📎 Sources"])

    # ---- Tab 1: Post Draft ----
    with tabs[0]:
        col1, col2 = st.columns([3, 1])

        with col1:
            post_text = result.get("post_draft", "")
            edited_post = st.text_area(
                "Your post (editable)",
                value=post_text,
                height=400,
                label_visibility="collapsed",
            )
            st.caption("✏️ Edit directly above — the post is fully editable before you copy it.")

        with col2:
            st.markdown("**Hashtags**")
            hashtags = result.get("hashtags", "#AI #ArtificialIntelligence")
            st.code(hashtags, language=None)

            word_count = len(edited_post.split())
            st.metric("Word count", word_count)

            if result.get("key_insight"):
                st.markdown("**Key insight**")
                st.info(result["key_insight"])

        st.markdown("**📋 Copy tip:** Click inside the text area → Ctrl+A → Ctrl+C")

    # ---- Tab 2: Alternatives ----
    with tabs[1]:
        st.markdown("### 🔀 Alternative Opening Lines")
        st.markdown("Swap your hook for one of these to test different angles:")

        alternatives = result.get("hook_alternatives", [])
        if alternatives:
            for i, alt in enumerate(alternatives, 1):
                st.info(f"**Option {i}:** {alt}")
        else:
            st.info("No alternative hooks were generated. Try regenerating for different options.")

        st.markdown("---")
        st.markdown(
            "_Tip: A strong hook is the single biggest factor in LinkedIn post reach. "
            "Test 2–3 versions to see which one resonates._"
        )

    # ---- Tab 3: Fact Check ----
    with tabs[2]:
        st.markdown("### ✓ Claim Verification")

        fact_checks = result.get("fact_check", [])
        if fact_checks:
            verified_count = sum(1 for f in fact_checks if f.get("status") == "verified")
            partial_count = sum(1 for f in fact_checks if f.get("status") == "partially_verified")
            total = len(fact_checks)

            accuracy_pct = round(
                (verified_count + 0.5 * partial_count) / total * 100
            ) if total > 0 else 0

            # Accuracy badge
            if accuracy_pct >= 80:
                st.success(f"✅ Overall accuracy: **{accuracy_pct}%** — Good to publish")
            elif accuracy_pct >= 50:
                st.warning(f"⚠️ Overall accuracy: **{accuracy_pct}%** — Review flagged claims")
            else:
                st.error(f"❌ Overall accuracy: **{accuracy_pct}%** — Significant issues found")

            st.markdown("---")

            status_icons = {
                "verified": "✅",
                "partially_verified": "⚠️",
                "unverified": "⚠️",
                "inaccurate": "❌",
            }

            for fc in fact_checks:
                status = fc.get("status", "unverified")
                icon = status_icons.get(status, "❓")
                claim = fc.get("claim", "")
                explanation = fc.get("explanation", "")
                source = fc.get("source", "")

                if status == "verified":
                    with st.success(f"{icon} **{claim}**"):
                        if explanation:
                            st.write(explanation)
                        if source:
                            st.caption(f"Source: {source}")
                elif status == "inaccurate":
                    with st.error(f"{icon} **{claim}**"):
                        if explanation:
                            st.write(explanation)
                        if source:
                            st.caption(f"Source: {source}")
                else:
                    with st.warning(f"{icon} **{claim}**"):
                        if explanation:
                            st.write(explanation)
                        if source:
                            st.caption(f"Source: {source}")
        else:
            st.info("No specific claims were extracted for fact-checking in this run.")

    # ---- Tab 4: Sources ----
    with tabs[3]:
        st.markdown("### 📎 Research Sources")

        query_summary = result.get("query_summary", "")
        if query_summary:
            st.markdown(f"**Research summary:** {query_summary}")
            st.markdown("---")

        references = result.get("references", [])
        if references:
            st.markdown("**Reference links found during research:**")
            for i, url in enumerate(references, 1):
                if url and url.startswith("http"):
                    st.markdown(f"{i}. [{url}]({url})")
                elif url:
                    st.markdown(f"{i}. {url}")
        else:
            st.info(
                "Specific source URLs were not captured in this run. "
                "The post was generated from web research — use the key insight and claims "
                "above to find primary sources."
            )

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Regenerate", use_container_width=True):
            st.session_state.generation_result = None
            st.rerun()
    with col_b:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.generation_result = None
            st.session_state.generation_error = None
            st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Built with [Claude claude-sonnet-4-6](https://anthropic.com/claude) · "
    "[Get API key](https://console.anthropic.com) · "
    "Not affiliated with LinkedIn"
)
