// Minimal JS utilities for the TISS Editor

function showToast(message, type const container = document.getElementById('toast-container    const toast = document.createElement('div');
    toast.className = `toast toast-${type || 'success'}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

async function abrirArquivo() {
    try {
        const resp = await fetch('/api/dialog/arquivo');
        const data = await resp.json();
        if (data.cancelado) return;

        // Load the selected XML into the editor
        const loadResp = await fetch('/api/carregar-xml', {
            method: ' headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({caminho: data.caminho})
               const html = await loadResp.text();
        document.getElementById('main-content').innerHTML = html;
    } catch (e) {
        showToast('Erro ao abrir arquivo: ' + e.message, 'error');
    }
}

// Listen for HTMX errors
document.body.addEventListener('htmx:responseError', function showToast('Erro na requisição', 'error');
});