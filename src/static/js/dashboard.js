/**
 * Scripts pour le tableau de bord utilisateur.
 *
 * Gère la connexion SSE pour l'affichage en temps réel
 * de la file d'attente des requêtes.
 */

const APP_PREFIX = document.querySelector('meta[name="app-prefix"]')?.content || '';

document.addEventListener('DOMContentLoaded', function () {
    initQueueSSE();
});

/**
 * Initialise la connexion SSE pour recevoir les mises à jour
 * de la file d'attente en temps réel.
 */
function initQueueSSE() {
    const evtSource = new EventSource(`${APP_PREFIX}/api/v1/queue/status`);

    evtSource.onmessage = function (event) {
        try {
            const data = JSON.parse(event.data);
            updateQueueDisplay(data);
        } catch (e) {
            console.error('Erreur de parsing SSE :', e);
        }
    };

    evtSource.onerror = function () {
        console.warn('Connexion SSE perdue, reconnexion dans 5s…');
        const indicator = document.getElementById('queue-indicator');
        if (indicator) {
            indicator.innerHTML = '<span class="text-danger"><i class="bi bi-wifi-off me-1"></i>Déconnecté</span>';
        }

        // Tenter de reconnecter après 5s
        setTimeout(function () {
            evtSource.close();
            initQueueSSE();
        }, 5000);
    };
}

/**
 * Met à jour l'affichage de la file d'attente à partir des données SSE.
 * @param {object} data - Données de la file d'attente
 */
function updateQueueDisplay(data) {
    // Mettre à jour le compteur de file
    const queueLength = document.getElementById('queue-length');
    if (queueLength) {
        queueLength.textContent = `File : ${data.queue_length}`;
    }

    // Mettre à jour les requêtes restantes
    if (data.remaining_requests !== undefined) {
        const remaining = document.getElementById('remaining-requests');
        if (remaining) {
            remaining.textContent = data.remaining_requests;

            // Mettre à jour la couleur
            remaining.className = 'fw-bold fs-4';
            if (data.remaining_requests > 10) {
                remaining.classList.add('text-success');
            } else if (data.remaining_requests > 3) {
                remaining.classList.add('text-warning');
            } else {
                remaining.classList.add('text-danger');
            }
        }
    }

    // Mettre à jour la section "en cours de traitement"
    const processingSection = document.getElementById('processing-section');
    const processingId = document.getElementById('processing-id');

    if (data.processing) {
        processingSection.classList.remove('d-none');
        processingId.textContent = `ID : ${data.processing.request_id}`;
    } else {
        processingSection.classList.add('d-none');
    }

    // Mettre à jour le tableau des requêtes
    const tableBody = document.getElementById('queue-table-body');
    if (!tableBody) return;

    if (data.items && data.items.length > 0) {
        let html = '';
        data.items.forEach(function (item) {
            const statusClass = getStatusClass(item.status);
            html += `
                <tr>
                    <td class="font-monospace small">${item.request_id}</td>
                    <td><span class="badge ${statusClass}">${item.status}</span></td>
                    <td>${item.position >= 0 ? '#' + (item.position + 1) : '—'}</td>
                </tr>
            `;
        });
        tableBody.innerHTML = html;
    } else if (!data.processing) {
        tableBody.innerHTML = `
            <tr id="no-requests-row">
                <td colspan="3" class="text-center text-muted py-4">
                    <i class="bi bi-inbox display-6 d-block mb-2"></i>
                    Aucune requête pour le moment
                </td>
            </tr>
        `;
    }

    // Indicateur de connexion
    const indicator = document.getElementById('queue-indicator');
    if (indicator) {
        indicator.innerHTML = '<span class="spinner-grow spinner-grow-sm text-primary" role="status"></span> <small class="text-muted">Temps réel</small>';
    }
}

/**
 * Retourne la classe CSS pour un statut donné.
 * @param {string} status - Statut de la requête
 * @returns {string} Classe CSS Bootstrap
 */
function getStatusClass(status) {
    const map = {
        waiting: 'bg-warning text-dark',
        processing: 'bg-primary',
        completed: 'bg-success',
        failed: 'bg-danger',
    };
    return map[status] || 'bg-secondary';
}

/**
 * Copie le token API dans le presse-papiers.
 */
function copyToken() {
    const tokenInput = document.getElementById('token-display');
    if (tokenInput) {
        tokenInput.select();
        navigator.clipboard.writeText(tokenInput.value).then(function () {
            const btn = tokenInput.nextElementSibling;
            const originalHtml = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-check2"></i>';
            btn.classList.add('btn-success');
            btn.classList.remove('btn-outline-secondary');

            setTimeout(function () {
                btn.innerHTML = originalHtml;
                btn.classList.remove('btn-success');
                btn.classList.add('btn-outline-secondary');
            }, 2000);
        });
    }
}
