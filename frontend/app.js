/* ═══════════════════════════════════════════════════════════════════════════
   Multi-Agent AI Research System — Frontend Logic
   ═══════════════════════════════════════════════════════════════════════════ */

const API_BASE = window.location.origin;

// ─── DOM References ────────────────────────────────────────────────────────
const form           = document.getElementById('research-form');
const queryInput     = document.getElementById('query-input');
const submitBtn      = document.getElementById('submit-btn');
const pipelineSection = document.getElementById('pipeline-section');
const pipelineQuery  = document.getElementById('pipeline-query');
const reportSection  = document.getElementById('report-section');
const reportContent  = document.getElementById('report-content');
const errorSection   = document.getElementById('error-section');
const errorMessage   = document.getElementById('error-message');
const copyBtn        = document.getElementById('copy-btn');
const downloadBtn    = document.getElementById('download-btn');
const newResearchBtn = document.getElementById('new-research-btn');
const retryBtn       = document.getElementById('retry-btn');
const revisionIndicator = document.getElementById('revision-indicator');
const revisionText   = document.getElementById('revision-text');

// Agent execution order for activating the pipeline visually
const AGENT_ORDER = ['research', 'scrape', 'write', 'review', 'finalize'];

let currentQuery   = '';
let rawReport      = '';
let revisionCount  = 0;

// ─── Chip click handlers ──────────────────────────────────────────────────
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        queryInput.value = chip.dataset.query;
        queryInput.focus();
    });
});

// ─── Form submit ──────────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;
    currentQuery = query;
    await startResearch(query);
});

// ─── New Research / Retry ─────────────────────────────────────────────────
newResearchBtn.addEventListener('click', resetToSearch);
retryBtn.addEventListener('click', resetToSearch);

// ─── Copy report ──────────────────────────────────────────────────────────
copyBtn.addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText(rawReport);
        const original = copyBtn.textContent;
        copyBtn.textContent = '✅ Copied!';
        setTimeout(() => { copyBtn.textContent = original; }, 2000);
    } catch {
        // Fallback
        const ta = document.createElement('textarea');
        ta.value = rawReport;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
    }
});

// ─── Download report (.md) ────────────────────────────────────────────────
downloadBtn.addEventListener('click', () => {
    const slug = currentQuery.toLowerCase().replace(/[^\w\s-]/g, '').replace(/[-\s]+/g, '_').trim() || 'research_report';
    const blob = new Blob([rawReport], { type: 'text/markdown' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `${slug}.md`;
    a.click();
    URL.revokeObjectURL(url);
});

// ─── Download report (PDF) ────────────────────────────────────────────────
const downloadPdfBtn = document.getElementById('download-pdf-btn');
downloadPdfBtn.addEventListener('click', () => {
    const slug = currentQuery.toLowerCase().replace(/[^\w\s-]/g, '').replace(/[-\s]+/g, '_').trim() || 'research_report';
    const renderedHtml = reportContent.innerHTML;

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`<!DOCTYPE html>
<html>
<head>
    <title>${slug}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #1a1a2e;
            line-height: 1.8;
            padding: 40px 50px;
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            font-size: 1.8rem;
            margin-bottom: 0.8rem;
            color: #1a1a2e;
            border-bottom: 2px solid #8264ff;
            padding-bottom: 0.5rem;
        }
        h2 {
            font-size: 1.3rem;
            margin-top: 1.8rem;
            margin-bottom: 0.6rem;
            color: #333;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 0.3rem;
        }
        h3 {
            font-size: 1.1rem;
            margin-top: 1.2rem;
            margin-bottom: 0.4rem;
            color: #444;
        }
        p { margin-bottom: 0.8rem; color: #333; }
        ul, ol { margin-bottom: 0.8rem; padding-left: 1.5rem; }
        li { margin-bottom: 0.3rem; color: #333; }
        strong { color: #1a1a2e; }
        a { color: #8264ff; text-decoration: none; }
        blockquote {
            border-left: 3px solid #8264ff;
            padding-left: 1rem;
            margin: 0.8rem 0;
            color: #666;
            font-style: italic;
        }
        code {
            font-family: 'Courier New', monospace;
            font-size: 0.88em;
            background: #f0f0f5;
            padding: 2px 5px;
            border-radius: 3px;
        }
        pre {
            background: #f5f5fa;
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            margin-bottom: 0.8rem;
            border: 1px solid #e0e0e0;
        }
        pre code { background: none; padding: 0; }
        .footer-note {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid #e0e0e0;
            font-size: 0.75rem;
            color: #999;
            text-align: center;
        }
        @media print {
            body { padding: 20px; }
            @page { margin: 1.5cm; }
        }
    </style>
</head>
<body>
    ${renderedHtml}
    <div class="footer-note">Generated by AI Research Agent — Multi-Agent Deep Research System</div>
    <script>
        window.onload = function() {
            setTimeout(function() { window.print(); }, 500);
        };
    </script>
</body>
</html>`);
    printWindow.document.close();
});

// ─── Reset UI to initial search state ─────────────────────────────────────
function resetToSearch() {
    pipelineSection.classList.add('hidden');
    reportSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    revisionIndicator.classList.add('hidden');
    revisionCount = 0;

    // Reset all pipeline nodes
    document.querySelectorAll('.pipeline-node').forEach(node => {
        node.classList.remove('active', 'completed', 'failed');
        node.querySelector('.node-status').textContent = 'Waiting…';
    });
    document.querySelectorAll('.pipeline-connector').forEach(conn => {
        conn.classList.remove('active');
    });

    submitBtn.classList.remove('loading');
    submitBtn.disabled = false;
    queryInput.value = '';
    queryInput.focus();
}

// ─── Start a research job ─────────────────────────────────────────────────
async function startResearch(query) {
    // Show pipeline, hide report & error
    reportSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    revisionIndicator.classList.add('hidden');
    pipelineSection.classList.remove('hidden');
    pipelineQuery.textContent = `"${query}"`;
    revisionCount = 0;

    // Reset pipeline nodes
    document.querySelectorAll('.pipeline-node').forEach(node => {
        node.classList.remove('active', 'completed', 'failed');
        node.querySelector('.node-status').textContent = 'Waiting…';
    });
    document.querySelectorAll('.pipeline-connector').forEach(conn => {
        conn.classList.remove('active');
    });

    submitBtn.classList.add('loading');
    submitBtn.disabled = true;

    // Activate the first node
    activateNode('research');

    try {
        // POST to start the job
        const res = await fetch(`${API_BASE}/api/research`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });

        if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            throw new Error(detail.detail || `Server error: ${res.status}`);
        }

        const { job_id } = await res.json();

        // Connect to SSE stream
        streamEvents(job_id);

    } catch (err) {
        showError(err.message);
    }
}

// ─── SSE Streaming ────────────────────────────────────────────────────────
function streamEvents(jobId) {
    const source = new EventSource(`${API_BASE}/api/research/${jobId}/stream`);

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.agent === 'system') {
            // Final event
            source.close();

            if (data.status === 'completed' && data.report) {
                completeNode('finalize');
                showReport(data.report);
            } else {
                showError(data.errors?.join(', ') || 'Research failed');
            }
            return;
        }

        // Detect revision loops: if "write" fires again, it means a revision
        if (data.agent === 'write' && isNodeCompleted('write')) {
            revisionCount++;
            revisionIndicator.classList.remove('hidden');
            revisionText.textContent = `Reviewer requested changes — revision #${revisionCount}`;

            // Reset write & review nodes for the new pass
            resetNode('write');
            resetNode('review');
            resetNode('finalize');
        }

        // Mark node as completed, activate the next one
        completeNode(data.agent);
        const nextAgent = getNextAgent(data.agent);
        if (nextAgent) {
            activateNode(nextAgent);
        }
    };

    source.onerror = () => {
        source.close();
        // Check if report already shown (might error after close)
        if (!reportSection.classList.contains('hidden')) return;
        showError('Lost connection to the server. Please try again.');
    };
}

// ─── Pipeline node helpers ────────────────────────────────────────────────
function activateNode(agentName) {
    const node = document.querySelector(`.pipeline-node[data-agent="${agentName}"]`);
    if (!node) return;
    node.classList.add('active');
    node.querySelector('.node-status').textContent = 'Running…';
}

function completeNode(agentName) {
    const node = document.querySelector(`.pipeline-node[data-agent="${agentName}"]`);
    if (!node) return;
    node.classList.remove('active');
    node.classList.add('completed');
    node.querySelector('.node-status').textContent = 'Done ✓';

    // Activate connector after this node
    const idx = AGENT_ORDER.indexOf(agentName);
    const connectors = document.querySelectorAll('.pipeline-connector');
    if (idx >= 0 && idx < connectors.length) {
        connectors[idx].classList.add('active');
    }
}

function resetNode(agentName) {
    const node = document.querySelector(`.pipeline-node[data-agent="${agentName}"]`);
    if (!node) return;
    node.classList.remove('active', 'completed', 'failed');
    node.querySelector('.node-status').textContent = 'Waiting…';

    const idx = AGENT_ORDER.indexOf(agentName);
    const connectors = document.querySelectorAll('.pipeline-connector');
    if (idx > 0 && idx <= connectors.length) {
        connectors[idx - 1].classList.remove('active');
    }
}

function isNodeCompleted(agentName) {
    const node = document.querySelector(`.pipeline-node[data-agent="${agentName}"]`);
    return node?.classList.contains('completed');
}

function getNextAgent(currentAgent) {
    const idx = AGENT_ORDER.indexOf(currentAgent);
    if (idx >= 0 && idx < AGENT_ORDER.length - 1) {
        return AGENT_ORDER[idx + 1];
    }
    return null;
}

// ─── Show Report ──────────────────────────────────────────────────────────
function showReport(markdown) {
    rawReport = markdown;
    reportContent.innerHTML = marked.parse(markdown);
    reportSection.classList.remove('hidden');
    reportSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    submitBtn.classList.remove('loading');
    submitBtn.disabled = false;
}

// ─── Show Error ───────────────────────────────────────────────────────────
function showError(message) {
    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
    pipelineSection.classList.add('hidden');

    submitBtn.classList.remove('loading');
    submitBtn.disabled = false;
}
