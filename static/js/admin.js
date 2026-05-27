// 申论帮 - 管理后台脚本

// 管理后台API请求封装
async function adminFetch(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };

  const token = localStorage.getItem('slb_token') || localStorage.getItem('admin_token');
  if (token) {
    headers['Authorization'] = 'Bearer ' + token;
  }

  const res = await fetch('/api/admin' + url, { ...options, headers });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || '请求失败');
  }
  return data;
}

// 初始化admin页面
document.addEventListener('DOMContentLoaded', function() {
  checkAdminAuth();
  lucide.createIcons();
});

async function checkAdminAuth() {
  const token = localStorage.getItem('admin_token') || localStorage.getItem('slb_token');
  if (!token) {
    // 未登录，跳转登录
    window.location.href = '/admin/login';
    return;
  }

  try {
    const data = await adminFetch('/auth/verify');
    if (!data.data.is_admin) {
      showToast('无权限访问', 'error');
      setTimeout(() => window.location.href = '/', 1000);
    }
  } catch (e) {
    window.location.href = '/admin/login';
  }
}

// 管理后台登录
async function adminLogin(e) {
  e.preventDefault();
  const username = document.getElementById('admin-username').value;
  const password = document.getElementById('admin-password').value;

  try {
    const res = await fetch('/api/admin/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (res.ok) {
      localStorage.setItem('admin_token', data.data.token);
      showToast('登录成功');
      setTimeout(() => window.location.href = '/admin', 500);
    } else {
      showToast(data.error || '登录失败', 'error');
    }
  } catch (e) {
    showToast('登录失败', 'error');
  }
}

// 登出
function adminLogout() {
  localStorage.removeItem('admin_token');
  window.location.href = '/admin/login';
}

// Toast通知 (管理后台用)
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container') || createAdminToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.style.cssText = 'position: fixed; bottom: 20px; right: 20px; padding: 12px 24px; border-radius: 6px; color: white; z-index: 2000; animation: slideIn 0.3s ease;';
  toast.style.background = type === 'success' ? '#059669' : '#DC2626';
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function createAdminToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  document.body.appendChild(container);
  return container;
}

// 模态框操作
function openModal(title, content) {
  const modal = document.getElementById('admin-modal');
  if (!modal) return;

  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = content;
  modal.classList.add('active');
  lucide.createIcons();
}

function closeModal() {
  const modal = document.getElementById('admin-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

// 日期格式化
function formatDate(dateStr) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// 确认对话框
function confirmAction(message, callback) {
  if (confirm(message)) {
    callback();
  }
}

// 导出表格为CSV
function exportTableAsCSV(tableId, filename) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const rows = table.querySelectorAll('tr');
  let csv = [];

  rows.forEach(row => {
    const cells = row.querySelectorAll('th, td');
    const rowData = [];
    cells.forEach(cell => {
      let text = cell.innerText.replace(/"/g, '""');
      rowData.push('"' + text + '"');
    });
    csv.push(rowData.join(','));
  });

  const blob = new Blob(['\ufeff' + csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename + '.csv';
  link.click();
}