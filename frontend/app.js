const API_URL = 'http://127.0.0.1:8000';

// State
let currentUser = {
    id: null,
    token: null,
    profileId: null
};
let statusInterval = null;

// DOM Elements
const authScreen = document.getElementById('auth-screen');
const profileScreen = document.getElementById('profile-screen');
const dashboardScreen = document.getElementById('dashboard-screen');

const authForm = document.getElementById('auth-form');
const authBtn = document.getElementById('auth-btn');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const authError = document.getElementById('auth-error');

let isLoginMode = true;

// Init
function init() {
    const storedUserId = localStorage.getItem('user_id');
    const storedToken = localStorage.getItem('token');
    const storedProfileId = localStorage.getItem('profile_id');

    if (storedUserId) {
        currentUser = { id: storedUserId, token: storedToken, profileId: storedProfileId };
        if (storedProfileId && storedProfileId !== 'undefined') {
            showScreen('dashboard-screen');
            fetchPortfolio(); // try to load existing portfolio
        } else {
            showScreen('profile-screen');
        }
    } else {
        showScreen('auth-screen');
    }
}

// UI Navigation
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => {
        s.classList.remove('active');
        s.classList.add('hidden');
    });
    document.getElementById(screenId).classList.remove('hidden');
    document.getElementById(screenId).classList.add('active');
}

// Auth Logic
document.getElementById('auth-screen').addEventListener('click', (e) => {
    if(e.target.id === 'toggle-auth-btn') {
        isLoginMode = !isLoginMode;
        if(isLoginMode) {
            authBtn.textContent = 'Login';
            e.target.parentElement.innerHTML = `Don't have an account? <span id="toggle-auth-btn">Register</span>`;
        } else {
            authBtn.textContent = 'Register';
            e.target.parentElement.innerHTML = `Already have an account? <span id="toggle-auth-btn">Login</span>`;
        }
    }
});

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authError.textContent = '';
    const email = emailInput.value;
    const password = passwordInput.value;
    authBtn.disabled = true;

    try {
        const endpoint = isLoginMode ? '/auth/login' : '/auth/register';
        const res = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Authentication failed');

        currentUser.id = data.user_id;
        if (isLoginMode && data.token) currentUser.token = data.token;
        
        localStorage.setItem('user_id', currentUser.id);
        if (currentUser.token) localStorage.setItem('token', currentUser.token);

        showScreen('profile-screen');
    } catch (err) {
        authError.textContent = err.message;
    } finally {
        authBtn.disabled = false;
    }
});

// Profile Logic
document.getElementById('profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById('profile-error');
    errorEl.textContent = '';
    const btn = e.target.querySelector('button');
    btn.disabled = true;

    try {
        const payload = {
            user_id: currentUser.id,
            income: parseFloat(document.getElementById('income').value),
            investment_amount: parseFloat(document.getElementById('investment').value),
            duration: parseInt(document.getElementById('duration').value),
            duration_unit: document.getElementById('duration-unit').value,
            stated_risk: document.getElementById('stated-risk').value,
            risk_answers: []
        };

        const res = await fetch(`${API_URL}/profile/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Profile creation failed');

        currentUser.profileId = data.profile_id;
        localStorage.setItem('profile_id', currentUser.profileId);
        
        showScreen('dashboard-screen');
    } catch (err) {
        errorEl.textContent = err.message;
    } finally {
        btn.disabled = false;
    }
});

// Dashboard Logic
document.getElementById('logout-btn').addEventListener('click', () => {
    localStorage.clear();
    currentUser = { id: null, token: null, profileId: null };
    showScreen('auth-screen');
});

document.getElementById('edit-profile-btn').addEventListener('click', async () => {
    if (currentUser.profileId) {
        try {
            const res = await fetch(`${API_URL}/profile/${currentUser.profileId}`);
            if (res.ok) {
                const data = await res.json();
                document.getElementById('income').value = data.income || '';
                document.getElementById('investment').value = data.investment_amount || '';
                document.getElementById('duration').value = data.duration || '';
                if (data.duration_unit) {
                    document.getElementById('duration-unit').value = data.duration_unit;
                }
                if (data.stated_risk) {
                    document.getElementById('stated-risk').value = data.stated_risk;
                }
            }
        } catch (e) {
            console.error("Could not fetch profile", e);
        }
    }
    showScreen('profile-screen');
});

document.getElementById('run-analysis-btn').addEventListener('click', async () => {
    const btn = document.getElementById('run-analysis-btn');
    const loading = document.getElementById('loading-indicator');
    const results = document.getElementById('portfolio-results');
    
    btn.disabled = true;
    btn.classList.remove('pulse');
    loading.classList.remove('hidden');
    results.classList.add('hidden');
    document.getElementById('loading-status').textContent = "Waking up Agents...";

    // Start Real-Time Polling
    statusInterval = setInterval(async () => {
        try {
            const statusRes = await fetch(`${API_URL}/analysis/status/${currentUser.id}`);
            if (statusRes.ok) {
                const statusData = await statusRes.json();
                if (statusData.status) {
                    document.getElementById('loading-status').textContent = statusData.status;
                }
            }
        } catch (e) {
            console.error("Status polling failed", e);
        }
    }, 2000);

    try {
        const res = await fetch(`${API_URL}/analysis/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                profile_id: currentUser.profileId
            })
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Analysis failed');

        displayPortfolio(data);
    } catch (err) {
        alert("Error running analysis: " + err.message);
    } finally {
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }
        btn.disabled = false;
        btn.classList.add('pulse');
        loading.classList.add('hidden');
    }
});

async function fetchPortfolio() {
    // Don't fetch if we are currently running an analysis
    if (document.getElementById('run-analysis-btn').disabled) return;

    try {
        const res = await fetch(`${API_URL}/analysis/portfolio/${currentUser.id}`);
        if (res.ok) {
            const data = await res.json();
            displayPortfolio(data);
        }
    } catch (e) {
        console.log("No existing portfolio found");
    }
}

function displayPortfolio(data) {
    document.getElementById('portfolio-results').classList.remove('hidden');
    document.getElementById('expected-return').textContent = data.expected_return;
    document.getElementById('risk-type').textContent = data.risk_score.toUpperCase();
    
    const list = document.getElementById('allocation-list');
    list.innerHTML = '';
    
    // Sort allocation by weight descending
    const sortedAlloc = Object.entries(data.allocation).sort((a,b) => b[1] - a[1]);
    
    sortedAlloc.forEach(([ticker, weight]) => {
        const percentage = (weight * 100).toFixed(1) + '%';
        const li = document.createElement('li');
        li.innerHTML = `<span class="ticker">${ticker}</span> <span class="weight">${percentage}</span>`;
        list.appendChild(li);
    });

    document.getElementById('explanation-text').textContent = data.explanation;
}

// Start
init();

// History Logic
const historyScreen = document.getElementById('history-screen');

document.getElementById('history-btn').addEventListener('click', async () => {
    showScreen('history-screen');
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = '<p>Loading history...</p>';
    
    try {
        const res = await fetch(`${API_URL}/analysis/portfolios/${currentUser.id}`);
        if (res.ok) {
            const data = await res.json();
            if (data.length === 0) {
                historyList.innerHTML = '<p>No previous portfolios found.</p>';
                return;
            }
            
            historyList.innerHTML = '';
            data.forEach((portfolio, index) => {
                const card = document.createElement('div');
                card.style.border = '1px solid rgba(255,255,255,0.2)';
                card.style.padding = '15px';
                card.style.borderRadius = '8px';
                card.style.background = 'rgba(0,0,0,0.2)';
                
                const expectedReturn = portfolio.expected_return;
                const riskType = portfolio.risk_score ? portfolio.risk_score.toUpperCase() : 'UNKNOWN';
                
                let allocHtml = '<div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;">';
                const sortedAlloc = Object.entries(portfolio.allocation).sort((a,b) => b[1] - a[1]);
                sortedAlloc.forEach(([ticker, weight]) => {
                    const percentage = (weight * 100).toFixed(1) + '%';
                    allocHtml += `<span style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; font-size: 0.9em;"><strong>${ticker}</strong> ${percentage}</span>`;
                });
                allocHtml += '</div>';

                card.innerHTML = `
                    <h4 style="margin-top: 0;">Portfolio ${index + 1} <span style="font-size: 0.8em; font-weight: normal; color: #aaa;">(${riskType} Risk)</span></h4>
                    <p style="margin: 5px 0;"><strong>Expected Return:</strong> ${expectedReturn}</p>
                    ${allocHtml}
                    <button class="secondary-btn" style="margin-top: 15px; font-size: 0.9em;" onclick='loadHistoryPortfolio(${JSON.stringify(portfolio).replace(/'/g, "&#39;")})'>View Details</button>
                `;
                historyList.appendChild(card);
            });
        } else {
            historyList.innerHTML = '<p>Failed to load history.</p>';
        }
    } catch (e) {
        console.error("Could not fetch history", e);
        historyList.innerHTML = '<p>Error loading history.</p>';
    }
});

document.getElementById('back-to-dashboard-btn').addEventListener('click', () => {
    showScreen('dashboard-screen');
});

// Expose globally for inline onclick
window.loadHistoryPortfolio = function(portfolioData) {
    showScreen('dashboard-screen');
    displayPortfolio(portfolioData);
};
