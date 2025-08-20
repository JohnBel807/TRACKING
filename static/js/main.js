(function () {
    const form = document.getElementById('contactForm');
    const statusEl = document.getElementById('formStatus');

    function isEmail(v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v || ''); }
    function isPhone(v) { return /^(\+?\d{7,15})$/.test((v || '').replace(/\s|-/g, '')); }

    const API = {
        create: `${window.location.origin}/api/clients`,
        list: `${window.location.origin}/api/clients`,
    };

    async function sendLead(data) {
        const res = await fetch(API.create, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const e = await res.json().catch(() => ({ error: 'Error' }));
            throw new Error(e.error || 'Error al guardar');
        }
        return res.json();
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('name').value.trim();
            const email = document.getElementById('email').value.trim();
            const phone = document.getElementById('phone').value.trim();
            const message = document.getElementById('message').value.trim();

            if (!name || !email || !phone || !message) { statusEl.textContent = 'Completa todos los campos.'; return; }
            if (!isEmail(email)) { statusEl.textContent = 'Correo no válido.'; return; }
            if (!isPhone(phone)) { statusEl.textContent = 'Teléfono no válido.'; return; }

            statusEl.textContent = 'Enviando…';
            try {
                const resp = await sendLead({ name, email, phone, message });
                statusEl.textContent = resp.message || 'Enviado correctamente';
                form.reset();
            } catch (err) {
                statusEl.textContent = err.message;
            }
        });
    }

    // (opcional) cargar tabla en /admin
    const table = document.getElementById('clientsTable');
    async function loadClients() {
        const res = await fetch(API.list);
        const rows = await res.json();
        const tbody = table?.querySelector('tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        for (const r of rows) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
        <td>${r.id}</td>
        <td>${r.name ?? ''}</td>
        <td>${r.email ?? ''}</td>
        <td>${r.phone ?? ''}</td>
        <td>${r.message ?? ''}</td>
        <td>${new Date(r.created_at).toLocaleString()}</td>`;
            tbody.appendChild(tr);
        }
    }
    if (table) loadClients();
})();
