/**
 * Scripts pour l'interface d'administration.
 *
 * Gère les actions AJAX : validation d'utilisateurs,
 * suspension, et génération de tokens.
 */

/**
 * Valide ou change le statut d'un utilisateur.
 * @param {number} userId - Identifiant de l'utilisateur
 * @param {string} status - Nouveau statut (normal, vip, rejected)
 */
async function validateUser(userId, status) {
    const formData = new FormData();
    formData.append('status', status);

    try {
        const response = await fetch(`/admin/users/${userId}/validate`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (data.success) {
            updateStatusBadge(userId, status);
            showToast(`Statut mis à jour : ${status}`, 'success');
        } else {
            showToast(data.detail || 'Erreur', 'danger');
        }
    } catch (error) {
        showToast('Erreur de communication avec le serveur', 'danger');
    }
}

/**
 * Suspend un utilisateur.
 * @param {number} userId - Identifiant de l'utilisateur
 */
async function suspendUser(userId) {
    if (!confirm('Voulez-vous vraiment suspendre cet utilisateur ?')) {
        return;
    }

    try {
        const response = await fetch(`/admin/users/${userId}/suspend`, {
            method: 'POST',
        });

        const data = await response.json();

        if (data.success) {
            updateStatusBadge(userId, 'suspended');
            showToast('Utilisateur suspendu', 'warning');
        } else {
            showToast(data.detail || 'Erreur', 'danger');
        }
    } catch (error) {
        showToast('Erreur de communication avec le serveur', 'danger');
    }
}

/**
 * Ouvre la modal de génération de token.
 * @param {number} userId - Identifiant de l'utilisateur
 * @param {string} userEmail - Email de l'utilisateur
 */
function openTokenModal(userId, userEmail) {
    document.getElementById('modal-user-id').value = userId;
    document.getElementById('modal-user-email').textContent = userEmail;
    document.getElementById('token-source').value = '';
    document.getElementById('token-result').classList.add('d-none');
}

/**
 * Génère un token à partir de la chaîne source saisie.
 */
async function generateToken() {
    const userId = document.getElementById('modal-user-id').value;
    const source = document.getElementById('token-source').value.trim();

    if (!source) {
        showToast('Veuillez saisir une chaîne source ou cliquer sur Random', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('source', source);

    try {
        const response = await fetch(`/admin/users/${userId}/token`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('token-value').textContent = data.token;
            document.getElementById('token-result').classList.remove('d-none');

            // Mettre à jour l'affichage dans le tableau
            const tokenDisplay = document.getElementById(`token-display-${userId}`);
            if (tokenDisplay) {
                tokenDisplay.textContent = data.token.substring(0, 16) + '…';
            }
            const tokenSource = document.getElementById(`token-source-${userId}`);
            if (tokenSource) {
                tokenSource.textContent = data.source;
            }

            showToast('Token généré avec succès', 'success');
        } else {
            showToast(data.detail || 'Erreur lors de la génération', 'danger');
        }
    } catch (error) {
        showToast('Erreur de communication avec le serveur', 'danger');
    }
}

/**
 * Copie le token généré dans le presse-papier.
 */
function copyToken() {
    const tokenValue = document.getElementById('token-value').textContent;
    if (!tokenValue) return;

    navigator.clipboard.writeText(tokenValue).then(() => {
        showToast('Token copié dans le presse-papier', 'success');
    }).catch(err => {
        showToast('Erreur lors de la copie', 'danger');
    });
}


/**
 * Génère une chaîne aléatoire et appelle directement l'API random.
 */
async function generateRandomSource() {
    const userId = document.getElementById('modal-user-id').value;

    try {
        const response = await fetch(`/admin/users/${userId}/token/random`, {
            method: 'POST',
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('token-source').value = data.source;
            document.getElementById('token-value').textContent = data.token;
            document.getElementById('token-result').classList.remove('d-none');

            // Mettre à jour l'affichage dans le tableau
            const tokenDisplay = document.getElementById(`token-display-${userId}`);
            if (tokenDisplay) {
                tokenDisplay.textContent = data.token.substring(0, 16) + '…';
            }
            const tokenSource = document.getElementById(`token-source-${userId}`);
            if (tokenSource) {
                tokenSource.textContent = data.source;
            }

            showToast('Token aléatoire généré avec succès', 'success');
        } else {
            showToast(data.detail || 'Erreur', 'danger');
        }
    } catch (error) {
        showToast('Erreur de communication avec le serveur', 'danger');
    }
}

/**
 * Met à jour le badge de statut d'un utilisateur dans le tableau.
 * @param {number} userId - Identifiant de l'utilisateur
 * @param {string} status - Nouveau statut
 */
function updateStatusBadge(userId, status) {
    const badge = document.getElementById(`status-badge-${userId}`);
    if (!badge) return;

    // Supprimer toutes les classes de couleur
    badge.className = 'badge';

    // Ajouter la nouvelle classe
    const colorMap = {
        pending: 'bg-warning text-dark',
        normal: 'bg-success',
        vip: 'bg-info',
        rejected: 'bg-danger',
        suspended: 'bg-secondary',
    };

    badge.classList.add(...(colorMap[status] || 'bg-secondary').split(' '));
    badge.textContent = status.toUpperCase();

    // Recharger la page après un court délai pour mettre à jour les boutons
    setTimeout(() => location.reload(), 800);
}

/**
 * Affiche un toast de notification.
 * @param {string} message - Message à afficher
 * @param {string} type - Type Bootstrap (success, danger, warning, info)
 */
function showToast(message, type) {
    // Créer le conteneur de toasts s'il n'existe pas
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto"
                        data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', toastHtml);

    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();

    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}
