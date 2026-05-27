// 申论帮 - 全局应用脚本

// 全局状态
const state = {
  token: localStorage.getItem('slb_token'),
  user: null
};

// DOM准备就绪
document.addEventListener('DOMContentLoaded', function() {
  initApp();
});

async function initApp() {
  // 检查登录状态
  if (state.token) {
    await loadUserInfo();
  }

  // 初始化UI组件
  lucide.createIcons();

  // 绑定导航事件
  initNavigation();
}

async function loadUserInfo() {
  try {
    const res = await fetch('/api/auth/me', {
      headers: { 'Authorization': 'Bearer ' + state.token }
    });
    if (res.ok) {
      const { data } = await res.json();
      state.user = data;
      updateUserUI();
    } else {
      logout();
    }
  } catch (e) {
    console.error('Failed to load user info:', e);
  }
}

function updateUserUI() {
  const userElements = document.querySelectorAll('.user-nickname, #user-nickname');
  const authButtons = document.querySelectorAll('.auth-buttons, #auth-buttons');
  const vipBadge = document.querySelector('.vip-badge, #vip-badge');

  userElements.forEach(el => {
    if (state.user) {
      el.textContent = state.user.nickname || state.user.username;
      el.style.display = '';
    } else {
      el.style.display = 'none';
    }
  });

  authButtons.forEach(el => {
    if (state.user) {
      el.style.display = 'none';
    } else {
      el.style.display = '';
    }
  });

  if (vipBadge && state.user) {
    if (isVIP(state.user)) {
      vipBadge.style.display = '';
    } else {
      vipBadge.style.display = 'none';
    }
  }
}

function isVIP(user) {
  if (!user) return false;
  if (user.role === 'admin' || user.role === 'super_admin') return true;
  if (user.vip_expire) {
    return new Date(user.vip_expire) > new Date();
  }
  return false;
}

function initNavigation() {
  // 移动端菜单切换
  const menuToggle = document.querySelector('.menu-toggle');
  const navbar = document.querySelector('.navbar');
  if (menuToggle && navbar) {
    menuToggle.addEventListener('click', () => {
      navbar.classList.toggle('active');
    });
  }
}

// 认证模态框
function openAuthModal(mode = 'login') {
  const modal = document.getElementById('auth-modal');
  if (!modal) return;

  const title = document.getElementById('auth-modal-title');
  const body = document.getElementById('auth-modal-body');

  if (mode === 'login') {
    title.textContent = '登录';
    body.innerHTML = `
      <form onsubmit="handleLogin(event)">
        <div class="form-group">
          <input type="text" id="login-username" class="input-field" placeholder="用户名" required>
        </div>
        <div class="form-group">
          <input type="password" id="login-password" class="input-field" placeholder="密码" required>
        </div>
        <button type="submit" class="btn btn-primary btn-block">登录</button>
        <p class="text-center" style="margin-top: var(--space-2);">
          还没有账号？<a href="#" onclick="openAuthModal('register'); return false;">立即注册</a>
        </p>
      </form>
    `;
  } else {
    title.textContent = '注册';
    body.innerHTML = `
      <form onsubmit="handleRegister(event)">
        <div class="form-group">
          <input type="text" id="register-username" class="input-field" placeholder="用户名 (4-20位)" required minlength="4" maxlength="20">
        </div>
        <div class="form-group">
          <input type="password" id="register-password" class="input-field" placeholder="密码 (6位以上)" required minlength="6">
        </div>
        <div class="form-group">
          <input type="password" id="register-confirm" class="input-field" placeholder="确认密码" required>
        </div>
        <div class="form-group">
          <input type="text" id="register-nickname" class="input-field" placeholder="昵称 (选填)">
        </div>
        <button type="submit" class="btn btn-primary btn-block">注册</button>
        <p class="text-center" style="margin-top: var(--space-2);">
          已有账号？<a href="#" onclick="openAuthModal('login'); return false;">立即登录</a>
        </p>
      </form>
    `;
  }

  modal.classList.add('active');
  lucide.createIcons();
}

function closeAuthModal() {
  const modal = document.getElementById('auth-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (res.ok) {
      localStorage.setItem('slb_token', data.data.token);
      state.token = data.data.token;
      await loadUserInfo();
      closeAuthModal();
      showToast('登录成功');
      setTimeout(() => location.reload(), 500);
    } else {
      showToast(data.error || '登录失败', 'error');
    }
  } catch (e) {
    showToast('登录失败', 'error');
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const username = document.getElementById('register-username').value;
  const password = document.getElementById('register-password').value;
  const confirm = document.getElementById('register-confirm').value;
  const nickname = document.getElementById('register-nickname').value;

  if (password !== confirm) {
    showToast('两次密码不一致', 'error');
    return;
  }

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, nickname })
    });

    const data = await res.json();

    if (res.ok) {
      localStorage.setItem('slb_token', data.data.token);
      state.token = data.data.token;
      await loadUserInfo();
      closeAuthModal();
      showToast('注册成功');
      setTimeout(() => location.reload(), 500);
    } else {
      showToast(data.error || '注册失败', 'error');
    }
  } catch (e) {
    showToast('注册失败', 'error');
  }
}

function logout() {
  localStorage.removeItem('slb_token');
  state.token = null;
  state.user = null;
  updateUserUI();
  showToast('已退出登录');
  if (window.location.pathname !== '/') {
    window.location.href = '/';
  }
}

// Toast通知
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <i data-lucide="${type === 'success' ? 'check-circle' : 'alert-circle'}"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  lucide.createIcons();
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.className = 'toast-container';
  document.body.appendChild(container);
  return container;
}

// API请求封装
async function apiFetch(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };

  if (state.token) {
    headers['Authorization'] = 'Bearer ' + state.token;
  }

  const res = await fetch(url, { ...options, headers });
  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.error || '请求失败');
  }
  return data;
}

// 日期格式化
function formatDate(dateStr) {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// 数字格式化
function formatNumber(num) {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万';
  }
  return num.toString();
}