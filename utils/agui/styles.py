"""
Chat UI styles — light theme, adapted from AlpaTrade for AHMF.
"""

from fasthtml.common import Style

CHAT_UI_STYLES = """
/* === CSS Variables (Light default) === */
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-tertiary: #f1f5f9;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-muted: #94a3b8;
  --border-color: #e2e8f0;
  --border-strong: #cbd5e1;
  --accent: #0066cc;
  --accent-hover: #0052a3;
  --table-bg: #ffffff;
  --table-header: #f1f5f9;
  --table-border: #e2e8f0;
  --table-stripe: #f8fafc;
  --table-hover: #f1f5f9;
  --table-text: #1e293b;
  --code-bg: #f1f5f9;
  --user-bubble: #0066cc;
  --asst-bubble: #f8fafc;
  --asst-border: #e2e8f0;
}

/* === Chat UI === */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.chat-container.welcome-active { justify-content: center; }
.chat-container.welcome-active .chat-messages { flex: 0 0 auto; overflow-y: hidden; padding-bottom: 0; }
.chat-container.welcome-active .chat-input { padding-top: 0.75rem; border-top: none; flex: 0 0 auto; }

/* === Messages === */
.chat-message {
  display: flex;
  flex-direction: column;
  max-width: 85%;
  animation: chat-message-in 0.3s ease-out;
}

.chat-message-content {
  padding: 0.75rem 1rem;
  border-radius: 1.125rem;
  font-size: 0.875rem;
  line-height: 1.5;
  word-wrap: break-word;
  position: relative;
}

.chat-message-content p { margin: 0 0 0.5rem 0; }
.chat-message-content p:last-child { margin-bottom: 0; }
.chat-message-content ul, .chat-message-content ol { margin: 0.5rem 0; padding-left: 1.5rem; }
.chat-message-content li { margin: 0.25rem 0; }

.chat-message-content code {
  background: var(--code-bg);
  color: var(--text-primary);
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875em;
}

.chat-message-content pre {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 0.75rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin: 0.5rem 0;
  font-size: 0.8rem;
  line-height: 1.5;
}

.chat-message-content pre code { background: none; padding: 0; color: inherit; }

.chat-message-content blockquote {
  border-left: 3px solid var(--border-color);
  padding-left: 1rem;
  margin: 0.5rem 0;
  color: var(--text-secondary);
}

.chat-message-content h1, .chat-message-content h2,
.chat-message-content h3, .chat-message-content h4 {
  margin: 0.75rem 0 0.5rem 0; font-weight: 600; color: var(--text-primary);
}

.chat-message-content strong { color: var(--text-primary); }
.chat-message-content li { color: var(--text-primary); }
.chat-message-content p { color: var(--text-primary); }
.chat-message-content h1 { font-size: 1.25rem; }
.chat-message-content h2 { font-size: 1.125rem; }
.chat-message-content h3 { font-size: 1rem; }

.chat-message-content table {
  border-collapse: collapse; width: 100%; margin: 0.5rem 0;
  background: var(--table-bg); display: block; overflow-x: auto;
  border: 1px solid var(--table-border); border-radius: 0.5rem;
  font-size: 0.85rem;
}
.chat-message-content thead { display: table; width: 100%; table-layout: fixed; }
.chat-message-content tbody { display: table; width: 100%; table-layout: fixed; }
.chat-message-content tr { display: table-row; }
.chat-message-content th, .chat-message-content td {
  display: table-cell; border: 1px solid var(--table-border);
  padding: 0.5rem 0.75rem; text-align: left;
  color: var(--table-text); white-space: nowrap; font-size: 0.8rem;
}
.chat-message-content th {
  background: var(--table-header); font-weight: 600;
  color: var(--text-secondary); font-size: 0.75rem;
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 2px solid var(--border-strong);
}
.chat-message-content tbody tr:nth-child(even) td { background: var(--table-stripe); }
.chat-message-content tbody tr:hover td { background: var(--table-hover); }

@keyframes chat-message-in {
  from { opacity: 0; transform: translateY(0.5rem); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-user { align-self: flex-end; }
.chat-assistant { align-self: flex-start; }

.chat-user .chat-message-content {
  background: var(--user-bubble); color: #ffffff;
  border-bottom-right-radius: 0.375rem;
}
.chat-assistant .chat-message-content {
  background: var(--asst-bubble); color: var(--text-primary);
  border: 1px solid var(--asst-border); border-bottom-left-radius: 0.375rem;
}

.chat-streaming::after { content: '|'; animation: chat-blink 1s infinite; opacity: 0.7; }
@keyframes chat-blink { 0%, 50% { opacity: 0.7; } 51%, 100% { opacity: 0; } }

/* === Input Form === */
.chat-input {
  padding: 1.25rem 1.5rem 1.5rem; background: var(--bg-primary);
  border-top: 1px solid var(--border-color);
  max-width: 800px; margin: 0 auto; width: 100%; box-sizing: border-box;
}

.chat-status { min-height: 1rem; padding: 0.25rem 0; color: var(--text-secondary); font-size: 0.8rem; text-align: center; }

#suggestion-buttons {
  display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0.5rem 0;
  margin-bottom: 0.25rem; justify-content: center;
}

.suggestion-btn {
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.45rem 0.9rem; background: var(--bg-primary);
  border: 1px solid var(--border-color); border-radius: 1.25rem;
  color: var(--accent); font-size: 0.8rem; cursor: pointer;
  white-space: nowrap; transition: all 0.2s;
}
.suggestion-btn .arrow { transition: transform 0.2s; font-size: 0.75rem; }
.suggestion-btn:hover { background: var(--accent); color: white; border-color: var(--accent); }
.suggestion-btn:hover .arrow { transform: translateX(2px); }

.chat-input-form {
  display: grid; grid-template-columns: 1fr auto; gap: 0.5rem; align-items: end;
  width: 100%; background: var(--bg-secondary); border: 1px solid var(--border-color);
  border-radius: 1rem; padding: 0.5rem; transition: border-color 0.2s, box-shadow 0.2s;
}
.chat-input-form:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1); }

.chat-input-field {
  width: 100%; padding: 0.5rem 0.75rem; border: none; border-radius: 0.5rem;
  background: transparent; color: var(--text-primary); font-family: inherit;
  font-size: 0.9rem; line-height: 1.5; resize: none; min-height: 3.5rem;
  max-height: 12rem; overflow-y: hidden; box-sizing: border-box;
}
.chat-input-field:focus { outline: none; border: none; box-shadow: none; }

.chat-input-button {
  padding: 0.5rem 1rem; background: var(--accent); color: white; border: none;
  border-radius: 0.625rem; font-family: inherit; font-size: 0.875rem;
  font-weight: 500; cursor: pointer; min-height: 2.25rem; align-self: end; margin-bottom: 0.125rem;
}
.chat-input-button:hover { background: var(--accent-hover); }
.chat-input-button:disabled { opacity: 0.5; cursor: not-allowed; background: #94a3b8; }
.chat-input-button.sending { animation: pulse-send 1.5s ease-in-out infinite; background: #94a3b8; }
@keyframes pulse-send { 0%, 100% { opacity: 0.5; } 50% { opacity: 0.7; } }

/* === Tool Messages === */
.chat-tool { align-self: center; max-width: 70%; }
.chat-tool .chat-message-content {
  background: var(--bg-tertiary); color: var(--text-secondary);
  font-size: 0.8rem; text-align: center; border-radius: 0.75rem; padding: 0.4rem 0.8rem;
}

.chat-error .chat-message-content { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

/* === Log Console === */
.agui-log-console { overflow: visible; }
.agui-log-pre {
  color: var(--text-secondary); font-size: 0.8em; margin: 0;
  white-space: pre-wrap; font-family: ui-monospace, monospace;
  background: var(--bg-secondary); border: 1px solid var(--border-color);
  padding: 0.75rem; border-radius: 0.5rem;
}

/* === Welcome Screen === */
.welcome-hero {
  display: flex; flex-direction: column; align-items: center;
  max-width: 560px; margin: 0 auto; padding-top: 2vh; padding-bottom: 2rem; text-align: center;
}
.welcome-icon {
  width: 56px; height: 56px;
  background: linear-gradient(135deg, #0066cc, #004d99);
  border-radius: 16px; display: flex; align-items: center; justify-content: center;
  margin-bottom: 1.25rem;
}
.welcome-title {
  font-size: 1.5rem; font-weight: 700;
  background: linear-gradient(135deg, #1e293b, #0066cc);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; margin-bottom: 0.5rem;
}
.welcome-subtitle { font-size: 0.875rem; color: #64748b; margin-bottom: 2rem; }
.welcome-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; width: 100%; }
.welcome-card {
  background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: 12px; padding: 1rem; cursor: pointer; text-align: left; transition: all 0.2s;
}
.welcome-card:hover { border-color: #66a3d9; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0, 102, 204, 0.1); }
.welcome-card-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;
}
.welcome-card-title { font-size: 0.825rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem; }
.welcome-card-desc { font-size: 0.75rem; color: var(--text-secondary); }

/* === Input Hint === */
.input-hint { font-size: 0.7rem; color: var(--text-muted); text-align: center; padding-top: 0.25rem; }
.kbd {
  background: var(--bg-tertiary); border: 1px solid var(--border-color);
  border-radius: 3px; padding: 0.1rem 0.35rem; font-family: ui-monospace, monospace; font-size: 0.65rem;
}

/* === Result Cards === */
.result-card {
  background: var(--bg-primary); border-radius: 12px;
  border: 1px solid var(--border-color); overflow: hidden; max-width: 100%; margin-bottom: 0.75rem;
}
.card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1rem; border-bottom: 1px solid var(--bg-tertiary);
}
.card-header h3 { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.card-metrics {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.5rem; padding: 0.75rem 1rem;
}
.metric { display: flex; flex-direction: column; }
.metric-label { font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; }
.metric-value { font-size: 1rem; font-weight: 700; color: var(--text-primary); }
.metric-value.positive { color: #16a34a; }
.metric-value.negative { color: #dc2626; }

.badge-green { display: inline-block; background: #dcfce7; color: #166534; padding: 0.15rem 0.5rem; border-radius: 1rem; font-size: 0.7rem; font-weight: 500; }
.badge-red { display: inline-block; background: #fef2f2; color: #991b1b; padding: 0.15rem 0.5rem; border-radius: 1rem; font-size: 0.7rem; font-weight: 500; }
.badge-blue { display: inline-block; background: #dbeafe; color: #1e40af; padding: 0.15rem 0.5rem; border-radius: 1rem; font-size: 0.7rem; font-weight: 500; }
.badge-amber { display: inline-block; background: #fef3c7; color: #92400e; padding: 0.15rem 0.5rem; border-radius: 1rem; font-size: 0.7rem; font-weight: 500; }

.result-enriched { padding: 0.5rem !important; background: transparent !important; border: none !important; overflow: visible !important; }
.chat-assistant .chat-message-content { overflow: visible; max-height: none; }

/* Scrollbar */
.chat-messages { scrollbar-width: thin; scrollbar-color: #cbd5e1 transparent; }
.chat-messages::-webkit-scrollbar { width: 6px; }
.chat-messages::-webkit-scrollbar-track { background: transparent; }
.chat-messages::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

/* === Table Toolbar === */
.table-toolbar { display: flex; gap: 0.35rem; justify-content: flex-end; margin-bottom: 0.25rem; }
.table-action-btn {
  padding: 0.2rem 0.5rem; font-size: 0.7rem; font-family: inherit;
  color: var(--accent); background: var(--bg-secondary);
  border: 1px solid var(--border-color); border-radius: 0.25rem; cursor: pointer; transition: all 0.15s;
}
.table-action-btn:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

/* === Responsive === */
@media (max-width: 768px) {
  .chat-message { max-width: 95%; }
  .welcome-grid { grid-template-columns: 1fr; }
}
"""


def get_chat_styles():
    """Get chat UI styles as a Style component."""
    return Style(CHAT_UI_STYLES)


def get_custom_theme(**theme_vars):
    """Generate custom theme CSS variable overrides."""
    css_vars = []
    for key, value in theme_vars.items():
        css_vars.append(f"--{key.replace('_', '-')}: {value};")
    return Style(f":root {{ {' '.join(css_vars)} }}")
