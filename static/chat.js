/* Monika — UI controller (sidebar nav, chat toggle, table CSV). */

(() => {
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    // ── Mobile sidebar toggle ────────────────────────────────────
    window.toggleLeftPane = () => {
        const lp = $(".left-pane");
        const ov = $(".left-overlay");
        if (lp) lp.classList.toggle("open");
        if (ov) ov.classList.toggle("visible");
    };

    // ── Show AI chat ─────────────────────────────────────────────
    window.showChat = () => {
        const content = document.getElementById("center-content");
        const chat = document.getElementById("center-chat");
        if (content) content.style.display = "none";
        if (chat) chat.style.display = "block";
        const h = document.getElementById("center-title");
        if (h) h.textContent = "AI Assistant";
        $$(".nav-item").forEach(i => i.classList.remove("active"));
        const btn = document.getElementById("nav-chat");
        if (btn) btn.classList.add("active");
    };

    // ── Load module into center pane ─────────────────────────────
    window.loadModule = (path, title) => {
        const content = document.getElementById("center-content");
        const chat = document.getElementById("center-chat");
        if (content && chat) {
            chat.style.display = "none";
            content.style.display = "block";
            htmx.ajax("GET", path, { target: "#center-content", swap: "innerHTML" });
        }
        const h = document.getElementById("center-title");
        if (h) h.textContent = title;
        $$(".nav-item").forEach(i => i.classList.remove("active"));
        if (event && event.currentTarget) event.currentTarget.classList.add("active");
    };

    // ── Fill chat input (for prompts) ────────────────────────────
    window.fillChat = (cmd) => {
        if (window._aguiProcessing) return;
        showChat();
        setTimeout(() => {
            const ta = document.getElementById("chat-input");
            if (ta) { ta.value = cmd; ta.focus(); }
        }, 100);
    };

    window.fillAndSend = (cmd) => {
        if (window._aguiProcessing) return;
        showChat();
        setTimeout(() => {
            const ta = document.getElementById("chat-input");
            const fm = document.getElementById("chat-form");
            if (ta && fm) { ta.value = cmd; fm.requestSubmit(); }
        }, 100);
    };

    // ── CSV copy / download for tables ───────────────────────────
    function tableToCSV(table) {
        const rows = [];
        table.querySelectorAll("tr").forEach(tr => {
            const cells = [];
            tr.querySelectorAll("th, td").forEach(td => {
                cells.push('"' + td.textContent.trim().replace(/"/g, '""') + '"');
            });
            rows.push(cells.join(","));
        });
        return rows.join("\n");
    }

    function enhanceTables(container) {
        if (!container) return;
        container.querySelectorAll("table").forEach(table => {
            if (table.dataset.enhanced) return;
            table.dataset.enhanced = "1";
            const toolbar = document.createElement("div");
            toolbar.className = "table-toolbar";
            const copyBtn = document.createElement("button");
            copyBtn.textContent = "Copy CSV";
            copyBtn.className = "table-action-btn";
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(tableToCSV(table)).then(() => {
                    copyBtn.textContent = "Copied!";
                    setTimeout(() => { copyBtn.textContent = "Copy CSV"; }, 1500);
                });
            };
            const dlBtn = document.createElement("button");
            dlBtn.textContent = "Download CSV";
            dlBtn.className = "table-action-btn";
            dlBtn.onclick = () => {
                const blob = new Blob([tableToCSV(table)], { type: "text/csv" });
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = "monika-data.csv";
                a.click();
                URL.revokeObjectURL(a.href);
            };
            toolbar.appendChild(copyBtn);
            toolbar.appendChild(dlBtn);
            table.parentNode.insertBefore(toolbar, table);
        });
    }

    document.querySelectorAll(".chat-message-content, .module-content").forEach(b => enhanceTables(b));
    new MutationObserver(() => {
        document.querySelectorAll(".chat-message-content, .module-content").forEach(b => enhanceTables(b));
    }).observe(document.body, { childList: true, subtree: true });

    window.enhanceTables = enhanceTables;
})();
