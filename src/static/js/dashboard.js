/**
 * Scripts pour le tableau de bord utilisateur.
 *
 * Gère la connexion SSE pour l'affichage en temps réel
 * de la file d'attente des requêtes.
 */

const APP_PREFIX = document.querySelector('meta[name="app-prefix"]')?.content || '';

document.addEventListener('DOMContentLoaded', function () {
    initQueuePolling();
});

/**
 * Initialise le polling (requêtes périodiques) pour recevoir les mises à jour
 * de la file d'attente en temps réel, remplaçant l'ancienne méthode SSE.
 */
function initQueuePolling() {
    const pollInterval = 2500; // 2.5 secondes

    async function fetchQueueStatus() {
        try {
            const response = await fetch(`${APP_PREFIX}/api/v1/queue/status`, {
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    // Non authentifié, redirection vers login
                    window.location.href = `${APP_PREFIX}/login`;
                    return;
                }
                throw new Error(`Erreur HTTP: ${response.status}`);
            }

            const data = await response.json();
            updateQueueDisplay(data);
        } catch (e) {
            console.error('Erreur lors du polling :', e);
            const indicator = document.getElementById('queue-indicator');
            if (indicator) {
                indicator.innerHTML = '<span class="text-danger"><i class="bi bi-wifi-off me-1"></i>Déconnecté</span>';
            }
        }
    }

    // Lancer le premier appel immédiatement
    fetchQueueStatus();

    // Configurer les appels réguliers
    setInterval(fetchQueueStatus, pollInterval);
}

/**
 * Met à jour l'affichage de la file d'attente à partir des données SSE.
 * @param {object} data - Données de la file d'attente
 */
function updateQueueDisplay(data) {
    // Mettre à jour le compteur de file
    const queueLength = document.getElementById('queue-length');
    if (queueLength) {
        queueLength.textContent = `File : ${data.queue_length || 0}`;
    }

    // Mettre à jour les requêtes restantes
    if (data.remaining_requests !== undefined) {
        const remaining = document.getElementById('remaining-requests');
        if (remaining) {
            if (data.remaining_requests >= 9999) {
                remaining.textContent = '∞';
                remaining.className = 'fw-bold fs-4 text-info';
            } else {
                remaining.textContent = data.remaining_requests;
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
    }

    // Mettre à jour la section "en cours de traitement"
    const processingSection = document.getElementById('processing-section');
    const processingId = document.getElementById('processing-id');

    if (data.processing) {
        if (processingSection) processingSection.classList.remove('d-none');
        if (processingId) processingId.textContent = `ID : ${data.processing.request_id}`;
    } else {
        if (processingSection) processingSection.classList.add('d-none');
    }

    // Mettre à jour les tableaux
    const queueTableBody = document.getElementById('queue-table-body');
    const historyTableBody = document.getElementById('history-table-body');
    if (!queueTableBody || !historyTableBody) return;

    let activeItems = 0;
    let queueHtml = '';
    let historyHtml = '';

    if (data.items && data.items.length > 0) {
        data.items.forEach(function (item) {
            const statusClass = getStatusClass(item.status);

            // Filtrage strict par statut pour éviter les doublons entre tableaux
            if (item.status === 'waiting' || item.status === 'processing') {
                activeItems++;
                queueHtml += `
                    <tr>
                        <td class="font-monospace small">${item.request_id}</td>
                        <td><span class="badge ${statusClass}">${item.status}</span></td>
                        <td>${item.position >= 0 ? '#' + (item.position + 1) : '—'}</td>
                    </tr>
                `;
            } else if (item.status === 'completed' || item.status === 'failed') {
                let actionHtml = '—';
                if (item.status === 'completed') {
                    actionHtml = `
                    <a href="${APP_PREFIX}/api/v1/traits/get_character/${item.request_id}" target="_blank" class="btn btn-sm btn-outline-info">
                        <i class="bi bi-download"></i> JSON
                    </a>`;
                } else if (item.status === 'failed') {
                    const errorMsg = item.error ? item.error.replace(/"/g, '&quot;') : 'Erreur inconnue';
                    actionHtml = `<span class="text-danger small" title="${errorMsg}"><i class="bi bi-exclamation-triangle"></i> Erreur</span>`;
                }

                historyHtml += `
                    <tr>
                        <td class="font-monospace small">${item.request_id}</td>
                        <td><span class="badge ${statusClass}">${item.status}</span></td>
                        <td>${actionHtml}</td>
                    </tr>
                `;
            }
        });
    }

    if (activeItems > 0) {
        queueTableBody.innerHTML = queueHtml;
    } else {
        queueTableBody.innerHTML = `
            <tr id="no-requests-row">
                <td colspan="3" class="text-center text-muted py-4">
                    <i class="bi bi-inbox display-6 d-block mb-2"></i>
                    Aucune requête en attente
                </td>
            </tr>
        `;
    }

    if (historyHtml.length > 0) {
        historyTableBody.innerHTML = historyHtml;
    } else {
        historyTableBody.innerHTML = `
            <tr id="no-history-row">
                <td colspan="3" class="text-center text-muted py-4">
                    <i class="bi bi-journal-x display-6 d-block mb-2"></i>
                    Aucun historique disponible
                </td>
            </tr>
        `;
    }

    // Indicateur de connexion (on affiche un texte vert pour montrer que c'est actif après mise à jour)
    const indicator = document.getElementById('queue-indicator');
    if (indicator) {
        indicator.innerHTML = '<span class="spinner-grow spinner-grow-sm text-primary" role="status"></span> <small class="text-primary fw-bold ms-1">En direct</small>';
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
