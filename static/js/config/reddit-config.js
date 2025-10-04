function populateRedditConfig(config) {
    const clientIdEl = document.getElementById('reddit-client-id');
    const clientSecretEl = document.getElementById('reddit-client-secret');
    const intervalEl = document.getElementById('reddit-interval');

    if (clientIdEl) clientIdEl.value = config.client_id || '';
    if (clientSecretEl) clientSecretEl.value = config.client_secret || '';
    if (intervalEl) intervalEl.value = config.check_interval || 300;
}

function populateDropWindowConfig(config) {
    const windowToggle = document.getElementById('window-enabled');
    const windowConfig = document.getElementById('reddit-window-config');

    if (windowToggle) {
        windowToggle.checked = config.enabled !== false;
        if (windowConfig) {
            windowConfig.style.display = config.enabled !== false ? 'block' : 'none';
        }
    }
    document.getElementById('window-timezone').value = config.timezone || 'America/New_York';

    const startTime = `${String(config.start_hour || 12).padStart(2, '0')}:${String(config.start_minute || 0).padStart(2, '0')}`;
    const endTime = `${String(config.end_hour || 17).padStart(2, '0')}:${String(config.end_minute || 0).padStart(2, '0')}`;

    document.getElementById('window-start-time').value = startTime;
    document.getElementById('window-end-time').value = endTime;

    const activeDays = config.days_of_week || [4];
    for (let i = 0; i <= 6; i++) {
        const checkbox = document.getElementById(`day-${i}`);
        if (checkbox) {
            checkbox.checked = activeDays.includes(i);
        }
    }
}

async function handleRedditConfigSubmit(e) {
    e.preventDefault();

    const redditConfig = {
        client_id: document.getElementById('reddit-client-id').value,
        client_secret: document.getElementById('reddit-client-secret').value,
        user_agent: 'FragDropDetector/1.0',
        subreddit: 'MontagneParfums',
        check_interval: parseInt(document.getElementById('reddit-interval').value),
        post_limit: 50
    };

    if (!redditConfig.client_id || !redditConfig.client_secret) {
        showAlert('Please fill in all required Reddit credentials', 'error');
        return;
    }

    const enabled = document.getElementById('window-enabled').checked;
    const timezone = document.getElementById('window-timezone').value;
    const startTime = document.getElementById('window-start-time').value.split(':');
    const endTime = document.getElementById('window-end-time').value.split(':');

    const days = [];
    for (let i = 0; i <= 6; i++) {
        const checkbox = document.getElementById(`day-${i}`);
        if (checkbox && checkbox.checked) {
            days.push(i);
        }
    }

    const dropWindowConfig = {
        enabled,
        timezone,
        days_of_week: days,
        start_hour: parseInt(startTime[0]),
        start_minute: parseInt(startTime[1]),
        end_hour: parseInt(endTime[0]),
        end_minute: parseInt(endTime[1])
    };

    if (enabled && days.length === 0) {
        showAlert('Please select at least one day when time restrictions are enabled', 'error');
        return;
    }

    try {
        setLoading('reddit-form', true);
        await saveRedditConfig(redditConfig);
        await saveDropWindowConfig(dropWindowConfig);
        const refreshedConfig = await loadConfig(true);
        if (refreshedConfig) {
            populateRedditConfig(refreshedConfig.reddit || {});
            populateDropWindowConfig(refreshedConfig.drop_window || {});
        }
    } catch (error) {
        // Error already shown
    } finally {
        setLoading('reddit-form', false);
    }
}

async function updateRedditAuthStatus() {
    try {
        const config = await loadConfig();
        const redditConfig = config.reddit || {};

        const authBanner = document.getElementById('reddit-auth-banner');
        const authSuccess = document.getElementById('reddit-auth-success');
        const authUserInfo = document.getElementById('auth-user-info');

        if (redditConfig.authenticated && redditConfig.username) {
            authBanner.style.display = 'none';
            authSuccess.style.display = 'flex';
            authUserInfo.textContent = `Authenticated as u/${redditConfig.username}`;
        } else {
            authBanner.style.display = 'flex';
            authSuccess.style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to update Reddit auth status:', error);
    }
}

function showAuthSetupModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal auth-setup-modal">
            <div class="modal-header">
                <h2>Reddit Authentication Setup</h2>
                <button class="modal-close" onclick="closeAuthSetupModal()">&times;</button>
            </div>
            <div class="modal-content">
                <p>User authentication is required to monitor r/MontagneParfums and access member-only posts.</p>

                <div class="setup-steps">
                    <div class="step">
                        <div class="step-number">1</div>
                        <div class="step-content">
                            <h4>SSH with Port Forwarding</h4>
                            <p>Connect to your Pi with port forwarding:</p>
                            <div class="code-block">
                                <code>ssh -L 8080:localhost:8080 pi@${window.location.hostname}</code>
                            </div>
                        </div>
                    </div>

                    <div class="step">
                        <div class="step-number">2</div>
                        <div class="step-content">
                            <h4>Run Authentication Script</h4>
                            <p>In your SSH session, run:</p>
                            <div class="code-block">
                                <code>python generate_token_headless.py</code>
                            </div>
                        </div>
                    </div>

                    <div class="step">
                        <div class="step-number">3</div>
                        <div class="step-content">
                            <h4>Authorize in Browser</h4>
                            <p>Follow the script instructions to authorize in your local browser.</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn secondary" onclick="closeAuthSetupModal()">Close</button>
                <button class="btn primary" onclick="checkAuthStatus()">Check Status</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeAuthSetupModal();
    });
}

function closeAuthSetupModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
        modal.remove();
    }
}

async function checkAuthStatus() {
    await updateRedditAuthStatus();
    closeAuthSetupModal();
    showToast('Authentication status updated', 'success');
}
