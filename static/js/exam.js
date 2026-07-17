// 申论帮 - 考试页面脚本

let currentPaper = null;
let currentQuestion = null;
let submissionId = null;

// 加载试卷列表
async function loadPapers(page = 1) {
  const container = document.getElementById('papers-container');
  if (!container) return;

  container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

  try {
    const params = new URLSearchParams({ page, limit: 12 });
    const examType = document.getElementById('filter-exam-type')?.value;
    const year = document.getElementById('filter-year')?.value;
    const search = document.getElementById('filter-search')?.value;

    if (examType) params.append('exam_type', examType);
    if (year) params.append('year', year);
    if (search) params.append('search', search);

    const res = await apiFetch(`/api/papers?${params}`);
    renderPapers(res.data);
  } catch (e) {
    container.innerHTML = `<p class="empty-state">加载失败: ${e.message}</p>`;
  }
}

function renderPapers(data) {
  const container = document.getElementById('papers-container');
  if (!data.papers || data.papers.length === 0) {
    container.innerHTML = '<p class="empty-state">暂无试卷</p>';
    return;
  }

  container.innerHTML = data.papers.map(paper => `
    <div class="card paper-card" onclick="selectPaper('${paper.pid}')">
      <h4>${paper.title}</h4>
      <div class="paper-meta">
        <span class="badge">${paper.exam_type}</span>
        <span class="badge">${paper.year}</span>
      </div>
      <p class="paper-desc">${paper.questions?.length || 0} 道题目</p>
      <div class="paper-heat">
        <i data-lucide="activity"></i>
        <span>${paper.heat || 0}</span>
      </div>
    </div>
  `).join('');

  lucide.createIcons();
  renderPagination(data);
}

function renderPagination(data) {
  const container = document.getElementById('pagination');
  if (!container || data.pages <= 1) {
    if (container) container.innerHTML = '';
    return;
  }

  let html = '';
  for (let i = 1; i <= data.pages; i++) {
    html += `<button class="pagination-btn ${i === data.page ? 'active' : ''}" onclick="loadPapers(${i})">${i}</button>`;
  }
  container.innerHTML = html;
}

// 选择试卷
async function selectPaper(pid) {
  try {
    const res = await apiFetch(`/api/papers/${pid}`);
    currentPaper = res.data;
    const questions = parseQuestions(currentPaper.questions);

    if (questions.length === 0) {
      showToast('该试卷暂无题目', 'error');
      return;
    }

    showQuestionSelector(questions);
  } catch (e) {
    showToast('加载失败', 'error');
  }
}

function showQuestionSelector(questions) {
  const modal = document.getElementById('question-selector-modal') || createQuestionSelectorModal();
  const list = document.getElementById('question-list');

  list.innerHTML = questions.map((q, i) => `
    <div class="question-item" onclick="startExam(${i})">
      <div class="question-number">${i + 1}</div>
      <div class="question-info">
        <p class="question-stem">${q.stem?.substring(0, 80)}${q.stem?.length > 80 ? '...' : ''}</p>
        <p class="question-meta">字数要求: ${q.word_limit || '未指定'}</p>
      </div>
    </div>
  `).join('');

  modal.classList.add('active');
  lucide.createIcons();
}

function createQuestionSelectorModal() {
  const modal = document.createElement('div');
  modal.id = 'question-selector-modal';
  modal.className = 'modal';
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h3>选择题目</h3>
        <button class="modal-close" onclick="closeQuestionSelector()">&times;</button>
      </div>
      <div class="modal-body" id="question-list"></div>
    </div>
  `;
  document.body.appendChild(modal);
  return modal;
}

function closeQuestionSelector() {
  const modal = document.getElementById('question-selector-modal');
  if (modal) modal.classList.remove('active');
}

// 开始考试
async function startExam(questionIndex) {
  closeQuestionSelector();

  const questions = parseQuestions(currentPaper.questions);
  currentQuestion = questions[questionIndex];

  // 显示作答界面
  document.getElementById('exam-section').style.display = 'block';
  document.getElementById('paper-title').textContent = currentPaper.title;

  // 显示材料
  const materialContainer = document.getElementById('material');
  if (currentQuestion.material && currentQuestion.material.length > 0) {
    materialContainer.innerHTML = currentQuestion.material.map(m => `<p>${m}</p>`).join('');
  } else {
    materialContainer.innerHTML = '<p class="empty-state">无给定材料</p>';
  }

  // 显示题目
  document.getElementById('question-stem').textContent = currentQuestion.stem;
  document.getElementById('word-limit').textContent = '字数要求: ' + (currentQuestion.word_limit || '未指定');

  // 清空答案
  document.getElementById('answer').value = '';
  document.getElementById('word-count').textContent = '0';

  // 隐藏结果区
  document.getElementById('result-section').style.display = 'none';
  document.getElementById('exam-section').scrollIntoView({ behavior: 'smooth' });

  lucide.createIcons();
}

// 字数统计
document.addEventListener('DOMContentLoaded', function() {
  const answerInput = document.getElementById('answer');
  if (answerInput) {
    answerInput.addEventListener('input', function() {
      document.getElementById('word-count').textContent = this.value.length;
    });
  }
});

// 提交答案
async function submitAnswer() {
  const answer = document.getElementById('answer').value.trim();

  if (!answer) {
    showToast('请输入答案', 'error');
    return;
  }

  if (currentQuestion.word_limit && answer.length > currentQuestion.word_limit * 1.2) {
    if (!confirm(`答案字数(${answer.length})超过字数要求(${currentQuestion.word_limit})的20%，可能影响评分，是否继续提交？`)) {
      return;
    }
  }

  const submitBtn = document.querySelector('.submit-btn');
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<div class="spinner"></div> 提交中...';

  try {
    const res = await apiFetch('/api/submissions', {
      method: 'POST',
      body: JSON.stringify({
        pid: currentPaper.pid,
        qid: currentQuestion.qid,
        answer: answer
      })
    });

    submissionId = res.data.sid;
    showResult(res.data);
  } catch (e) {
    showToast(e.message || '提交失败', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i data-lucide="send"></i> 提交批改';
    lucide.createIcons();
  }
}

// 显示结果
function showResult(data) {
  document.getElementById('exam-section').style.display = 'none';
  document.getElementById('result-section').style.display = 'block';

  // 填充结果数据
  document.getElementById('total-score').textContent = data.score !== null ? Math.round(data.score) : '--';
  document.getElementById('paper-info').textContent = currentPaper.title;

  // 维度得分
  if (data.dimension_scores) {
    const dims = data.dimension_scores;
    const maxScores = { '踩点命中': 40, '逻辑结构': 25, '语言规范': 20, '字数控制': 10, '卷面整洁': 5 };

    document.getElementById('dimension-scores').innerHTML = Object.entries(dims).map(([key, value]) => `
      <div class="dimension-item">
        <span class="dimension-label">${key}</span>
        <div class="dimension-bar">
          <div class="dimension-fill" style="width: ${(value / maxScores[key]) * 100}%"></div>
        </div>
        <span class="dimension-value">${value}/${maxScores[key]}</span>
      </div>
    `).join('');
  }

  // 命中/遗漏要点
  if (data.hit_points && data.hit_points.length > 0) {
    document.getElementById('hit-points').innerHTML = data.hit_points.map(p => `<li>${p}</li>`).join('');
  } else {
    document.getElementById('hit-points').innerHTML = '<li>无</li>';
  }

  if (data.missing_points && data.missing_points.length > 0) {
    document.getElementById('missing-points').innerHTML = data.missing_points.map(p => `<li>${p}</li>`).join('');
  } else {
    document.getElementById('missing-points').innerHTML = '<li>无</li>';
  }

  // AI反馈
  document.getElementById('ai-feedback').textContent = data.ai_feedback || '暂无反馈';

  // 改进建议
  document.getElementById('improving-suggestions').textContent = data.improving_suggestions || '暂无建议';

  // 用户答案
  document.getElementById('user-answer').textContent = data.user_answer || '';

  document.getElementById('result-section').scrollIntoView({ behavior: 'smooth' });
  lucide.createIcons();
}

// 继续练习
function continuePractice() {
  document.getElementById('result-section').style.display = 'none';
  document.getElementById('exam-section').style.display = 'block';
  document.getElementById('answer').value = '';
  document.getElementById('word-count').textContent = '0';
}

// 解析题目JSON
function parseQuestions(questionsJson) {
  try {
    return JSON.parse(questionsJson);
  } catch {
    return [];
  }
}