/* ========================================
   SLB 组件库 JS —— 交互逻辑
   ======================================== */

(function () {
  'use strict';

  /* ========================================
     Toast 通知系统
     ======================================== */
  const SLBToast = {
    container: null,

    init() {
      this.container = document.getElementById('toast-container');
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        document.body.appendChild(this.container);
      }
    },

    show({ type = 'info', title = '', message = '', duration = 3000 }) {
      if (!this.container) this.init();

      const icons = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>',
        error:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
        warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>',
        info:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/></svg>'
      };

      const toast = document.createElement('div');
      toast.className = `toast toast-${type}`;
      toast.innerHTML = `
        <div class="toast-icon">${icons[type] || icons.info}</div>
        <div class="toast-body">
          ${title ? `<div class="toast-title">${title}</div>` : ''}
          <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" aria-label="关闭">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      `;

      this.container.appendChild(toast);

      const close = () => {
        toast.classList.add('toast-exit');
        toast.addEventListener('animationend', () => toast.remove());
      };

      toast.querySelector('.toast-close').addEventListener('click', close);
      if (duration > 0) setTimeout(close, duration);
    },

    success(msg, title) { this.show({ type: 'success', title, message: msg }); },
    error(msg, title)   { this.show({ type: 'error', title, message: msg, duration: 5000 }); },
    warning(msg, title) { this.show({ type: 'warning', title, message: msg, duration: 4000 }); },
    info(msg, title)    { this.show({ type: 'info', title, message: msg }); }
  };

  window.SLBToast = SLBToast;

  /* ========================================
     AI 批改进度条
     ======================================== */
  const GradingProgress = {
    bar: null,
    container: null,
    steps: [],

    init() {
      this.container = document.querySelector('.grading-progress');
      this.bar = document.querySelector('.grading-progress-bar');
      this.steps = document.querySelectorAll('.grading-step');
    },

    start() {
      if (!this.container) this.init();
      this.container?.classList.add('active');
      this.setPercent(10);
    },

    setPercent(pct) {
      if (this.bar) this.bar.style.width = Math.min(pct, 100) + '%';
    },

    nextStep(index) {
      // 完成当前步骤，激活下一步
      this.steps.forEach((step, i) => {
        if (i < index) step.classList.add('done');
        if (i === index) step.classList.add('active');
      });
      const pctMap = [25, 50, 75, 100];
      this.setPercent(pctMap[index] || 100);
    },

    finish() {
      this.setPercent(100);
      this.steps.forEach(s => s.classList.add('done'));
      setTimeout(() => {
        this.container?.classList.remove('active');
        // 重置
        this.steps.forEach(s => { s.classList.remove('done', 'active'); });
        if (this.bar) this.bar.style.width = '0';
      }, 800);
    }
  };

  window.SLBGradingProgress = GradingProgress;

  /* ========================================
     移动端汉堡菜单
     ======================================== */
  function initMobileMenu() {
    const toggle = document.querySelector('.navbar-toggle');
    const menu = document.querySelector('.navbar-menu');
    if (!toggle || !menu) return;

    const syncAria = () => {
      toggle.setAttribute('aria-expanded', menu.classList.contains('open') ? 'true' : 'false');
    };

    toggle.addEventListener('click', () => {
      toggle.classList.toggle('open');
      menu.classList.toggle('open');
      document.body.style.overflow = menu.classList.contains('open') ? 'hidden' : '';
      syncAria();
    });

    // 点击菜单项后关闭
    menu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        toggle.classList.remove('open');
        menu.classList.remove('open');
        document.body.style.overflow = '';
        syncAria();
      });
    });

    // ESC 关闭
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && menu.classList.contains('open')) {
        toggle.classList.remove('open');
        menu.classList.remove('open');
        document.body.style.overflow = '';
        syncAria();
      }
    });
  }

  /* ========================================
     Tab 页签
     ======================================== */
  function initTabs() {
    document.querySelectorAll('.tabs').forEach(tabGroup => {
      const tabs = tabGroup.querySelectorAll('.tab');
      const containerId = tabGroup.dataset.tabGroup;
      const contents = document.querySelectorAll(`[data-tab-content="${containerId}"] .tab-content`);

      tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          const target = tab.dataset.tab;

          tabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');

          contents.forEach(c => {
            c.classList.toggle('active', c.dataset.tab === target);
          });
        });
      });
    });
  }

  /* ========================================
     下拉菜单
     ======================================== */
  function initDropdowns() {
    document.querySelectorAll('.dropdown').forEach(dropdown => {
      const trigger = dropdown.querySelector('.dropdown-trigger');
      const menu = dropdown.querySelector('.dropdown-menu');
      if (!trigger || !menu) return;

      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        // 关闭其他下拉
        document.querySelectorAll('.dropdown-menu.open').forEach(m => {
          if (m !== menu) m.classList.remove('open');
        });
        menu.classList.toggle('open');
      });
    });

    // 点击外部关闭
    document.addEventListener('click', () => {
      document.querySelectorAll('.dropdown-menu.open').forEach(m => {
        m.classList.remove('open');
      });
    });
  }

  /* ========================================
     搜索框 (带自动补全)
     ======================================== */
  function initSearchBoxes() {
    document.querySelectorAll('.search-box').forEach(box => {
      const input = box.querySelector('.search-input');
      const clearBtn = box.querySelector('.search-clear');
      const suggestions = box.querySelector('.search-suggestions');
      if (!input) return;

      // 显示/隐藏清除按钮
      input.addEventListener('input', () => {
        clearBtn?.classList.toggle('visible', input.value.length > 0);
      });

      // 清除
      clearBtn?.addEventListener('click', () => {
        input.value = '';
        clearBtn.classList.remove('visible');
        suggestions?.classList.remove('open');
        input.focus();
      });

      // ESC 关闭建议
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          suggestions?.classList.remove('open');
        }
      });
    });
  }

  /* ========================================
     手风琴 / 折叠面板
     ======================================== */
  function initAccordions() {
    document.querySelectorAll('.accordion').forEach(accordion => {
      const items = accordion.querySelectorAll('.accordion-item');

      items.forEach(item => {
        const trigger = item.querySelector('.accordion-trigger');
        const content = item.querySelector('.accordion-content');
        if (!trigger || !content) return;

        trigger.addEventListener('click', () => {
          const isOpen = item.classList.contains('open');

          // 关闭其他（手风琴模式，如需独立展开则注释掉）
          items.forEach(other => {
            if (other !== item) {
              other.classList.remove('open');
              const otherContent = other.querySelector('.accordion-content');
              if (otherContent) otherContent.style.maxHeight = '0';
            }
          });

          if (isOpen) {
            item.classList.remove('open');
            content.style.maxHeight = '0';
          } else {
            item.classList.add('open');
            content.style.maxHeight = content.scrollHeight + 'px';
          }
        });
      });
    });
  }

  /* ========================================
     返回顶部
     ======================================== */
  function initBackToTop() {
    const btn = document.querySelector('.back-to-top');
    if (!btn) return;

    const toggleVisibility = () => {
      btn.classList.toggle('visible', window.scrollY > 300);
    };

    window.addEventListener('scroll', toggleVisibility, { passive: true });
    toggleVisibility();

    btn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ========================================
     得分环动画
     ======================================== */
  function initScoreRings() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const ring = entry.target;
          const pct = parseFloat(ring.dataset.score) || 0;
          const circle = ring.querySelector('.score-ring-fill');
          if (!circle) return;

          const radius = parseFloat(circle.getAttribute('r'));
          const circumference = 2 * Math.PI * radius;
          circle.style.strokeDasharray = circumference;
          circle.style.strokeDashoffset = circumference;

          // 颜色分级
          ring.classList.remove('high', 'mid', 'low');
          if (pct >= 80) ring.classList.add('high');
          else if (pct >= 60) ring.classList.add('mid');
          else ring.classList.add('low');

          requestAnimationFrame(() => {
            circle.style.strokeDashoffset = circumference * (1 - pct / 100);
          });

          observer.unobserve(ring);
        }
      });
    }, { threshold: 0.3 });

    document.querySelectorAll('.score-ring').forEach(ring => observer.observe(ring));
  }

  /* ========================================
     数字滚动 (countUp)
     ======================================== */
  function countUp(el, target, duration = 800) {
    const start = 0;
    const startTime = performance.now();
    const isFloat = String(target).includes('.');

    function update(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = start + (target - start) * eased;
      el.textContent = isFloat ? current.toFixed(1) : Math.round(current);
      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }

  // 自动初始化带 .counter[data-target] 的元素
  function initCounters() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const target = parseFloat(el.dataset.target);
          if (!isNaN(target)) countUp(el, target);
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.3 });

    document.querySelectorAll('.counter[data-target]').forEach(el => observer.observe(el));
  }

  /* ========================================
     全局初始化
     ======================================== */
  function init() {
    SLBToast.init();
    initMobileMenu();
    initTabs();
    initDropdowns();
    initSearchBoxes();
    initAccordions();
    initBackToTop();
    initScoreRings();
    initCounters();
    GradingProgress.init();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* ========================================
     Chart.js 图表组件
     ======================================== */

  // Chart.js 全局默认配置
  if (typeof Chart !== 'undefined') {
    Chart.defaults.font.family = "'Noto Sans SC', 'Inter', -apple-system, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = '#6b7280';
    Chart.defaults.plugins.legend.display = false;
    Chart.defaults.animation.duration = 600;
    Chart.defaults.animation.easing = 'easeOutQuart';
  }

  const SLBCharts = {
    // SLB 品牌色板
    colors: {
      primary: '#1e3a5f',
      primaryLight: 'rgba(30, 58, 95, 0.15)',
      accent: '#b8942e',
      accentLight: 'rgba(184, 148, 46, 0.15)',
      success: '#2d8a56',
      warning: '#c47d1a',
      error: '#c03636',
      gray: '#9ca3af',
      palette: ['#1e3a5f', '#b8942e', '#2d8a56', '#c47d1a', '#c03636', '#5b8abf', '#7c6da0']
    },

    /**
     * 雷达图 — 能力诊断五维度
     * @param {string} canvasId
     * @param {object} opts - { labels: [], data: [], label: '' }
     */
    radar(canvasId, opts) {
      const ctx = document.getElementById(canvasId);
      if (!ctx) return null;
      return new Chart(ctx, {
        type: 'radar',
        data: {
          labels: opts.labels || ['踩点命中', '逻辑结构', '语言规范', '字数控制', '卷面整洁'],
          datasets: [{
            label: opts.label || '能力值',
            data: opts.data || [],
            backgroundColor: this.colors.primaryLight,
            borderColor: this.colors.primary,
            borderWidth: 2,
            pointBackgroundColor: this.colors.primary,
            pointRadius: 4,
            pointHoverRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          scales: {
            r: {
              beginAtZero: true,
              max: opts.max || 100,
              ticks: { stepSize: 20, font: { size: 10 } },
              grid: { color: 'rgba(0,0,0,0.06)' },
              angleLines: { color: 'rgba(0,0,0,0.06)' },
              pointLabels: { font: { size: 12, weight: '500' }, color: '#374151' }
            }
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: '#1f2937',
              padding: 10,
              cornerRadius: 8,
              titleFont: { weight: '600' }
            }
          }
        }
      });
    },

    /**
     * 柱状图 — 得分分布 / 对比
     * @param {string} canvasId
     * @param {object} opts - { labels: [], datasets: [{label, data, color}] }
     */
    bar(canvasId, opts) {
      const ctx = document.getElementById(canvasId);
      if (!ctx) return null;
      const datasets = (opts.datasets || []).map((ds, i) => ({
        label: ds.label || '',
        data: ds.data || [],
        backgroundColor: ds.color || this.colors.palette[i],
        borderRadius: 6,
        borderSkipped: false,
        barPercentage: 0.6,
        categoryPercentage: 0.7
      }));
      return new Chart(ctx, {
        type: 'bar',
        data: { labels: opts.labels || [], datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { display: false } },
            y: {
              beginAtZero: true,
              max: opts.max || 100,
              grid: { color: 'rgba(0,0,0,0.04)' },
              ticks: { font: { size: 11 } }
            }
          },
          plugins: {
            legend: { display: datasets.length > 1, position: 'top', labels: { usePointStyle: true, padding: 16 } },
            tooltip: { backgroundColor: '#1f2937', padding: 10, cornerRadius: 8 }
          }
        }
      });
    },

    /**
     * 折线图 — 学习趋势
     * @param {string} canvasId
     * @param {object} opts - { labels: [], datasets: [{label, data, color}] }
     */
    line(canvasId, opts) {
      const ctx = document.getElementById(canvasId);
      if (!ctx) return null;
      const datasets = (opts.datasets || []).map((ds, i) => ({
        label: ds.label || '',
        data: ds.data || [],
        borderColor: ds.color || this.colors.palette[i],
        backgroundColor: (ds.color || this.colors.palette[i]) + '15',
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        fill: true,
        tension: 0.3
      }));
      return new Chart(ctx, {
        type: 'line',
        data: { labels: opts.labels || [], datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { display: false } },
            y: {
              beginAtZero: opts.beginAtZero !== false,
              max: opts.max,
              grid: { color: 'rgba(0,0,0,0.04)' }
            }
          },
          plugins: {
            legend: { display: datasets.length > 1, position: 'top', labels: { usePointStyle: true, padding: 16 } },
            tooltip: { backgroundColor: '#1f2937', padding: 10, cornerRadius: 8 }
          }
        }
      });
    },

    /**
     * 环形图 — 题型得分率
     * @param {string} canvasId
     * @param {object} opts - { labels: [], data: [], colors: [] }
     */
    doughnut(canvasId, opts) {
      const ctx = document.getElementById(canvasId);
      if (!ctx) return null;
      return new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: opts.labels || [],
          datasets: [{
            data: opts.data || [],
            backgroundColor: opts.colors || this.colors.palette,
            borderWidth: 0,
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          cutout: '65%',
          plugins: {
            legend: { display: false },
            tooltip: { backgroundColor: '#1f2937', padding: 10, cornerRadius: 8 }
          }
        }
      });
    },

    /**
     * 进度条图 — 各维度得分
     * @param {string} containerId
     * @param {object} opts - { items: [{label, value, max, color}] }
     */
    progressBars(containerId, opts) {
      const container = document.getElementById(containerId);
      if (!container) return;
      container.innerHTML = '';

      (opts.items || []).forEach((item, i) => {
        const pct = Math.round((item.value / (item.max || 100)) * 100);
        const color = item.color || this.colors.palette[i % this.colors.palette.length];

        const row = document.createElement('div');
        row.className = 'progress-labeled';
        row.style.marginBottom = '12px';
        row.innerHTML = `
          <span style="font-size:13px;color:#374151;min-width:72px;font-weight:500">${item.label}</span>
          <div class="progress-bar">
            <div class="progress-bar-fill" style="width:0;background:${color}"></div>
          </div>
          <span class="progress-label">${item.value}/${item.max || 100}</span>
        `;
        container.appendChild(row);

        // 动画：延迟展开
        requestAnimationFrame(() => {
          setTimeout(() => {
            row.querySelector('.progress-bar-fill').style.width = pct + '%';
          }, i * 100);
        });
      });
    }
  };

  window.SLBCharts = SLBCharts;

})();
