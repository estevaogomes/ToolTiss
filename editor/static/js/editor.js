// Minimal JS utilities for the TISS Editor
function showToast(message, type) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + (type || 'success');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 4000);
}

async function abrirArquivo() {
    try {
        const resp = await fetch('/api/dialog/arquivo');
        const data = await resp.json();
        if (data.cancelado) return;
        const loadResp = await fetch('/api/carregar-xml', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({caminho: data.caminho})
        });
        const html = await loadResp.text();
        document.getElementById('main-content').innerHTML = html;
    } catch (e) {
        showToast('Erro ao abrir arquivo: ' + e.message, 'error');
    }
}

document.body.addEventListener('htmx:responseError', function() {
    showToast('Erro na requisição', 'error');
});

async function salvarGuia(guiaId) {
    const form = document.getElementById('guia-form');
    const formData = new FormData(form);
    // Convert bracket-notation keys to nested object
    const dados = {};
    for (const [key, value] of formData.entries()) {
        const parts = key.replace(/\]/g, '').split('[');
        let current = dados;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!(parts[i] in current)) current[parts[i]] = {};
            current = current[parts[i]];
        }
        current[parts[parts.length - 1]] = value;
    }
    try {
        const saveResp = await fetch('/api/salvar-xml', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({guia_id: guiaId, dados: dados})
        });
        const result = await saveResp.json();
        if (result.sucesso) {
            showToast('Salvo com sucesso! Hash: ' + result.hash, 'success');
        } else {
            showToast('Erro: ' + result.erro, 'error');
        }
    } catch (e) {
        showToast('Erro ao salvar: ' + e.message, 'error');
    }
}
