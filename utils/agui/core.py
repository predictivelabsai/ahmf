"""
AG-UI core: WebSocket-based chat with LangGraph agents.

Streaming via LangGraph astream_events(v2).
Adapted from AlpaTrade for AHMF film finance domain.
"""

from typing import Dict, List, Optional, Any
from fasthtml.common import (
    Div, Form, Hidden, Textarea, Button, Span, Script, Style, Pre, NotStr,
)
import asyncio
import collections
import logging
import re
import threading
import uuid

from .styles import get_chat_styles
from .chat_store import (
    save_conversation, save_message,
    load_conversation_messages, list_conversations,
)

_SCROLL_CHAT_JS = "var m=document.getElementById('chat-messages');if(m)m.scrollTop=m.scrollHeight;"
_GUARD_ENABLE_JS = "window._aguiProcessing=true;"
_GUARD_DISABLE_JS = "window._aguiProcessing=false;"


class StreamingCommand:
    """Sentinel returned by the command interceptor for long-running commands."""
    def __init__(self, raw_command: str, session: dict, app_state: Any):
        self.raw_command = raw_command
        self.session = session
        self.app_state = app_state


class LogCapture(logging.Handler):
    """Captures log records into a deque for streaming to the browser."""
    def __init__(self, maxlen=500):
        super().__init__()
        self.lines: collections.deque = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record):
        try:
            msg = self.format(record)
            with self._lock:
                self.lines.append(msg)
        except Exception:
            self.handleError(record)

    def get_lines(self) -> list:
        with self._lock:
            return list(self.lines)

    def clear(self):
        with self._lock:
            self.lines.clear()


# ---------------------------------------------------------------------------
# UI renderer
# ---------------------------------------------------------------------------

class UI:
    """Renders chat components for a given thread."""

    def __init__(self, thread_id: str, autoscroll: bool = True):
        self.thread_id = thread_id
        self.autoscroll = autoscroll

    def _clear_input(self):
        return self._render_input_form(oob_swap=True)

    def _render_messages(self, messages: list[dict], oob: bool = False):
        attrs = {"id": "chat-messages", "cls": "chat-messages"}
        if oob:
            attrs["hx_swap_oob"] = "outerHTML"
        return Div(
            *[self._render_message(m) for m in messages],
            **attrs,
        )

    def _render_message(self, message: dict):
        role = message.get("role", "assistant")
        cls = "chat-user" if role == "user" else "chat-assistant"
        mid = message.get("message_id", str(uuid.uuid4()))
        return Div(
            Div(message.get("content", ""), cls="chat-message-content marked"),
            cls=f"chat-message {cls}",
            id=mid,
        )

    def _render_input_form(self, oob_swap=False):
        container_attrs = {"cls": "chat-input", "id": "chat-input-container"}
        if oob_swap:
            container_attrs["hx_swap_oob"] = "outerHTML"

        return Div(
            Div(id="suggestion-buttons"),
            Div(id="chat-status", cls="chat-status"),
            Form(
                Hidden(name="thread_id", value=self.thread_id),
                Textarea(
                    id="chat-input",
                    name="msg",
                    placeholder="Type a command or ask a question...\nShift+Enter for new line",
                    autofocus=True,
                    autocomplete="off",
                    cls="chat-input-field",
                    rows="2",
                    onkeydown="handleKeyDown(this, event)",
                    oninput="autoResize(this)",
                ),
                Button("Send", type="submit", cls="chat-input-button",
                       onclick="if(window._aguiProcessing){event.preventDefault();return false;}"),
                cls="chat-input-form",
                id="chat-form",
                ws_send=True,
            ),
            Div(Span("Enter", cls="kbd"), " to send  ", Span("Shift+Enter", cls="kbd"), " new line", cls="input-hint"),
            **container_attrs,
        )

    def _render_welcome(self):
        """Render the welcome hero with suggestion cards."""
        _ICON_CHAT = '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>'
        _ICON_DEAL = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg>'
        _ICON_CHART = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>'
        _ICON_SEARCH = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>'
        _ICON_FILM = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/><line x1="17" y1="17" x2="22" y2="17"/></svg>'

        _ICON_RISK = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
        _ICON_GLOBE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>'

        cards = [
            ("View Deal Pipeline", "See all active and pipeline deals", "deal:list", "#0066cc", _ICON_DEAL),
            ("Generate Sales Estimate", "AI-powered revenue projections", "estimate:new", "#8b5cf6", _ICON_CHART),
            ("Search Contacts", "Find distributors, producers, agents", "contact:search", "#f59e0b", _ICON_SEARCH),
            ("Portfolio Overview", "Aggregate loan and performance data", "portfolio", "#10b981", _ICON_FILM),
            ("Production Risk Score", "Evaluate execution risk across 6 dimensions", "risk:new", "#dc2626", _ICON_RISK),
            ("Film Tax Incentives", "Search 16+ global incentive programs", "incentives", "#0891b2", _ICON_GLOBE),
        ]

        card_els = []
        for title, desc, cmd, color, icon_svg in cards:
            card_els.append(
                Div(
                    Div(NotStr(icon_svg), cls="welcome-card-icon",
                        style=f"background:{color}15;color:{color}"),
                    Div(title, cls="welcome-card-title"),
                    Div(desc, cls="welcome-card-desc"),
                    cls="welcome-card",
                    onclick=(
                        f"if(window._aguiProcessing)return;"
                        f"var ta=document.getElementById('chat-input');"
                        f"var fm=document.getElementById('chat-form');"
                        f"if(ta&&fm){{ta.value={repr(cmd)};fm.requestSubmit();}}"
                    ),
                )
            )

        return Div(
            Div(
                Div(NotStr(_ICON_CHAT), cls="welcome-icon"),
                Div("Ashland Hill Media Finance", cls="welcome-title"),
                Div("AI-powered film financing intelligence", cls="welcome-subtitle"),
                Div(*card_els, cls="welcome-grid"),
                cls="welcome-hero",
            ),
            id="welcome-screen",
        )

    def chat(self, **kwargs):
        """Return the full chat widget (messages + input + scripts)."""
        # Check if thread has existing messages — only fetch via HTMX if so
        has_messages = False
        try:
            rows = load_conversation_messages(self.thread_id)
            has_messages = len(rows) > 0
        except Exception:
            pass

        if has_messages:
            msg_div = Div(
                id="chat-messages", cls="chat-messages",
                hx_get=f"/agui/messages/{self.thread_id}",
                hx_trigger="load", hx_swap="outerHTML",
            )
        else:
            # New thread — render welcome directly, no HTMX fetch (prevents flash)
            msg_div = Div(
                self._render_welcome(),
                id="chat-messages", cls="chat-messages",
            )

        components = [
            get_chat_styles(),
            msg_div,
            self._render_input_form(),
            Script("""
                (function() {
                    function checkWelcome() {
                        var container = document.querySelector('.chat-container');
                        var welcome = document.getElementById('welcome-screen');
                        if (container) {
                            if (welcome) container.classList.add('welcome-active');
                            else container.classList.remove('welcome-active');
                        }
                    }
                    checkWelcome();
                    var container = document.querySelector('.chat-container');
                    if (container) {
                        var observer = new MutationObserver(checkWelcome);
                        observer.observe(container, {childList: true, subtree: true});
                    }
                })();

                function autoResize(textarea) {
                    textarea.style.height = 'auto';
                    var maxH = 12 * 16;
                    var h = Math.min(textarea.scrollHeight, maxH);
                    textarea.style.height = h + 'px';
                    textarea.style.overflowY = textarea.scrollHeight > maxH ? 'auto' : 'hidden';
                }
                function handleKeyDown(textarea, event) {
                    autoResize(textarea);
                    if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        if (window._aguiProcessing) return;
                        var form = textarea.closest('form');
                        if (form && textarea.value.trim()) form.requestSubmit();
                    }
                }
                function renderMarkdown(elementId) {
                    setTimeout(function() {
                        var el = document.getElementById(elementId);
                        if (el && window.marked && el.classList.contains('marked')) {
                            var txt = el.textContent || el.innerText;
                            if (txt.trim()) {
                                el.innerHTML = marked.parse(txt);
                                el.classList.remove('marked');
                                el.classList.add('marked-done');
                                delete el.dataset.rendering;
                            }
                        }
                    }, 100);
                }
                if (window.marked) {
                    new MutationObserver(function() {
                        document.querySelectorAll('.marked').forEach(function(el) {
                            var parent = el.parentElement;
                            if (parent) {
                                var cursor = parent.querySelector('.chat-streaming');
                                if (cursor && cursor.textContent) return;
                            }
                            var txt = el.textContent || el.innerText;
                            if (txt.trim() && !el.dataset.rendering) {
                                el.dataset.rendering = '1';
                                setTimeout(function() {
                                    if (!el.classList.contains('marked')) { delete el.dataset.rendering; return; }
                                    var finalTxt = el.textContent || el.innerText;
                                    if (finalTxt.trim()) {
                                        el.innerHTML = marked.parse(finalTxt);
                                        el.classList.remove('marked');
                                        el.classList.add('marked-done');
                                    }
                                    delete el.dataset.rendering;
                                }, 150);
                            }
                        });
                    }).observe(document.body, {childList: true, subtree: true});
                }
            """),
        ]

        if self.autoscroll:
            components.append(Script("""
                (function() {
                    var obs = new MutationObserver(function() {
                        var m = document.getElementById('chat-messages');
                        if (m) m.scrollTop = m.scrollHeight;
                    });
                    var t = document.getElementById('chat-messages');
                    if (t) obs.observe(t, {childList: true, subtree: true});
                })();
            """))

        components.append(Div(id="agui-js", style="display:none"))

        return Div(
            *components,
            hx_ext="ws",
            ws_connect=f"/agui/ws/{self.thread_id}",
            cls="chat-container welcome-active",
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Thread (conversation)
# ---------------------------------------------------------------------------

class AGUIThread:
    """Single conversation thread with message history and LangGraph agent."""

    def __init__(self, thread_id: str, langgraph_agent, user_id: str = None):
        self.thread_id = thread_id
        self._agent = langgraph_agent
        self._user_id = user_id
        self._messages: list[dict] = []
        self._connections: Dict[str, Any] = {}
        self.ui = UI(self.thread_id, autoscroll=True)
        self._suggestions: list[str] = []
        self._command_interceptor = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True
        try:
            rows = load_conversation_messages(self.thread_id)
            self._messages = rows
        except Exception:
            pass

    def subscribe(self, connection_id, send):
        self._connections[connection_id] = send

    def unsubscribe(self, connection_id: str):
        self._connections.pop(connection_id, None)

    async def send(self, element):
        for _, send_fn in self._connections.items():
            await send_fn(element)

    async def _send_js(self, js_code: str):
        await self.send(Div(Script(js_code), id="agui-js", hx_swap_oob="innerHTML"))

    async def set_suggestions(self, suggestions: list[str]):
        self._suggestions = suggestions[:4]
        if self._suggestions:
            el = Div(
                *[
                    Button(
                        Span(s), Span("\u2192", cls="arrow"),
                        onclick=f"if(window._aguiProcessing)return;"
                        f"var ta=document.getElementById('chat-input');"
                        f"var fm=document.getElementById('chat-form');"
                        f"if(ta&&fm){{ta.value={repr(s)};fm.requestSubmit();}}",
                        cls="suggestion-btn",
                    )
                    for s in self._suggestions
                ],
                id="suggestion-buttons",
                hx_swap_oob="outerHTML",
            )
        else:
            el = Div(id="suggestion-buttons", hx_swap_oob="outerHTML")
        await self.send(el)

    async def _handle_message(self, msg: str, session):
        self._ensure_loaded()
        await self._send_js(_GUARD_ENABLE_JS)
        await self._send_js(
            "var w=document.getElementById('welcome-screen');if(w)w.remove();"
            "var c=document.querySelector('.chat-container');if(c)c.classList.remove('welcome-active');"
        )
        await self.set_suggestions([])

        if self._command_interceptor:
            result = await self._command_interceptor(msg, session)
            if result is not None:
                if isinstance(result, StreamingCommand):
                    asyncio.create_task(
                        self._handle_streaming_command(msg, result, session)
                    )
                else:
                    await self._handle_command_result(msg, result, session)
                return

        await self._handle_ai_run(msg, session)

    async def _handle_ai_run(self, msg: str, session):
        """Stream a LangGraph agent response via astream_events(v2)."""
        from langchain_core.messages import HumanMessage, AIMessage

        _open_trace = (
            "var l=document.querySelector('.app-layout');"
            "if(l&&!l.classList.contains('right-open'))l.classList.add('right-open');"
            "setTimeout(function(){var tc=document.getElementById('trace-content');"
            "if(tc)tc.scrollTop=tc.scrollHeight;},100);"
        )

        user_mid = str(uuid.uuid4())
        asst_mid = str(uuid.uuid4())
        content_id = f"message-content-{asst_mid}"

        # Save user message
        user_dict = {"role": "user", "content": msg, "message_id": user_mid}
        self._messages.append(user_dict)
        try:
            title = msg[:80] if len(self._messages) == 1 else None
            save_conversation(self.thread_id, user_id=self._user_id, title=title)
        except Exception:
            pass
        try:
            save_message(self.thread_id, "user", msg, user_mid)
        except Exception:
            pass

        # Send user bubble
        await self.send(Div(
            Div(Div(msg, cls="chat-message-content"), cls="chat-message chat-user", id=user_mid),
            id="chat-messages", hx_swap_oob="beforeend",
        ))

        # Disable input
        await self.send(self.ui._clear_input())
        await self._send_js(
            "var b=document.querySelector('.chat-input-button'),t=document.getElementById('chat-input');"
            "if(b){b.disabled=true;b.classList.add('sending')}"
            "if(t){t.disabled=true;t.placeholder='Thinking...'}"
        )

        # Create streaming assistant bubble
        await self.send(Div(
            Div(
                Div(
                    Span("", id=content_id),
                    Span("", cls="chat-streaming", id=f"streaming-{asst_mid}"),
                    cls="chat-message-content",
                ),
                cls="chat-message chat-assistant",
                id=f"message-{asst_mid}",
            ),
            id="chat-messages", hx_swap_oob="beforeend",
        ))

        # Trace: run started
        run_trace_id = str(uuid.uuid4())
        await self.send(Div(
            Div(Span("AI run started", cls="trace-label"), cls="trace-entry trace-run-start", id=f"trace-run-{run_trace_id}"),
            Script(_open_trace), id="trace-content", hx_swap_oob="beforeend",
        ))

        # Convert to LangChain messages
        lc_messages = []
        for m in self._messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            else:
                lc_messages.append(AIMessage(content=content))

        # Stream response
        full_response = ""
        try:
            async for event in self._agent.astream_events(
                {"messages": lc_messages}, version="v2"
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        full_response += token
                        await self.send(Span(token, id=content_id, hx_swap_oob="beforeend"))

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "tool")
                    tool_run_id = event.get("run_id", "")[:8]
                    await self.send(Div(
                        Div(Span(f"Tool: {tool_name}", cls="trace-label"), Span("running...", cls="trace-detail"),
                            cls="trace-entry trace-tool-active", id=f"trace-tool-{tool_run_id}"),
                        Script(_open_trace), id="trace-content", hx_swap_oob="beforeend",
                    ))
                    await self.send(Div(
                        Div(Div(f"Running {tool_name}...", cls="chat-message-content"), cls="chat-message chat-tool", id=f"tool-{tool_run_id}"),
                        id="chat-messages", hx_swap_oob="beforeend",
                    ))

                elif kind == "on_tool_end":
                    tool_run_id = event.get("run_id", "")[:8]
                    await self.send(Div(Div("Done", cls="chat-message-content"), cls="chat-message chat-tool",
                                        id=f"tool-{tool_run_id}", hx_swap_oob="outerHTML"))
                    await self.send(Div(Span("Tool complete", cls="trace-label"), cls="trace-entry trace-tool-done",
                                        id=f"trace-tool-{tool_run_id}", hx_swap_oob="outerHTML"))

        except Exception as e:
            error_msg = str(e)
            full_response = f"Error: {error_msg}"
            await self.send(Span(f"\n\n**Error:** {error_msg}", id=content_id, hx_swap_oob="beforeend"))

        # Finalize
        await self.send(Span("", id=f"streaming-{asst_mid}", hx_swap_oob="outerHTML"))
        await self._send_js(
            f"var el=document.getElementById('{content_id}');"
            f"if(el)el.classList.add('marked');"
            f"renderMarkdown('{content_id}');"
        )

        # Trace: run finished
        await self.send(Div(
            Div(Span("Run finished", cls="trace-label"), cls="trace-entry trace-run-end"),
            id="trace-content", hx_swap_oob="beforeend",
        ))

        # Save assistant message
        asst_dict = {"role": "assistant", "content": full_response, "message_id": asst_mid}
        self._messages.append(asst_dict)
        try:
            save_message(self.thread_id, "assistant", full_response, asst_mid)
        except Exception:
            pass

        # Re-enable input
        await self.send(self.ui._clear_input())
        await self._send_js(
            _GUARD_DISABLE_JS +
            "var b=document.querySelector('.chat-input-button'),t=document.getElementById('chat-input');"
            "if(b){b.disabled=false;b.classList.remove('sending')}"
            "if(t){t.disabled=false;t.placeholder='Type a command or ask a question...';t.focus()}"
        )
        await self._send_js(_SCROLL_CHAT_JS)

    async def _handle_command_result(self, msg: str, result: str, session):
        """Display a CLI command result in chat."""
        user_mid = str(uuid.uuid4())
        asst_mid = str(uuid.uuid4())
        content_id = f"message-content-{asst_mid}"

        # Save user message
        user_dict = {"role": "user", "content": msg, "message_id": user_mid}
        self._messages.append(user_dict)
        try:
            save_conversation(self.thread_id, user_id=self._user_id,
                              title=msg[:80] if len(self._messages) == 1 else None)
        except Exception:
            pass
        try:
            save_message(self.thread_id, "user", msg, user_mid)
        except Exception:
            pass

        # Send user bubble
        await self.send(Div(
            Div(Div(msg, cls="chat-message-content"), cls="chat-message chat-user", id=user_mid),
            id="chat-messages", hx_swap_oob="beforeend",
        ))

        # Send result
        await self.send(Div(
            Div(
                Div(result, cls="chat-message-content marked", id=content_id),
                cls="chat-message chat-assistant", id=f"message-{asst_mid}",
            ),
            id="chat-messages", hx_swap_oob="beforeend",
        ))
        await self._send_js(f"renderMarkdown('{content_id}');")

        # Save assistant response
        asst_dict = {"role": "assistant", "content": result, "message_id": asst_mid}
        self._messages.append(asst_dict)
        try:
            save_message(self.thread_id, "assistant", result, asst_mid)
        except Exception:
            pass

        # Re-enable input
        await self.send(self.ui._clear_input())
        await self._send_js(
            _GUARD_DISABLE_JS +
            "var b=document.querySelector('.chat-input-button'),t=document.getElementById('chat-input');"
            "if(b){b.disabled=false;b.classList.remove('sending')}"
            "if(t){t.disabled=false;t.placeholder='Type a command or ask a question...';t.focus()}"
        )
        await self._send_js(_SCROLL_CHAT_JS)

        # Follow-up suggestions
        suggestions = _get_followup_suggestions(msg)
        await self.set_suggestions(suggestions)


# ---------------------------------------------------------------------------
# Follow-up suggestions
# ---------------------------------------------------------------------------

def _get_followup_suggestions(msg: str) -> list:
    cmd = msg.strip().lower()
    first = cmd.split()[0] if cmd.split() else ""

    if first.startswith("deal:"):
        return ["contact:search", "portfolio", "estimate:new"]
    if first.startswith("contact:"):
        return ["deal:list", "portfolio", "estimate:new"]
    if first.startswith("estimate:"):
        return ["deal:list", "portfolio", "contact:search"]
    if cmd == "portfolio":
        return ["deal:list", "estimate:new", "contact:search"]
    if cmd == "help":
        return ["deal:list", "portfolio", "estimate:new"]

    return ["deal:list", "portfolio", "help"]


# ---------------------------------------------------------------------------
# Setup function
# ---------------------------------------------------------------------------

class AGUISetup:
    """Container holding threads and the LangGraph agent."""

    def __init__(self, app, langgraph_agent, command_interceptor=None):
        self._app = app
        self._agent = langgraph_agent
        self._threads: Dict[str, AGUIThread] = {}
        self._command_interceptor = command_interceptor
        self._register_routes()

    def get_thread(self, thread_id: str, user_id: str = None) -> AGUIThread:
        if thread_id not in self._threads:
            thread = AGUIThread(thread_id, self._agent, user_id)
            thread._command_interceptor = self._command_interceptor
            self._threads[thread_id] = thread
        return self._threads[thread_id]

    def chat(self, thread_id: str):
        """Return the chat widget for embedding in a page."""
        thread = self.get_thread(thread_id)
        return thread.ui.chat()

    def _register_routes(self):
        app = self._app
        rt = app.route

        @rt("/agui/messages/{thread_id}")
        def agui_messages(thread_id: str):
            thread = self.get_thread(thread_id)
            thread._ensure_loaded()
            if thread._messages:
                return thread.ui._render_messages(thread._messages)
            return Div(thread.ui._render_welcome(), id="chat-messages", cls="chat-messages")

        @app.ws("/agui/ws/{thread_id}")
        async def ws(msg: str, thread_id: str, send, session):
            thread = self.get_thread(thread_id, user_id=session.get("user_id"))
            conn_id = str(uuid.uuid4())
            thread.subscribe(conn_id, send)
            try:
                if msg and msg.strip():
                    await thread._handle_message(msg.strip(), session)
            finally:
                thread.unsubscribe(conn_id)


def setup_agui(app, langgraph_agent, command_interceptor=None) -> AGUISetup:
    """Initialize AG-UI on a FastHTML app."""
    return AGUISetup(app, langgraph_agent, command_interceptor=command_interceptor)
