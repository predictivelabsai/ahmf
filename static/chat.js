/* Monika — chat client (canvas, copy/share, sample cards). */

(() => {
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    // ── UI helpers ────────────────────────────────────────────────
    window.toggleLeftPane = () => {
        const lp = $(".left-pane");
        const ov = $(".left-overlay");
        if (lp) lp.classList.toggle("open");
        if (ov) ov.classList.toggle("visible");
    };

    window.toggleArtifactPane = () => {
        const r = $("#right-pane");
        const app = $(".app-layout");
        if (!r || !app) return;
        if (r.classList.contains("open")) {
            r.classList.remove("open");
            app.classList.add("pane-closed");
            const btn = $("#artifact-btn");
            if (btn) btn.classList.remove("active");
        } else {
            r.classList.add("open");
            app.classList.remove("pane-closed");
            const btn = $("#artifact-btn");
            if (btn) btn.classList.add("active");
        }
    };

    window.toggleGroup = (id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.toggle("open");
        const btn = document.getElementById("btn-" + id);
        if (btn) btn.classList.toggle("open");
    };

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
            if (ta && fm) {
                ta.value = cmd;
                fm.requestSubmit();
            }
        }, 100);
    };

    window.showChat = () => {
        const container = document.getElementById("center-content");
        const chatContainer = document.getElementById("center-chat");
        if (container) container.style.display = "none";
        if (chatContainer) chatContainer.style.display = "block";
        const h = document.getElementById("center-title");
        if (h) h.textContent = "AI Chat";
        $$(".sidebar-item").forEach(i => i.classList.remove("active"));
        const chatBtn = document.getElementById("nav-chat");
        if (chatBtn) chatBtn.classList.add("active");
    };

    window.loadModule = (path, title) => {
        const container = document.getElementById("center-content");
        const chatContainer = document.getElementById("center-chat");
        if (container && chatContainer) {
            chatContainer.style.display = "none";
            container.style.display = "block";
            htmx.ajax("GET", path, { target: "#center-content", swap: "innerHTML" });
        }
        const h = document.getElementById("center-title");
        if (h) h.textContent = title;
        $$(".sidebar-item").forEach(i => i.classList.remove("active"));
        if (event && event.currentTarget) event.currentTarget.classList.add("active");
    };

    // ── Copy / share chat ──────────────────────────────────────────
    window.copyChat = () => {
        const msgs = $$(".chat-message");
        const lines = [];
        msgs.forEach(m => {
            const role = m.classList.contains("chat-user") ? "You" : "Monika";
            const content = m.querySelector(".chat-message-content");
            if (content) lines.push(`${role}: ${content.textContent.trim()}`);
        });
        const text = lines.join("\n\n");
        navigator.clipboard.writeText(text).then(() => {
            const btn = document.getElementById("copy-chat-btn");
            if (btn) { btn.textContent = "Copied!"; setTimeout(() => { btn.textContent = "Copy chat"; }, 1500); }
        });
    };

    window.shareChat = () => {
        const btn = document.getElementById("share-chat-btn");
        // Copy current URL as share link
        navigator.clipboard.writeText(window.location.href).then(() => {
            if (btn) { btn.textContent = "Link copied!"; setTimeout(() => { btn.textContent = "Share"; }, 1500); }
        });
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

    // Enhance tables on page load and when new content appears
    document.querySelectorAll(".chat-message-content, .module-content").forEach(b => enhanceTables(b));
    new MutationObserver(() => {
        document.querySelectorAll(".chat-message-content, .module-content").forEach(b => enhanceTables(b));
    }).observe(document.body, { childList: true, subtree: true });

    window.enhanceTables = enhanceTables;
})();
