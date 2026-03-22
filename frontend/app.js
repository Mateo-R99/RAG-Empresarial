/**
 * RAG Empresarial — Lógica del Chat
 * Maneja consultas, uploads, renderizado de respuestas y fuentes.
 */

const API_BASE = '/api';

// ─── DOM Elements ──────────────────────────────────────────────────
const chatMessages = document.getElementById('chatMessages');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const fileInput = document.getElementById('fileInput');
const uploadZone = document.getElementById('uploadZone');
const uploadProgress = document.getElementById('uploadProgress');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const documentsList = document.getElementById('documentsList');
const systemStatus = document.getElementById('systemStatus');
const menuBtn = document.getElementById('menuBtn');
const sidebar = document.getElementById('sidebar');

let isQuerying = false;

// ─── Initialization ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadDocuments();
    setupEventListeners();
});

function setupEventListeners() {
    // Send message
    sendBtn.addEventListener('click', sendQuery);
    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuery();
        }
    });

    // Auto-resize textarea
    queryInput.addEventListener('input', () => {
        queryInput.style.height = 'auto';
        queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + 'px';
        sendBtn.disabled = !queryInput.value.trim();
    });

    // File upload
    uploadZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) uploadFile(e.target.files[0]);
    });

    // Drag & drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
    });

    // Suggestion chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            queryInput.value = chip.dataset.query;
            queryInput.dispatchEvent(new Event('input'));
            sendQuery();
        });
    });

    // Mobile menu
    menuBtn.addEventListener('click', toggleSidebar);
}

// ─── Query / RAG ───────────────────────────────────────────────────
async function sendQuery() {
    const pregunta = queryInput.value.trim();
    if (!pregunta || isQuerying) return;

    isQuerying = true;
    sendBtn.disabled = true;

    // Remove welcome message
    const welcome = chatMessages.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // Add user message
    addMessage('user', pregunta);
    queryInput.value = '';
    queryInput.style.height = 'auto';

    // Add typing indicator
    const typingEl = addTypingIndicator();

    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pregunta })
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Error ${response.status}`);
        }

        const data = await response.json();
        typingEl.remove();
        addMessage('assistant', data.respuesta, data.fuentes, data.modelo_usado);
    } catch (error) {
        typingEl.remove();
        addMessage('assistant', `⚠️ Error: ${error.message}. Verifica que todos los servicios estén activos.`);
    } finally {
        isQuerying = false;
        sendBtn.disabled = false;
        queryInput.focus();
    }
}

// ─── Messages ──────────────────────────────────────────────────────
function addMessage(role, text, fuentes = [], modelo = '') {
    const msg = document.createElement('div');
    msg.className = `message ${role}`;

    const avatar = role === 'user' ? '👤' : '🤖';
    const formattedText = formatText(text);

    let sourcesHTML = '';
    if (fuentes && fuentes.length > 0) {
        const sourceCards = fuentes.map((f, i) => `
            <div class="source-card">
                <div class="source-header">
                    <span class="source-name">📄 ${escapeHtml(f.documento)}${f.pagina ? ` — Pág. ${f.pagina}` : ''}</span>
                    <span class="source-score">${(f.similitud * 100).toFixed(0)}%</span>
                </div>
                <div class="source-text">${escapeHtml(f.fragmento)}</div>
            </div>
        `).join('');

        sourcesHTML = `
            <div class="sources-section">
                <button class="sources-toggle" onclick="toggleSources(this)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"/>
                    </svg>
                    ${fuentes.length} fuente${fuentes.length > 1 ? 's' : ''} consultada${fuentes.length > 1 ? 's' : ''}
                </button>
                <div class="sources-list">${sourceCards}</div>
            </div>
        `;
    }

    msg.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            ${formattedText}
            ${sourcesHTML}
        </div>
    `;

    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTypingIndicator() {
    const msg = document.createElement('div');
    msg.className = 'message assistant';
    msg.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msg;
}

function toggleSources(btn) {
    btn.classList.toggle('expanded');
    const list = btn.nextElementSibling;
    list.classList.toggle('visible');
}

// ─── File Upload ───────────────────────────────────────────────────
async function uploadFile(file) {
    const validExts = ['.pdf', '.docx'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!validExts.includes(ext)) {
        alert('Formato no soportado. Use PDF o DOCX.');
        return;
    }

    uploadProgress.classList.add('active');
    progressFill.style.width = '30%';
    progressText.textContent = `Procesando ${file.name}...`;

    const formData = new FormData();
    formData.append('archivo', file);

    try {
        progressFill.style.width = '60%';

        const response = await fetch(`${API_BASE}/ingest`, {
            method: 'POST',
            body: formData
        });

        progressFill.style.width = '90%';

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Error ${response.status}`);
        }

        const data = await response.json();
        progressFill.style.width = '100%';
        progressText.textContent = `✅ ${data.fragmentos_creados} fragmentos creados`;

        loadDocuments();

        setTimeout(() => {
            uploadProgress.classList.remove('active');
            progressFill.style.width = '0%';
        }, 3000);
    } catch (error) {
        progressText.textContent = `❌ Error: ${error.message}`;
        progressFill.style.width = '100%';
        progressFill.style.background = 'var(--error)';

        setTimeout(() => {
            uploadProgress.classList.remove('active');
            progressFill.style.width = '0%';
            progressFill.style.background = '';
        }, 4000);
    }

    fileInput.value = '';
}

// ─── Documents List ────────────────────────────────────────────────
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents`);
        if (!response.ok) throw new Error();

        const data = await response.json();

        if (data.documentos.length === 0) {
            documentsList.innerHTML = `
                <div class="empty-state">
                    <p>No hay documentos cargados</p>
                </div>
            `;
            return;
        }

        documentsList.innerHTML = data.documentos.map(doc => `
            <div class="doc-item">
                <div class="doc-icon ${doc.tipo}">${doc.tipo.toUpperCase()}</div>
                <div class="doc-info">
                    <div class="doc-name" title="${escapeHtml(doc.nombre)}">${escapeHtml(doc.nombre)}</div>
                    <div class="doc-meta">${doc.fragmentos} fragmentos</div>
                </div>
                <button class="doc-delete" onclick="deleteDocument('${escapeHtml(doc.nombre)}')" title="Eliminar">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            </div>
        `).join('');
    } catch (error) {
        documentsList.innerHTML = `
            <div class="empty-state">
                <p>Error cargando documentos</p>
            </div>
        `;
    }
}

async function deleteDocument(nombre) {
    if (!confirm(`¿Eliminar "${nombre}" y todos sus fragmentos?`)) return;

    try {
        const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(nombre)}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error();

        loadDocuments();
    } catch (error) {
        alert('Error eliminando documento');
    }
}

// ─── Health Check ──────────────────────────────────────────────────
async function checkHealth() {
    const statusEl = systemStatus;

    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        const dot = statusEl.querySelector('.status-dot');
        const text = statusEl.querySelector('span');

        if (data.chroma_conectado && data.llm_disponible) {
            dot.className = 'status-dot online';
            text.textContent = `${data.proveedor_llm} · Conectado`;
        } else if (data.chroma_conectado) {
            dot.className = 'status-dot';
            text.textContent = `ChromaDB OK · LLM no disponible`;
        } else {
            dot.className = 'status-dot offline';
            text.textContent = 'Servicios desconectados';
        }
    } catch {
        const dot = statusEl.querySelector('.status-dot');
        const text = statusEl.querySelector('span');
        dot.className = 'status-dot offline';
        text.textContent = 'API no disponible';
    }
}

// ─── Utilities ─────────────────────────────────────────────────────
function formatText(text) {
    // Basic markdown-like formatting
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\[Fuente: (.*?)\]/g, '<span class="source-ref">[📄 $1]</span>')
        .split('\n')
        .map(line => {
            line = line.trim();
            if (!line) return '';
            if (line.startsWith('- ') || line.startsWith('• ')) {
                return `<li>${line.substring(2)}</li>`;
            }
            return `<p>${line}</p>`;
        })
        .join('')
        .replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleSidebar() {
    sidebar.classList.toggle('open');

    let overlay = document.querySelector('.sidebar-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.addEventListener('click', toggleSidebar);
        document.body.appendChild(overlay);
    }
    overlay.classList.toggle('active');
}

// Refresh health/docs periodically
setInterval(checkHealth, 30000);
setInterval(loadDocuments, 60000);
