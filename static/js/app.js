/**
 * 星伴·启明 前端逻辑
 */

const API_BASE = '';

// 工具函数
function getToken() {
    return localStorage.getItem('token');
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function removeToken() {
    localStorage.removeItem('token');
}

function getUser() {
    try {
        const data = localStorage.getItem('user');
        return data ? JSON.parse(data) : null;
    } catch (e) {
        return null;
    }
}

function setUser(user) {
    localStorage.setItem('user', JSON.stringify(user));
}

// API调用（带重试）
async function apiCall(path, options = {}, retries = 2) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    for (let i = 0; i <= retries; i++) {
        try {
            const resp = await fetch(`${API_BASE}${path}`, {
                ...options,
                headers,
            });

            if (resp.status === 401) {
                removeToken();
                window.location.href = '/login';
                return null;
            }

            if (!resp.ok) {
                const error = await resp.json().catch(() => ({ detail: '请求失败' }));
                throw new Error(error.detail || `HTTP ${resp.status}`);
            }

            return await resp.json();
        } catch (e) {
            if (i === retries) {
                throw e;
            }
            // 等待后重试
            await new Promise(r => setTimeout(r, 1000 * (i + 1)));
        }
    }
}

// 认证
async function register(username, password, nickname) {
    const data = await apiCall('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, password, nickname }),
    });
    if (data && data.token) {
        setToken(data.token);
        setUser({ user_id: data.user_id, username: data.username, nickname: data.nickname });
    }
    return data;
}

async function login(username, password) {
    const data = await apiCall('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
    if (data && data.token) {
        setToken(data.token);
        setUser({ user_id: data.user_id, username: data.username, nickname: data.nickname });
    }
    return data;
}

function logout() {
    removeToken();
    localStorage.removeItem('user');
    localStorage.removeItem('session_id');
    window.location.href = '/login';
}

function checkAuth() {
    if (!getToken()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// 聊天
let currentSessionId = '';
let isSending = false;

function initChat() {
    if (!checkAuth()) return;

    const user = getUser();
    const nicknameEl = document.getElementById('user-nickname');
    if (nicknameEl && user) {
        nicknameEl.textContent = user.nickname || user.username;
    }

    currentSessionId = localStorage.getItem('session_id') || generateSessionId();
    localStorage.setItem('session_id', currentSessionId);

    loadHistory();

    // 移动端输入框处理
    setupMobileInput();
}

function setupMobileInput() {
    const input = document.getElementById('chat-input');
    if (!input) return;

    // 聚焦时滚动到底部
    input.addEventListener('focus', () => {
        setTimeout(() => {
            scrollToBottom();
        }, 300);
    });
}

function generateSessionId() {
    return 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function newSession() {
    currentSessionId = generateSessionId();
    localStorage.setItem('session_id', currentSessionId);
    const container = document.getElementById('messages');
    if (container) {
        container.innerHTML = '<div class="message system">新对话已开始，试试问我数学问题吧！</div>';
    }
}

async function loadHistory() {
    try {
        const data = await apiCall(`/api/v3/chat/history/${currentSessionId}`);
        if (data && data.history) {
            const container = document.getElementById('messages');
            if (!container) return;
            container.innerHTML = '';
            if (data.history.length === 0) {
                container.innerHTML = '<div class="message system">你好！我是星伴·启明，你的AI数学辅导老师。有什么数学问题想问我吗？</div>';
            } else {
                data.history.forEach(msg => {
                    addMessage(msg.role === 'student' ? 'user' : 'assistant', msg.content);
                });
            }
            scrollToBottom();
        }
    } catch (e) {
        console.error('Load history failed:', e);
    }
}

function addMessage(role, content) {
    const container = document.getElementById('messages');
    if (!container) return;

    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.textContent = content;
    container.appendChild(div);
    scrollToBottom();
}

function showLoading() {
    const container = document.getElementById('messages');
    if (!container) return;

    const div = document.createElement('div');
    div.className = 'loading';
    div.id = 'loading-indicator';
    div.innerHTML = '<span></span><span></span><span></span>';
    container.appendChild(div);
    scrollToBottom();
}

function hideLoading() {
    const el = document.getElementById('loading-indicator');
    if (el) el.remove();
}

function scrollToBottom() {
    const container = document.getElementById('messages');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

async function sendMessage() {
    if (isSending) return;

    const input = document.getElementById('chat-input');
    if (!input) return;

    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    addMessage('user', message);
    showLoading();
    isSending = true;

    // 禁用发送按钮
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) sendBtn.disabled = true;

    try {
        const data = await apiCall('/api/v3/chat/message', {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId,
            }),
        });

        hideLoading();

        if (data && data.response) {
            addMessage('assistant', data.response);
            if (data.topic) {
                localStorage.setItem('current_topic', data.topic);
            }
        } else if (data && data.detail) {
            addMessage('system', '抱歉，出了点问题：' + data.detail);
        } else {
            addMessage('system', '抱歉，我没有收到有效回复，请重试');
        }
    } catch (e) {
        hideLoading();
        if (e.message.includes('Failed to fetch')) {
            addMessage('system', '网络连接失败，请检查网络后重试');
        } else {
            addMessage('system', '抱歉，出了点问题：' + (e.message || '请重试'));
        }
        console.error('Send failed:', e);
    } finally {
        isSending = false;
        if (sendBtn) sendBtn.disabled = false;
        input.focus();
    }
}

// 诊断
async function loadDiagnosis() {
    if (!checkAuth()) return;

    try {
        const data = await apiCall('/api/v3/student/diagnosis');
        if (data) {
            const container = document.getElementById('diagnosis-content');
            if (container && data.diagnosis) {
                container.textContent = data.diagnosis;
            }
            if (data.stats) {
                updateStats(data.stats);
            }
        }
    } catch (e) {
        console.error('Load diagnosis failed:', e);
        const container = document.getElementById('diagnosis-content');
        if (container) {
            container.textContent = '加载失败，请刷新重试';
        }
    }
}

function updateStats(stats) {
    const totalEl = document.getElementById('stat-total');
    const correctEl = document.getElementById('stat-correct');
    const accuracyEl = document.getElementById('stat-accuracy');

    if (totalEl) totalEl.textContent = stats.total || 0;
    if (correctEl) correctEl.textContent = stats.correct || 0;
    if (accuracyEl) accuracyEl.textContent = Math.round((stats.accuracy || 0) * 100) + '%';
}

// 事件绑定
document.addEventListener('DOMContentLoaded', () => {
    // 登录表单
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const btn = loginForm.querySelector('button[type="submit"]');
            if (btn) btn.disabled = true;

            try {
                const result = await login(username, password);
                if (result && result.token) {
                    window.location.href = '/chat';
                } else {
                    alert('登录失败：' + (result?.detail || '用户名或密码错误'));
                }
            } catch (err) {
                alert('登录失败：' + (err.message || '网络错误，请重试'));
            } finally {
                if (btn) btn.disabled = false;
            }
        });
    }

    // 注册表单
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('reg-username').value;
            const password = document.getElementById('reg-password').value;
            const nickname = document.getElementById('reg-nickname').value;
            const btn = registerForm.querySelector('button[type="submit"]');
            if (btn) btn.disabled = true;

            try {
                const result = await register(username, password, nickname);
                if (result && result.token) {
                    window.location.href = '/chat';
                } else {
                    alert('注册失败：' + (result?.detail || '用户名可能已存在'));
                }
            } catch (err) {
                alert('注册失败：' + (err.message || '网络错误，请重试'));
            } finally {
                if (btn) btn.disabled = false;
            }
        });
    }

    // 聊天输入
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // 发送按钮
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }

    // 新对话按钮
    const newChatBtn = document.getElementById('new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', newSession);
    }

    // 初始化
    if (document.querySelector('.chat-page')) {
        initChat();
    }
    if (document.querySelector('.diagnosis-page')) {
        loadDiagnosis();
    }
});
