/**
 * 真相猎人 — 前端交互逻辑
 *
 * 3Agent SSE流式展示：
 *   Agent 1: 恶意假设官 → Agent 2: 核查记者 → Agent 3: 真相发布官
 */

// ============================================================
// 初始化
// ============================================================

let currentText = '';
let currentReport = null;
let knowledgeGraph = null;

document.addEventListener('DOMContentLoaded', () => {
    loadDemoCases();
    loadKnowledgeStats();

    // 绑定开始核查按钮
    const btnAnalyze = document.getElementById('btn-analyze');
    if (btnAnalyze) {
        btnAnalyze.addEventListener('click', startAnalysis);
    }

    // 绑定图片审查按钮
    const btnAnalyzeImage = document.getElementById('btn-analyze-image');
    if (btnAnalyzeImage) {
        btnAnalyzeImage.addEventListener('click', startImageAnalysis);
    }

    // 绑定清除图片按钮
    const btnClearImage = document.getElementById('btn-clear-image');
    if (btnClearImage) {
        btnClearImage.addEventListener('click', clearImage);
    }

    // 绑定反馈按钮
    const btnYes = document.getElementById('btn-feedback-yes');
    const btnNo = document.getElementById('btn-feedback-no');
    if (btnYes) btnYes.addEventListener('click', () => submitFeedback(true));
    if (btnNo) btnNo.addEventListener('click', () => submitFeedback(false));

    // 绑定复制辟谣卡片按钮
    const btnCopy = document.getElementById('btn-copy');
    if (btnCopy) btnCopy.addEventListener('click', copyDebunkCard);

    // 图片粘贴事件
    const textarea = document.getElementById('input-text');
    if (textarea) {
        textarea.addEventListener('paste', handleImagePaste);
    }

    // 预设案例按钮 — 事件委托（动态生成）
    const demoContainer = document.getElementById('demo-cases');
    if (demoContainer) {
        demoContainer.addEventListener('click', (e) => {
            const btn = e.target.closest('button');
            if (btn && btn.dataset.caseText) {
                loadCase(btn.dataset.caseText);
            }
        });
    }
});

// ============================================================
// 预设案例
// ============================================================

async function loadDemoCases() {
    try {
        const resp = await fetch('/api/demo/cases');
        const data = await resp.json();
        const container = document.getElementById('demo-cases');

        if (!data.cases || data.cases.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-sm">暂无预设案例</p>';
            return;
        }

        container.innerHTML = data.cases.map(c => `
            <button
                data-case-text="${escapeAttr(c.text)}"
                class="text-left bg-gray-900 hover:bg-gray-800 border border-gray-700 hover:border-gray-600 rounded-xl p-4 transition-colors group"
            >
                <div class="text-sm text-gray-300 group-hover:text-white line-clamp-2 mb-2">
                    ${escapeHtml(c.text.substring(0, 80))}${c.text.length > 80 ? '...' : ''}
                </div>
                <span class="case-tag tag-${c.category}">${categoryLabel(c.category)}</span>
                ${c.difficulty === 'hard' ? '<span class="text-xs text-yellow-500 ml-1">困难</span>' : ''}
            </button>
        `).join('');
    } catch (e) {
        console.error('加载案例失败:', e);
    }
}

function loadCase(text) {
    document.getElementById('input-text').value = text;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function categoryLabel(id) {
    const labels = {
        data_fabrication: '📊 假数据',
        emotion_hijack: '🔥 情绪劫持',
        narrative_transplant: '🔀 叙事移植',
        authority_fake: '📜 权威伪装',
        trust_corrosion: '🕳️ 信任腐蚀',
        selective_feeding: '🎯 信息投喂',
        none: '✅ 真实信息',
    };
    return labels[id] || id;
}

// ============================================================
// 知识库统计
// ============================================================

async function loadKnowledgeStats() {
    try {
        const resp = await fetch('/api/knowledge/stats');
        const stats = await resp.json();
        document.getElementById('kb-stats').innerHTML =
            `📚 知识库: <span class="text-blue-400">${stats.total_cases || 0}</span> 条`;
    } catch (e) {
        document.getElementById('kb-stats').textContent = '📚 知识库: --';
    }
}

// ============================================================
// 分析主流程
// ============================================================

async function startAnalysis() {
    const btn = document.getElementById('btn-analyze');
    const text = document.getElementById('input-text').value.trim();
    if (!text) {
        alert('请先输入或选择待核查的信息');
        return;
    }

    // 防止重复点击
    if (btn.disabled) return;

    currentText = text;
    currentReport = null;

    btn.disabled = true;
    btn.textContent = '⏳ 核查中...';

    // 先重置界面再显示进度
    resetUI();
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // 显示进度区
    document.getElementById('progress-section').classList.remove('hidden');

    try {
        const resp = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });

        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const event = JSON.parse(line.slice(6));
                    handleSSEEvent(event);
                } catch (e) {
                    console.warn('SSE解析失败:', line);
                }
            }
        }
    } catch (e) {
        console.error('分析请求失败:', e);
        alert('分析请求失败，请检查后端是否启动');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 开始核查';
    }
}

// ============================================================
// SSE 事件处理
// ============================================================

function handleSSEEvent(event) {
    const { event: evt, agent, data } = event;

    switch (evt) {
        // 指纹特征
        case 'fingerprint':
            handleFingerprint(data);
            break;

        // 行为+动机+进化树
        case 'behavior_motivation':
            handleBehaviorMotivation(data);
            break;

        // OCR 事件
        case 'ocr_start':
            handleOcrStart(data);
            break;
        case 'ocr_complete':
            handleOcrComplete(data);
            break;

        // 并行调查事件
        case 'parallel_start':
            handleParallelStart(data);
            break;
        case 'parallel_complete':
            handleParallelComplete(data);
            break;

        case 'knowledge_hit':
            handleKnowledgeHit(data);
            break;

        // Agent 1: 恶意假设官
        case 'agent_start':
            if (agent === 'malice') handleMaliceStart(data);
            else if (agent === 'debater') handleDebaterStart(data);
            else if (agent === 'publisher') handlePublisherStart(data);
            else if (agent === 'evaluator') handleEvaluatorStart(data);
            break;

        case 'agent_complete':
            if (agent === 'malice') handleMaliceComplete(data);
            else if (agent === 'debater') handleDebaterComplete(data);
            else if (agent === 'publisher') handlePublisherComplete(data);
            else if (agent === 'evaluator') handleEvaluatorComplete(data);
            break;

        case 'agent_skip':
            if (agent === 'investigator') handleInvestigatorSkip(data);
            break;

        case 'report':
            handleReport(data);
            break;

        case 'error':
            alert('核查出错: ' + (event.message || '未知错误'));
            break;

        case 'done':
            loadKnowledgeStats();
            break;
    }
}

// ============================================================
// ============================================================
// OCR 事件处理
// ============================================================

function handleOcrStart(data) {
    // 在 Agent 1 面板前显示 OCR 进度
    const panel = document.getElementById('agent1-panel');
    panel.classList.add('active');
    panel.classList.remove('opacity-50');
    document.getElementById('agent1-status').textContent = '🤖 OCR 提取文字中...';
    document.getElementById('agent1-status').className = 'text-xs text-purple-400 ml-auto animate-pulse';
    document.getElementById('agent1-progress').querySelector('div').style.width = '50%';

    const content = document.getElementById('agent1-content');
    content.classList.remove('hidden');
    content.innerHTML = `<div class="text-purple-300 text-sm">🤖 正在用多模态 LLM 提取图片中的文字信息...</div>`;
}

function handleOcrComplete(data) {
    const text = data.text || '';
    const len = data.length || 0;

    const content = document.getElementById('agent1-content');
    content.innerHTML = `
        <div class="text-green-400 text-sm mb-2">✅ OCR 提取完成 — ${len} 字符</div>
        <div class="bg-gray-800 rounded-lg p-3 max-h-32 overflow-y-auto">
            <div class="text-gray-300 text-xs whitespace-pre-wrap">${escapeHtml(text.substring(0, 500))}${text.length > 500 ? '...' : ''}</div>
        </div>
        <div class="text-xs text-gray-500 mt-2">📋 已将提取文字送入核查流水线 →</div>
    `;

    // 把提取的文字填入输入框
    document.getElementById('input-text').value = text;
    currentText = text;
}

// 知识库命中
// ============================================================

function handleKnowledgeHit(data) {
    const panel = document.getElementById('agent1-panel');
    panel.classList.add('complete');
    document.getElementById('agent1-status').textContent = '📚 知识库命中';
    document.getElementById('agent1-status').className = 'text-xs text-green-400 ml-auto';
    document.getElementById('agent1-progress').querySelector('div').style.width = '100%';

    const content = document.getElementById('agent1-content');
    content.classList.remove('hidden');
    content.innerHTML = `<div class="text-green-400 text-sm">📚 知识库已有相似案例（相似度 ${(data.similarity * 100).toFixed(0)}%），直接复用结论</div>`;

    // 跳过后面的Agent
    ['agent2-panel', 'agent3-panel'].forEach(id => {
        const p = document.getElementById(id);
        p.classList.add('skipped');
        p.querySelector('[id$="-status"]').textContent = '⏭️ 已跳过';
    });
}

// ============================================================
// 谣言指纹
// ============================================================

function handleFingerprint(data) {
    const fp = data.fingerprint || {};
    const features = fp.features || {};
    const activeFeatures = Object.entries(features).filter(([k, v]) => v);
    const similarCount = (data.similar_cases || []).length;

    const featureLabels = {
        has_extreme_numbers: '📊极端数字', has_urgency_call: '🚨紧急呼吁',
        has_emotional_trigger: '😱情绪触发', has_authority_claim: '🏛️声称权威',
        has_identity_binding: '👥身份绑定', has_visual_description: '👁️画面描述',
        has_conspiracy_hint: '🕵️阴谋暗示', has_total_negation: '🚫全称否定',
        has_vague_time_place: '📍时空模糊', has_call_to_action: '📢行动号召',
        has_numeric_claim: '🔢数据声明', has_moral_judgment: '⚖️道德评判',
        has_us_vs_them: '⚔️对立叙事', has_health_fear: '☠️健康恐慌',
    };

    const panel = document.getElementById('agent1-panel');
    const content = document.getElementById('agent1-content');
    content.classList.remove('hidden');

    let featuresHtml = activeFeatures.slice(0, 6).map(([k]) =>
        `<span class="inline-block px-2 py-0.5 rounded text-xs ${features[k] ? 'bg-red-900/30 text-red-300' : 'bg-gray-800 text-gray-600'}">${featureLabels[k] || k}</span>`
    ).join(' ');

    content.innerHTML = `
        <div class="space-y-2">
            <div class="flex items-center gap-2">
                <span class="text-xs text-gray-400">🧬 谣言指纹:</span>
                <span class="text-xs font-bold ${fp.risk_level === 'high' ? 'text-red-400' : fp.risk_level === 'medium' ? 'text-yellow-400' : 'text-green-400'}">
                    ${fp.risk_level === 'high' ? '🔴' : fp.risk_level === 'medium' ? '🟡' : '🟢'} ${fp.risk_level}
                </span>
                <span class="text-xs text-gray-500">${fp.feature_count || 0}个特征命中</span>
                ${similarCount > 0 ? `<span class="text-xs text-blue-400">📚 ${similarCount}个相似案例</span>` : ''}
            </div>
            <div class="flex flex-wrap gap-1">${featuresHtml}</div>
        </div>
    `;
}

// ============================================================
// 行为+动机分析
// ============================================================

function handleBehaviorMotivation(data) {
    const behavior = data.behavior || {};
    const motivation = data.motivation || {};
    const evolution = data.evolution || {};

    // 在指纹区下面追加分析结果
    const content = document.getElementById('agent1-content');
    const currentHtml = content.innerHTML;

    let analysisHtml = `
        <div class="mt-3 pt-3 border-t border-gray-700 space-y-2 fade-in">
            <div class="grid grid-cols-2 gap-2 text-xs">
                <div class="bg-blue-900/20 rounded-lg p-2">
                    <div class="text-blue-300 font-medium mb-1">🕵️ 行为分析</div>
                    <div class="text-gray-400">${escapeHtml(behavior.manipulation_style || '').substring(0, 80)}</div>
                    <div class="text-gray-500 mt-1">传播: ${escapeHtml(behavior.spread_mechanism || '').substring(0, 60)}</div>
                </div>
                <div class="bg-purple-900/20 rounded-lg p-2">
                    <div class="text-purple-300 font-medium mb-1">🎯 动机分析</div>
                    <div class="text-gray-400">${escapeHtml(motivation.primary_motive || '').substring(0, 80)}</div>
                    <div class="text-gray-500 mt-1">分类: ${escapeHtml(motivation.motive_category || '')} | 受众: ${escapeHtml(motivation.intended_audience || '').substring(0, 30)}</div>
                </div>
            </div>
            ${evolution.total_variants > 0 ? `
            <div class="bg-green-900/20 rounded-lg p-2 text-xs">
                <span class="text-green-300">🧬 进化树: </span>
                <span class="text-gray-400">知识库中发现 <b class="text-green-400">${evolution.total_variants}</b> 个相似变体</span>
                ${(evolution.mutation_patterns || []).map(p => `<span class="text-gray-500 ml-2">· ${escapeHtml(p.description || '').substring(0, 50)}</span>`).join('')}
            </div>` : ''}
        </div>
    `;

    content.innerHTML = currentHtml + analysisHtml;
}

// ============================================================
// Agent 1: 恶意假设官
// ============================================================

function handleMaliceStart(data) {
    const panel = document.getElementById('agent1-panel');
    panel.classList.add('active');
    panel.classList.remove('opacity-50');
    document.getElementById('agent1-status').textContent = '👁️ 恶意假设分析中...';
    document.getElementById('agent1-status').className = 'text-xs text-purple-400 ml-auto animate-pulse';
    document.getElementById('agent1-progress').querySelector('div').style.width = '70%';

    const content = document.getElementById('agent1-content');
    content.classList.remove('hidden');
    // Append thinking indicator without wiping fingerprint data
    const thinking = document.getElementById('agent1-thinking');
    if (thinking) {
        thinking.classList.remove('hidden');
        thinking.textContent = '💭 基于指纹特征，分析恶意意图...';
    }
}

function handleMaliceProgress(data) {
    const thinking = document.getElementById('agent1-thinking');
    thinking.classList.remove('hidden');
    thinking.textContent = '💭 "' + (data.thinking || '正在分析...') + '"';
}

function handleMaliceComplete(data) {
    const panel = document.getElementById('agent1-panel');
    panel.classList.remove('active');
    panel.classList.add('complete');
    document.getElementById('agent1-status').textContent = '✓ 指纹+恶意假设完成';
    document.getElementById('agent1-status').className = 'text-xs text-green-400 ml-auto';
    document.getElementById('agent1-progress').querySelector('div').style.width = '100%';

    const evil = data.evil_score || 0;
    const evilColor = evil >= 0.7 ? 'text-red-400' : evil >= 0.4 ? 'text-orange-400' : 'text-green-400';

    const content = document.getElementById('agent1-content');
    content.classList.remove('hidden');

    // Append malice result below existing fingerprint
    const maliceHtml = document.createElement('div');
    maliceHtml.className = 'mt-3 pt-3 border-t border-gray-700 fade-in';
    maliceHtml.innerHTML = `
        ${data.malice_hypothesis ? `<div class="text-sm text-purple-200 bg-purple-900/30 rounded-lg p-2 mb-2">
            <span class="text-purple-300 font-medium text-xs">🔮 恶意假设：</span>${escapeHtml(data.malice_hypothesis).substring(0, 200)}
        </div>` : ''}
        <div class="flex gap-4 text-xs">
            <span class="text-gray-400">邪恶评分: <b class="${evilColor}">${(evil*100).toFixed(0)}%</b></span>
            <span class="text-gray-400">攻击维度: <b class="text-purple-300">${attackLabel(data.primary_attack)}</b></span>
            <span class="text-red-400 font-bold">🛡️ 零信任·全量核查</span>
        </div>
    `;
    content.appendChild(maliceHtml);
}

function attackLabel(key) {
    const labels = {
        political_stability: '政治稳定',
        economic_confidence: '经济信心',
        social_cohesion: '社会团结',
        institutional_trust: '制度信任',
    };
    return labels[key] || key || '未知';
}

// ============================================================
// Agent 2: 核查记者
// ============================================================

function handleInvestigatorStart(data) {
    const panel = document.getElementById('agent2-panel');
    panel.classList.add('active');
    panel.classList.remove('opacity-50');
    document.getElementById('agent2-status').textContent = '🔍 正在溯源调查...';
    document.getElementById('agent2-status').className = 'text-xs text-blue-400 ml-auto animate-pulse';
    document.getElementById('agent2-progress').querySelector('div').style.width = '40%';
}

function handleInvestigatorProgress(data) {
    const log = document.getElementById('agent2-search-log');
    const content = document.getElementById('agent2-content');
    content.classList.remove('hidden');

    if (data.claims_count) {
        log.innerHTML += `<div class="fade-in text-blue-300">📊 提取 ${data.claims_count} 个事实点进行核查...</div>`;
    }
    if (data.search_sources) {
        log.innerHTML += `<div class="fade-in text-green-300">🔗 360搜索找到 ${data.search_sources} 个信源，交叉验证中...</div>`;
    }
}

function handleInvestigatorComplete(data) {
    const panel = document.getElementById('agent2-panel');
    panel.classList.remove('active');
    panel.classList.add('complete');
    document.getElementById('agent2-status').textContent = '✓ 调查完成';
    document.getElementById('agent2-status').className = 'text-xs text-green-400 ml-auto';
    document.getElementById('agent2-progress').querySelector('div').style.width = '100%';

    const content = document.getElementById('agent2-content');
    content.classList.remove('hidden');

    const result = document.getElementById('agent2-result');
    const score = (data.overall_factual_score * 100).toFixed(0);
    const scoreColor = data.overall_factual_score > 0.7 ? 'text-green-400' :
                       data.overall_factual_score > 0.3 ? 'text-yellow-400' : 'text-red-400';

    let html = `<div class="fade-in mt-2">`;
    html += `<div class="text-white">事实置信度：<span class="${scoreColor} font-bold">${score}%</span></div>`;
    html += `<div class="text-gray-400 text-xs mt-1">信源交叉验证：${data.cross_validation_count || 0} 个独立来源</div>`;

    if (data.claims && data.claims.length > 0) {
        html += '<div class="mt-2 space-y-1">';
        for (const c of data.claims.slice(0, 5)) {
            const icon = c.verdict === 'true' ? '✅' : c.verdict === 'false' ? '❌' : '⚠️';
            html += `<div class="text-xs text-gray-400">${icon} ${escapeHtml((c.claim || '').substring(0, 60))} → <span class="text-gray-300">${c.verdict}</span></div>`;
        }
        html += '</div>';
    }

    if (data.investigation_notes) {
        html += `<div class="mt-2 text-xs text-gray-500 italic">📝 ${escapeHtml(data.investigation_notes.substring(0, 150))}</div>`;
    }

    html += '</div>';
    result.innerHTML = html;

    // 更新搜索日志
    const log = document.getElementById('agent2-search-log');
    if (data.summary) {
        log.innerHTML += `<div class="fade-in text-blue-200 text-xs">${escapeHtml(data.summary.substring(0, 200))}</div>`;
    }
}

function handleInvestigatorSkip(data) {
    const panel = document.getElementById('agent2-panel');
    panel.classList.add('skipped');
    panel.classList.remove('opacity-50');
    document.getElementById('agent2-status').textContent = '⏭️ ' + (data.message || '快速判伪');
    document.getElementById('agent2-status').className = 'text-xs text-yellow-400 ml-auto';
    document.getElementById('agent2-progress').querySelector('div').style.width = '100%';

    const content = document.getElementById('agent2-content');
    content.classList.remove('hidden');
    content.innerHTML = `<div class="text-yellow-400 text-sm">📋 ${escapeHtml(data.reason || '低危信息，跳过深度核查')}</div>`;
}

// ============================================================
// Agent 3: 真相发布官
// ============================================================

function handlePublisherStart(data) {
    const panel = document.getElementById('agent3-panel');
    panel.classList.add('active');
    panel.classList.remove('opacity-50');
    document.getElementById('agent3-status').textContent = '📋 正在生成报告...';
    document.getElementById('agent3-status').className = 'text-xs text-green-400 ml-auto animate-pulse';
    document.getElementById('agent3-progress').querySelector('div').style.width = '50%';
}

function handlePublisherComplete(data) {
    const panel = document.getElementById('agent3-panel');
    panel.classList.remove('active');
    panel.classList.add('complete');
    document.getElementById('agent3-status').textContent = '✓ 辩论+报告完成';
    document.getElementById('agent3-status').className = 'text-xs text-green-400 ml-auto';
    document.getElementById('agent3-progress').querySelector('div').style.width = '100%';

    const content = document.getElementById('agent3-content');
    content.classList.remove('hidden');
    // Append publisher info to debate content
    const pubHtml = document.createElement('div');
    pubHtml.className = 'mt-2 pt-2 border-t border-gray-700 fade-in';
    pubHtml.innerHTML = `
        <div class="text-white text-xs">📊 ${escapeHtml(data.one_sentence_verdict || '报告已生成')}</div>
        <div class="text-xs text-gray-400 mt-1">${categoryLabel(data.category)} | 置信度 ${((data.confidence||0.8)*100).toFixed(0)}%</div>
    `;
    content.appendChild(pubHtml);
}

// ============================================================
// 并行调查 + 辩论
// ============================================================

function handleParallelStart(data) {
    const panel = document.getElementById('agent2-panel');
    panel.classList.add('active');
    panel.classList.remove('opacity-50');
    document.getElementById('agent2-status').textContent = '🔍 3路并行取证中...';
    document.getElementById('agent2-status').className = 'text-xs text-blue-400 ml-auto animate-pulse';
    document.getElementById('agent2-progress').querySelector('div').style.width = '40%';

    const content = document.getElementById('agent2-content');
    content.classList.remove('hidden');
    const agents = data.agents || [];
    content.innerHTML = `
        <div class="grid grid-cols-3 gap-2 text-xs">
            <div class="bg-blue-900/30 rounded-lg p-2 text-center">
                <div class="text-blue-300 font-medium">🔍 ${agents[0] || '360搜索'}</div>
                <div class="text-gray-500 mt-1 animate-pulse">调查中...</div>
            </div>
            <div class="bg-orange-900/30 rounded-lg p-2 text-center">
                <div class="text-orange-300 font-medium">🔥 ${agents[1] || 'FC搜索'}</div>
                <div class="text-gray-500 mt-1 animate-pulse">调查中...</div>
            </div>
            <div class="bg-green-900/30 rounded-lg p-2 text-center">
                <div class="text-green-300 font-medium">📄 ${agents[2] || 'FC抓取'}</div>
                <div class="text-gray-500 mt-1 animate-pulse">调查中...</div>
            </div>
        </div>
    `;
}

function handleParallelComplete(data) {
    const panel = document.getElementById('agent2-panel');
    panel.classList.remove('active');
    panel.classList.add('complete');
    document.getElementById('agent2-status').textContent = '✓ 3路调查完成';
    document.getElementById('agent2-status').className = 'text-xs text-green-400 ml-auto';
    document.getElementById('agent2-progress').querySelector('div').style.width = '100%';

    const content = document.getElementById('agent2-content');
    const f360 = data.findings_360 || {};
    const fcSearch = data.findings_fc_search || {};
    const fcScrape = data.findings_fc_scrape || {};

    content.innerHTML = `
        <div class="grid grid-cols-3 gap-2 text-xs">
            <div class="bg-blue-900/20 rounded-lg p-2">
                <div class="text-blue-300 font-medium">🔍 360搜索</div>
                <div class="text-gray-400 mt-1">${escapeHtml((f360.summary || '完成').substring(0, 60))}</div>
                <div class="text-blue-400 mt-1">${(f360.findings || []).length} 个发现</div>
            </div>
            <div class="bg-orange-900/20 rounded-lg p-2">
                <div class="text-orange-300 font-medium">🔥 FC搜索</div>
                <div class="text-gray-400 mt-1">${escapeHtml((fcSearch.summary || '完成').substring(0, 60))}</div>
                <div class="text-orange-400 mt-1">${(fcSearch.findings || []).length} 个发现</div>
            </div>
            <div class="bg-green-900/20 rounded-lg p-2">
                <div class="text-green-300 font-medium">📄 FC抓取</div>
                <div class="text-gray-400 mt-1">${escapeHtml((fcScrape.summary || '完成').substring(0, 60))}</div>
                <div class="text-green-400 mt-1">${(fcScrape.findings || []).length} 个发现</div>
            </div>
        </div>
    `;
}

function handleDebaterStart(data) {
    const panel = document.getElementById('agent3-panel');
    panel.classList.add('active');
    panel.classList.remove('opacity-50');
    document.getElementById('agent3-status').textContent = '⚖️ 正在辩论对比证据...';
    document.getElementById('agent3-status').className = 'text-xs text-yellow-400 ml-auto animate-pulse';
    document.getElementById('agent3-progress').querySelector('div').style.width = '50%';
}

function handleDebaterComplete(data) {
    const panel = document.getElementById('agent3-panel');
    panel.classList.remove('active');
    panel.classList.add('complete');
    document.getElementById('agent3-status').textContent = '✓ 辩论共识达成';
    document.getElementById('agent3-status').className = 'text-xs text-green-400 ml-auto';
    document.getElementById('agent3-progress').querySelector('div').style.width = '100%';

    const content = document.getElementById('agent3-content');
    content.classList.remove('hidden');
    const cv = data.cross_validation || {};
    const fv = data.final_verdict || {};

    content.innerHTML = `
        <div class="fade-in text-sm space-y-2">
            <div class="text-white">⚖️ ${escapeHtml(data.debate_summary || '辩论完成').substring(0, 120)}</div>
            <div class="flex gap-4 text-xs">
                <span class="text-blue-400">📊 ${cv.total_sources || 0} 个信源</span>
                <span class="text-green-400">✅ ${cv.agreeing_sources || 0} 个印证</span>
                <span class="text-yellow-400">📋 质量: ${cv.quality || '?'}</span>
            </div>
            <div class="text-gray-300">结论: ${fv.conclusion || '?'} (置信度 ${((fv.confidence || 0)*100).toFixed(0)}%)</div>
        </div>
    `;
}

// ============================================================
// Agent 4: 质量审查官
// ============================================================

function handleEvaluatorStart(data) {
    const panel = document.getElementById('agent4-panel');
    panel.classList.add('active');
    panel.classList.remove('opacity-50');
    document.getElementById('agent4-status').textContent = '🛡️ 正在自我评估...';
    document.getElementById('agent4-status').className = 'text-xs text-yellow-400 ml-auto animate-pulse';
    document.getElementById('agent4-progress').querySelector('div').style.width = '50%';
}

function handleEvaluatorComplete(data) {
    const panel = document.getElementById('agent4-panel');
    panel.classList.remove('active');
    panel.classList.add('complete');
    document.getElementById('agent4-status').textContent = '✓ 评估完成';
    document.getElementById('agent4-status').className = 'text-xs text-green-400 ml-auto';
    document.getElementById('agent4-progress').querySelector('div').style.width = '100%';

    const content = document.getElementById('agent4-content');
    content.classList.remove('hidden');

    const qs = data.quality_score || 0;
    const qsColor = qs >= 0.8 ? 'text-green-400' : qs >= 0.6 ? 'text-yellow-400' : 'text-red-400';
    const dims = data.dimensions || {};

    content.innerHTML = `
        <div class="fade-in">
            <div>综合质量评分：<span class="${qsColor} font-bold text-lg">${(qs * 100).toFixed(0)}%</span></div>
            <div class="grid grid-cols-4 gap-2 mt-2 text-xs">
                <div class="text-center bg-gray-800 rounded-lg p-2">
                    <div class="text-gray-400">证据充分</div>
                    <div class="text-white font-bold">${((dims.evidence_sufficiency || 0) * 100).toFixed(0)}%</div>
                </div>
                <div class="text-center bg-gray-800 rounded-lg p-2">
                    <div class="text-gray-400">置信合理</div>
                    <div class="text-white font-bold">${((dims.confidence_reasonability || 0) * 100).toFixed(0)}%</div>
                </div>
                <div class="text-center bg-gray-800 rounded-lg p-2">
                    <div class="text-gray-400">核查完整</div>
                    <div class="text-white font-bold">${((dims.completeness || 0) * 100).toFixed(0)}%</div>
                </div>
                <div class="text-center bg-gray-800 rounded-lg p-2">
                    <div class="text-gray-400">结论严谨</div>
                    <div class="text-white font-bold">${((dims.rigor || 0) * 100).toFixed(0)}%</div>
                </div>
            </div>
            ${data.final_assessment ? `<div class="text-yellow-200 text-xs mt-2">📝 ${escapeHtml(data.final_assessment)}</div>` : ''}
        </div>
    `;
}

// ============================================================
// 完整报告渲染
// ============================================================

function handleReport(report) {
    currentReport = report;
    const section = document.getElementById('report-section');
    section.classList.remove('hidden');
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // 结论卡片
    const verdictMap = {
        verdict_true: { icon: '✅', label: '信息基本属实', cls: 'verdict-true' },
        verdict_false: { icon: '❌', label: '虚假信息', cls: 'verdict-false' },
        verdict_manipulative: { icon: '⚠️', label: '高度危险的认知操纵', cls: 'verdict-manipulative' },
        verdict_suspicious: { icon: '🟡', label: '信息存疑', cls: 'verdict-suspicious' },
        verdict_unknown: { icon: '⚪', label: '无法判定', cls: 'verdict-unknown' },
    };
    const v = verdictMap[report.overall_verdict] || verdictMap.verdict_unknown;

    const verdictCard = document.getElementById('verdict-card');
    verdictCard.className = `rounded-2xl p-6 border-2 ${v.cls}`;
    document.getElementById('verdict-icon').textContent = v.icon;
    document.getElementById('verdict-label').textContent =
        report.verdict_display || v.label;

    // 元信息
    const meta = document.getElementById('verdict-meta');
    let metaHtml = '';
    if (report.one_sentence_verdict) {
        metaHtml += `<div class="text-white font-medium">${escapeHtml(report.one_sentence_verdict)}</div>`;
    }
    if (report.investigation_depth === 'cached') {
        metaHtml += `<div class="text-blue-400">📚 知识库复用 | 置信度: 95%</div>`;
    } else {
        metaHtml += `<div>邪恶评分: <span class="font-bold">${(report.evil_score * 100).toFixed(0)}%</span> | 置信度: <span class="font-bold">${((report.confidence || 0.8) * 100).toFixed(0)}%</span></div>`;
        if (report.escalation === 'quick') {
            metaHtml += `<div class="text-yellow-400">📋 低危信息 · 快速判伪模式</div>`;
        } else if (report.escalation === 'deep') {
            metaHtml += `<div class="text-red-400">🔍 高危信息 · 深度核查模式</div>`;
        }
    }
    document.getElementById('verdict-meta').innerHTML = metaHtml;

    // 恶意假设
    if (report.malice_hypothesis) {
        const mh = document.getElementById('malice-hypothesis');
        mh.classList.remove('hidden');
        mh.innerHTML = '<span class="text-purple-300 font-medium">🔮 恶意假设：</span>' + escapeHtml(report.malice_hypothesis);
    }

    // 证据链
    renderEvidenceChain(report.evidence_chain || []);

    // 交叉验证面板
    renderCrossValidation(report);

    // 认知处方
    renderPrescription(report.prescription);

    // 行为动机进化树
    const bmHtml = renderBehaviorMotivation(report.behavior, report.motivation, report.evolution);
    if (bmHtml) {
        const evidenceParent = document.getElementById('evidence-chain').parentElement;
        const bmDiv = document.createElement('div');
        bmDiv.innerHTML = bmHtml;
        evidenceParent.parentElement.insertBefore(bmDiv.firstElementChild, evidenceParent);
    }

    // 自我评估
    renderEvaluation(report.self_evaluation);

    // 辟谣卡片
    renderDebunkCard(report.debunk_card);
}

function renderEvidenceChain(chain) {
    const el = document.getElementById('evidence-chain');
    if (!chain || chain.length === 0) {
        el.innerHTML = '<p class="text-gray-500 text-sm">知识库复用，无需重新构建证据链</p>';
        return;
    }

    // 统计
    const totalClaims = chain.length;
    const falseCount = chain.filter(c => c.verdict === 'false').length;
    const trueCount = chain.filter(c => c.verdict === 'true').length;
    const partialCount = chain.filter(c => c.verdict === 'partial').length;

    // ═══ 1. 网络图：交叉验证可视化 ═══
    const graphId = 'evidence-graph-' + Date.now();
    let html = `
    <div class="evidence-graph-container bg-gray-800/50 rounded-xl border border-gray-700 mb-4 overflow-hidden" style="height: 350px;">
        <div id="${graphId}" style="width:100%; height:100%"></div>
    </div>
    <div class="text-xs text-gray-500 text-center mb-4">
        🔵 声明 → 🟠 搜索查询 → 🟢 信源 → 🔴/🟢 判定 &nbsp;|&nbsp; 虚线 = 交叉验证 &nbsp;|&nbsp; 粗线 = 高置信度
    </div>`;

    // ═══ 2. 详细卡片 ═══
    html += '<div class="evidence-timeline">';

    chain.forEach((item, idx) => {
        const verdict = item.verdict || 'unverifiable';
        const verdictIcon = verdict === 'true' ? '✅' : verdict === 'false' ? '❌' : verdict === 'partial' ? '⚠️' : '◻️';
        const verdictLabel = verdict === 'true' ? '属实' : verdict === 'false' ? '虚假' : verdict === 'partial' ? '部分属实' : '无法验证';

        html += `
        <div class="evidence-step fade-in" style="animation-delay: ${idx * 0.1}s">
            <div class="evidence-step-header">
                <div class="evidence-step-num ${verdict}">${idx + 1}</div>
                <div class="evidence-claim-text">
                    📝 ${escapeHtml((item.claim_text || item.description || '事实点').substring(0, 100))}
                </div>
                <div class="evidence-verdict-badge ${verdict}">${verdictIcon} ${verdictLabel}</div>
            </div>
            <div class="evidence-step-body">`;

        // 来源详情
        if (item.sources && item.sources.length > 0) {
            html += `<div class="text-xs text-gray-400 mb-2">📎 ${item.sources.length} 个信源交叉验证</div>`;
            item.sources.forEach(src => {
                const isGov = (src.url || '').includes('.gov') || (src.title || '').includes('官方') || (src.title || '').includes('统计局');
                const badgeClass = isGov ? 'gov' : 'news';
                const badgeLabel = isGov ? '官方数据' : '媒体报道';
                html += `
                <div class="evidence-trace-item source" style="padding-left:20px">
                    <span class="evidence-source-badge ${badgeClass}">${badgeLabel}</span>
                    <span class="text-gray-300 text-xs">${escapeHtml((src.title || '').substring(0, 100))}</span>
                    ${src.snippet ? `<div class="text-gray-500 text-xs mt-0.5">"${escapeHtml(src.snippet.substring(0, 120))}"</div>` : ''}
                </div>`;
            });
        }

        // 官方数据对比
        if (item.official_data && item.official_data.source) {
            html += `
            <div class="evidence-compare">
                <div class="evidence-compare-fake">
                    <div class="evidence-compare-label fake">❌ 谣言声称</div>
                    <div class="text-gray-300 text-xs">${escapeHtml((item.claim_text || '').substring(0, 100))}</div>
                </div>
                <div class="evidence-compare-real">
                    <div class="evidence-compare-label real">✅ 官方/真实数据</div>
                    <div class="text-gray-300 text-xs">${escapeHtml((item.official_data.actual_value || item.official_data.source).substring(0, 100))}</div>
                    <div class="text-xs text-green-500 mt-1">📎 ${escapeHtml(item.official_data.source)}</div>
                </div>
            </div>`;
        }

        html += `</div></div>`;
    });

    html += '</div>';

    // 汇总统计
    html += `
    <div class="evidence-summary fade-in">
        <div class="evidence-summary-item">
            <span class="evidence-summary-icon">📊</span>
            <span>核查 <b>${totalClaims}</b> 个事实点</span>
        </div>
        ${falseCount > 0 ? `<div class="evidence-summary-item"><span class="evidence-summary-icon">❌</span><span class="text-red-400"><b>${falseCount}</b> 虚假</span></div>` : ''}
        ${trueCount > 0 ? `<div class="evidence-summary-item"><span class="evidence-summary-icon">✅</span><span class="text-green-400"><b>${trueCount}</b> 属实</span></div>` : ''}
        ${partialCount > 0 ? `<div class="evidence-summary-item"><span class="evidence-summary-icon">⚠️</span><span class="text-yellow-400"><b>${partialCount}</b> 部分</span></div>` : ''}
        <div class="evidence-summary-item"><span class="evidence-summary-icon">🔗</span><span>360搜索交叉验证</span></div>
    </div>`;

    el.innerHTML = html;

    // ═══ 渲染 vis.js 网络图 ═══
    setTimeout(() => renderEvidenceGraph(graphId, chain), 100);
}

function renderEvidenceGraph(containerId, chain) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const graphNodes = [];
    const graphEdges = [];
    let nodeIdx = 0;

    // 颜色映射
    const verdictColors = {
        'true': { bg: '#22c55e', border: '#4ade80' },
        'false': { bg: '#ef4444', border: '#f87171' },
        'partial': { bg: '#eab308', border: '#fbbf24' },
        'unverifiable': { bg: '#6b7280', border: '#9ca3af' },
    };

    // 中心节点：原始信息
    const centerId = 'center';
    graphNodes.push({
        id: centerId, label: '📋 待核查信息', group: 'center',
        shape: 'box', size: 30,
        color: { background: '#1e40af', border: '#3b82f6' },
        font: { color: '#93c5fd', size: 14, face: 'sans-serif' },
    });

    chain.forEach((item, ci) => {
        // 声明节点
        const claimId = `claim_${ci}`;
        const vColor = verdictColors[item.verdict] || verdictColors['unverifiable'];
        graphNodes.push({
            id: claimId,
            label: (item.claim_text || '事实点').substring(0, 25),
            group: 'claim',
            shape: 'ellipse', size: 22,
            color: { background: vColor.bg, border: vColor.border },
            font: { color: '#e5e7eb', size: 11, face: 'sans-serif' },
            title: `<b>${item.claim_text || ''}</b><br>判定: ${item.verdict}<br>置信度: ${(item.confidence || 0) * 100}%`,
        });
        graphEdges.push({ from: centerId, to: claimId, color: { color: '#6b7280' }, width: 1 });

        // 搜索查询节点
        const searchId = `search_${ci}`;
        graphNodes.push({
            id: searchId,
            label: '🔍 360搜索',
            group: 'search',
            shape: 'dot', size: 12,
            color: { background: '#f97316', border: '#fb923c' },
            font: { color: '#fdba74', size: 9, face: 'sans-serif' },
            title: '通过360搜索引擎进行溯源验证',
        });
        graphEdges.push({ from: claimId, to: searchId, color: { color: '#f97316', opacity: 0.6 }, dashes: true });

        // 来源节点
        const sources = item.sources || [];
        if (sources.length > 0) {
            sources.forEach((src, si) => {
                const srcId = `src_${ci}_${si}`;
                const isGov = (src.url || '').includes('.gov');
                graphNodes.push({
                    id: srcId,
                    label: (src.title || '来源').substring(0, 20),
                    group: 'source',
                    shape: 'box', size: 16,
                    color: { background: isGov ? '#166534' : '#1e3a5f', border: isGov ? '#22c55e' : '#3b82f6' },
                    font: { color: '#cbd5e1', size: 10, face: 'sans-serif' },
                    title: `<b>${src.title || ''}</b><br>${src.snippet || ''}<br><a href="${src.url || '#'}" target="_blank">${src.url || ''}</a>`,
                });
                graphEdges.push({ from: searchId, to: srcId, color: { color: isGov ? '#22c55e' : '#60a5fa', opacity: 0.7 } });

                // 来源 → 判定
                const verdictId = `verdict_${ci}`;
                if (si === 0) {
                    const vIcon = item.verdict === 'false' ? '❌' : item.verdict === 'true' ? '✅' : '⚠️';
                    graphNodes.push({
                        id: verdictId,
                        label: `${vIcon} ${item.verdict}`,
                        group: 'verdict',
                        shape: 'diamond', size: 18,
                        color: { background: vColor.bg, border: vColor.border },
                        font: { color: '#fff', size: 10, face: 'sans-serif' },
                    });
                    graphEdges.push({
                        from: srcId, to: verdictId,
                        color: { color: vColor.border, opacity: 0.8 },
                        width: 1 + (item.confidence || 0.5),
                    });
                }
            });

            // 多源交叉验证连线
            if (sources.length >= 2) {
                for (let si = 1; si < sources.length; si++) {
                    graphEdges.push({
                        from: `src_${ci}_0`, to: `src_${ci}_${si}`,
                        color: { color: '#22c55e', opacity: 0.3 },
                        dashes: true, width: 0.5,
                        title: '交叉验证: 两个独立信源',
                    });
                }
            }
        } else {
            // 无来源 → 直接连到判定
            const verdictId = `verdict_${ci}`;
            const vIcon = item.verdict === 'false' ? '❌' : '✅';
            graphNodes.push({
                id: verdictId,
                label: `${vIcon} ${item.verdict}`,
                group: 'verdict',
                shape: 'diamond', size: 16,
                color: { background: vColor.bg, border: vColor.border },
            });
            graphEdges.push({ from: searchId, to: verdictId, dashes: true, width: 1 });
        }
    });

    const nodes = new vis.DataSet(graphNodes);
    const edges = new vis.DataSet(graphEdges);

    const options = {
        nodes: { borderWidth: 2, shadow: { enabled: true, size: 3 } },
        edges: { smooth: { type: 'cubicBezier', roundness: 0.4 } },
        physics: {
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {
                gravitationalConstant: -50, centralGravity: 0.005,
                springLength: 150, springConstant: 0.04, damping: 0.5,
            },
            stabilization: { iterations: 100 },
        },
        interaction: { hover: true, tooltipDelay: 100, zoomView: false, dragView: false },
        layout: { improvedLayout: true },
        groups: {
            center: { shape: 'box', borderWidth: 3 },
            claim: { shape: 'ellipse', borderWidth: 2 },
            search: { shape: 'dot', borderWidth: 1 },
            source: { shape: 'box', borderWidth: 1 },
            verdict: { shape: 'diamond', borderWidth: 2 },
        },
    };

    const graph = new vis.Network(container, { nodes, edges }, options);
    setTimeout(() => graph.fit({ animation: { duration: 800, easingFunction: 'easeInOutQuad' } }), 300);
}

function renderCrossValidation(report) {
    const evidenceEl = document.getElementById('evidence-chain');
    if (!evidenceEl) return;

    const debate = report.debate || {};
    const cv = debate.cross_validation || {};
    const fv = debate.final_verdict || {};
    const consensus = debate.consensus || {};

    let html = '<div class="bg-gray-900 rounded-xl p-5 border border-blue-800/50 mb-4 fade-in">';
    html += '<h3 class="font-medium text-blue-300 mb-3">📊 交叉验证 & 溯源分析</h3>';

    html += `<div class="grid grid-cols-4 gap-3 mb-4">
        <div class="bg-blue-900/20 rounded-lg p-3 text-center">
            <div class="text-2xl font-bold text-blue-400">${cv.total_sources || 0}</div>
            <div class="text-xs text-gray-400">总信源</div>
        </div>
        <div class="bg-green-900/20 rounded-lg p-3 text-center">
            <div class="text-2xl font-bold text-green-400">${cv.agreeing_sources || 0}</div>
            <div class="text-xs text-gray-400">交叉印证</div>
        </div>
        <div class="bg-yellow-900/20 rounded-lg p-3 text-center">
            <div class="text-2xl font-bold text-yellow-400">${cv.quality || '?'}</div>
            <div class="text-xs text-gray-400">证据质量</div>
        </div>
        <div class="bg-purple-900/20 rounded-lg p-3 text-center">
            <div class="text-2xl font-bold text-purple-400">${((fv.confidence || 0) * 100).toFixed(0)}%</div>
            <div class="text-xs text-gray-400">综合置信</div>
        </div>
    </div>`;

    const confirmed = consensus.confirmed || [];
    const disputed = consensus.disputed || [];
    if (confirmed.length) {
        html += `<div class="mb-1"><span class="text-green-400 text-xs font-medium">✅ 多方印证 (${confirmed.length})</span></div>`;
        confirmed.forEach(c => { html += `<div class="text-xs text-gray-400 ml-4 mb-1">· ${escapeHtml(c).substring(0, 100)}</div>`; });
    }
    if (disputed.length) {
        html += `<div class="mt-2 mb-1"><span class="text-yellow-400 text-xs font-medium">⚠️ 存在争议 (${disputed.length})</span></div>`;
        disputed.forEach(c => { html += `<div class="text-xs text-gray-400 ml-4 mb-1">· ${escapeHtml(c).substring(0, 100)}</div>`; });
    }

    html += '<div class="mt-3 pt-3 border-t border-gray-700">';
    html += '<div class="text-xs text-blue-300 font-medium mb-2">🔗 溯源来源可信度</div>';
    const sources = [
        { label: '官方数据 (.gov.cn)', score: 95, c: 'green' },
        { label: '360搜索交叉验证', score: report.cross_validation_count > 1 ? 85 : 60, c: report.cross_validation_count > 1 ? 'green' : 'yellow' },
        { label: 'Firecrawl深度抓取', score: 80, c: 'green' },
        { label: '知识库案例匹配', score: report.knowledge_hit ? 90 : 50, c: report.knowledge_hit ? 'green' : 'gray' },
        { label: 'LLM逻辑推演', score: 65, c: 'yellow' },
    ];
    sources.forEach(s => {
        const bar = s.c === 'green' ? 'bg-green-500' : s.c === 'yellow' ? 'bg-yellow-500' : 'bg-gray-500';
        html += `<div class="flex items-center gap-2 mb-1.5">
            <span class="text-xs text-gray-400 w-32">${s.label}</span>
            <div class="flex-1 h-2 bg-gray-700 rounded-full"><div class="h-full ${bar} rounded-full" style="width:${s.score}%"></div></div>
            <span class="text-xs text-gray-500 w-8">${s.score}%</span>
        </div>`;
    });
    html += '</div></div>';

    const div = document.createElement('div');
    div.innerHTML = html;
    evidenceEl.parentElement.insertBefore(div.firstElementChild, evidenceEl.nextSibling);
}

function renderPrescription(rx) {
    const section = document.getElementById('prescription-section');
    const el = document.getElementById('prescription-content');

    if (!rx || (!rx.how_deceived?.length && !rx.prevention?.length)) {
        section.classList.add('hidden');
        return;
    }

    section.classList.remove('hidden');
    let html = '';

    if (rx.how_deceived?.length) {
        html += `<div>
            <h4 class="text-sm font-medium text-yellow-200 mb-2">🤔 它是怎么骗你的？</h4>
            <div class="space-y-1.5">
                ${rx.how_deceived.map(s => `<div class="text-sm text-gray-300">· ${escapeHtml(s)}</div>`).join('')}
            </div>
        </div>`;
    }

    if (rx.cognitive_weakness?.length) {
        html += `<div class="mt-3">
            <h4 class="text-sm font-medium text-yellow-200 mb-2">🧠 你的认知弱点被利用了</h4>
            <div class="space-y-1.5">
                ${rx.cognitive_weakness.map(s => `<div class="text-sm text-gray-300">· ${escapeHtml(s)}</div>`).join('')}
            </div>
        </div>`;
    }

    if (rx.prevention?.length) {
        html += `<div class="mt-3">
            <h4 class="text-sm font-medium text-yellow-200 mb-2">🛡️ 以后怎么防？</h4>
            <div class="space-y-1.5">
                ${rx.prevention.map(s => `<div class="text-sm text-gray-300">· ${escapeHtml(s)}</div>`).join('')}
            </div>
        </div>`;
    }

    if (rx.immunity_quote) {
        html += `<div class="mt-3 p-3 bg-yellow-900/20 rounded-lg">
            <div class="text-sm text-yellow-200 font-medium">💡 防骗口诀</div>
            <div class="text-sm text-gray-300 mt-1 italic">"${escapeHtml(rx.immunity_quote)}"</div>
        </div>`;
    }

    el.innerHTML = html;
}

function renderBehaviorMotivation(behavior, motivation, evolution) {
    if (!behavior && !motivation) return;

    let html = '<div class="bg-gray-900 rounded-xl p-5 border border-purple-800/50 mb-4"><h3 class="font-medium text-purple-300 mb-3">🧬 谣言行为·动机·进化分析</h3><div class="grid grid-cols-2 gap-3 text-sm">';

    if (behavior) {
        html += `<div class="bg-purple-900/20 rounded-lg p-3">
            <div class="text-purple-300 font-medium text-xs mb-2">🕵️ 行为模式</div>
            <div class="text-gray-300 text-xs mb-1">${escapeHtml(behavior.manipulation_style || '')}</div>
            <div class="text-gray-500 text-xs">传播: ${escapeHtml(behavior.spread_mechanism || '')}</div>
            <div class="text-gray-500 text-xs">认知目标: ${(behavior.cognitive_targets || []).join('、')}</div>
            <div class="text-gray-500 text-xs">情绪杠杆: ${(behavior.emotional_levers || []).join('、')}</div>
            <div class="text-xs text-orange-400 mt-1">传播力: ${((behavior.virality_score || 0) * 100).toFixed(0)}%</div>
        </div>`;
    }

    if (motivation) {
        html += `<div class="bg-blue-900/20 rounded-lg p-3">
            <div class="text-blue-300 font-medium text-xs mb-2">🎯 创作动机</div>
            <div class="text-gray-300 text-xs mb-1">${escapeHtml(motivation.primary_motive || '')}</div>
            <div class="text-gray-500 text-xs">分类: ${escapeHtml(motivation.motive_category || '')}</div>
            <div class="text-gray-500 text-xs">目标受众: ${escapeHtml(motivation.intended_audience || '')}</div>
            <div class="text-gray-500 text-xs">期望效果: ${escapeHtml(motivation.desired_effect || '')}</div>
            <div class="text-xs text-yellow-400 mt-1">获益方: ${escapeHtml(motivation.beneficiary || '')}</div>
        </div>`;
    }

    html += '</div>';

    if (evolution && evolution.total_variants_found > 0) {
        html += `<div class="mt-3 bg-green-900/20 rounded-lg p-3 text-xs">
            <span class="text-green-300 font-medium">🧬 进化树: </span>
            <span class="text-gray-400">知识库中 <b class="text-green-400">${evolution.total_variants_found}</b> 个变异版本</span>`;
        if (evolution.mutation_patterns) {
            evolution.mutation_patterns.forEach(p => {
                html += `<div class="text-gray-500 mt-1 ml-4">· ${escapeHtml(p.description || '')}</div>`;
            });
        }
        html += '</div>';
    }

    html += '</div>';
    return html;
}

function renderDebunkCard(card) {
    const section = document.getElementById('debunk-section');
    const el = document.getElementById('debunk-content');

    if (!card || !card.headline) {
        section.classList.add('hidden');
        return;
    }

    section.classList.remove('hidden');
    el.innerHTML = `
        <h4>${escapeHtml(card.headline)}</h4>
        <div class="space-y-2 mt-2">
            <div>
                <span class="text-xs text-gray-500">❌ 谣言：</span>
                <span class="fake-text text-sm">${escapeHtml(card.fake_claim || '')}</span>
            </div>
            <div>
                <span class="text-xs text-gray-500">✅ 真相：</span>
                <span class="truth-text text-sm">${escapeHtml(card.truth || '')}</span>
            </div>
            ${card.source ? `<div class="text-xs text-blue-300">📎 来源：${escapeHtml(card.source)}</div>` : ''}
            ${card.tips ? `<div class="text-xs text-yellow-300 mt-1">💡 ${escapeHtml(card.tips)}</div>` : ''}
        </div>
    `;
}

function renderEvaluation(evalData) {
    const section = document.getElementById('evaluation-section');
    const el = document.getElementById('evaluation-content');

    if (!evalData || !evalData.dimensions) {
        section.classList.add('hidden');
        return;
    }

    section.classList.remove('hidden');

    const qs = evalData.quality_score || 0;
    const qsColor = qs >= 0.8 ? 'text-green-400' : qs >= 0.6 ? 'text-yellow-400' : 'text-red-400';
    const qsBg = qs >= 0.8 ? 'bg-green-900/30' : qs >= 0.6 ? 'bg-yellow-900/30' : 'bg-red-900/30';
    const dims = evalData.dimensions || {};

    let html = `
    <div class="flex items-center gap-4 mb-4">
        <div class="${qsBg} rounded-xl px-4 py-3 text-center">
            <div class="text-xs text-gray-400">综合质量</div>
            <div class="${qsColor} text-2xl font-bold">${(qs * 100).toFixed(0)}%</div>
        </div>
        <div class="flex-1 grid grid-cols-2 gap-2 text-xs">
            ${renderDimBar('证据充分性', dims.evidence_sufficiency || 0)}
            ${renderDimBar('置信度合理性', dims.confidence_reasonability || 0)}
            ${renderDimBar('核查完整性', dims.completeness || 0)}
            ${renderDimBar('结论严谨性', dims.rigor || 0)}
        </div>
    </div>`;

    if (evalData.strengths && evalData.strengths.length) {
        html += `<div class="text-xs text-green-400 mb-1">✅ 做得好的：</div>`;
        html += evalData.strengths.map(s => `<div class="text-xs text-gray-400 ml-4 mb-1">· ${escapeHtml(s)}</div>`).join('');
    }
    if (evalData.weaknesses && evalData.weaknesses.length) {
        html += `<div class="text-xs text-yellow-400 mt-2 mb-1">⚠️ 需要改进：</div>`;
        html += evalData.weaknesses.map(s => `<div class="text-xs text-gray-400 ml-4 mb-1">· ${escapeHtml(s)}</div>`).join('');
    }
    if (evalData.missed_angles && evalData.missed_angles.length) {
        html += `<div class="text-xs text-orange-400 mt-2 mb-1">🔍 可能遗漏：</div>`;
        html += evalData.missed_angles.map(s => `<div class="text-xs text-gray-400 ml-4 mb-1">· ${escapeHtml(s)}</div>`).join('');
    }
    if (evalData.confidence_adjustment) {
        html += `<div class="text-xs text-blue-400 mt-2">📊 置信度建议：${escapeHtml(evalData.confidence_adjustment)}</div>`;
    }
    if (evalData.final_assessment) {
        html += `<div class="text-sm text-yellow-200 mt-3 bg-yellow-900/20 rounded-lg p-3">📝 ${escapeHtml(evalData.final_assessment)}</div>`;
    }

    el.innerHTML = html;
}

function renderDimBar(label, score) {
    const color = score >= 0.8 ? 'bg-green-500' : score >= 0.6 ? 'bg-yellow-500' : 'bg-red-500';
    return `<div>
        <div class="flex justify-between text-gray-400"><span>${label}</span><span>${(score * 100).toFixed(0)}%</span></div>
        <div class="h-1.5 bg-gray-700 rounded-full mt-0.5"><div class="h-full ${color} rounded-full" style="width:${(score * 100).toFixed(0)}%"></div></div>
    </div>`;
}

// ============================================================
// 辟谣卡片复制
// ============================================================

function copyDebunkCard() {
    if (!currentReport || !currentReport.debunk_card) return;

    const card = currentReport.debunk_card;
    const text = `🛡️ 真相猎人辟谣\n\n❌ 谣言：${card.fake_claim || ''}\n✅ 真相：${card.truth || ''}\n📎 来源：${card.source || '真相猎人核查'}\n💡 ${card.tips || ''}\n\n🔗 核查编号：${currentReport.id || ''}`;

    navigator.clipboard.writeText(text).then(() => {
        const status = document.getElementById('copy-status');
        status.classList.remove('hidden');
        setTimeout(() => status.classList.add('hidden'), 2000);
    }).catch(() => {
        alert('复制失败，请手动复制');
    });
}

// ============================================================
// 用户反馈
// ============================================================

async function submitFeedback(isCorrect) {
    if (!currentText) return;

    const yesBtn = document.getElementById('btn-feedback-yes');
    const noBtn = document.getElementById('btn-feedback-no');
    const status = document.getElementById('feedback-status');

    yesBtn.disabled = true;
    noBtn.disabled = true;

    try {
        await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: currentText,
                is_correct: isCorrect,
                comment: '',
            }),
        });
        status.textContent = isCorrect ? '✅ 感谢反馈！已记录为准确' : '📝 感谢反馈！我们会人工复核';
        status.classList.remove('hidden');
    } catch (e) {
        status.textContent = '反馈提交失败';
        status.classList.remove('hidden');
    }
}

// ============================================================
// 图片处理
// ============================================================

let currentImageFile = null;

function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    setImageFile(file);
}

function handleImagePaste(event) {
    const items = event.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
        if (item.type.startsWith('image/')) {
            event.preventDefault();
            const file = item.getAsFile();
            setImageFile(file);
            return;
        }
    }
}

function setImageFile(file) {
    currentImageFile = file;
    const url = URL.createObjectURL(file);

    document.getElementById('image-preview').classList.remove('hidden');
    document.getElementById('image-preview-img').src = url;
    document.getElementById('image-preview-label').textContent = `📷 ${file.name} (${(file.size / 1024).toFixed(1)} KB) — 点击"图片审查"开始`;
    document.getElementById('btn-analyze-image').classList.remove('hidden');
    document.getElementById('btn-analyze').classList.add('hidden');
    document.getElementById('input-text').placeholder = '图片已就绪，文字输入框将显示 OCR 提取结果...';
}

function clearImage() {
    currentImageFile = null;
    document.getElementById('image-preview').classList.add('hidden');
    document.getElementById('image-preview-img').src = '';
    document.getElementById('btn-analyze-image').classList.add('hidden');
    document.getElementById('btn-analyze').classList.remove('hidden');
    document.getElementById('input-text').value = '';
    document.getElementById('input-text').placeholder = '在这里粘贴你在朋友圈、群聊、社交媒体上看到的可疑信息...';
    const fileInput = document.getElementById('input-image');
    if (fileInput) fileInput.value = '';
}

async function startImageAnalysis() {
    if (!currentImageFile) {
        alert('请先上传或粘贴图片');
        return;
    }

    const btn = document.getElementById('btn-analyze-image');
    btn.disabled = true;
    btn.textContent = '⏳ 审查中...';

    currentText = '';
    currentReport = null;
    resetUI();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    document.getElementById('progress-section').classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', currentImageFile);

    try {
        const resp = await fetch('/api/analyze-image', {
            method: 'POST',
            body: formData,
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const event = JSON.parse(line.slice(6));
                    handleSSEEvent(event);
                } catch (e) {
                    console.warn('SSE解析失败:', line);
                }
            }
        }
    } catch (e) {
        console.error('图片审查失败:', e);
        alert('图片审查失败，请重试');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 图片审查';
        loadKnowledgeStats();
    }
}

// ============================================================
// 视图切换
// ============================================================

function switchView(view) {
    const checkView = document.getElementById('view-check');
    const graphSection = document.getElementById('graph-section');
    const btnCheck = document.getElementById('btn-view-check');
    const btnGraph = document.getElementById('btn-view-graph');

    if (view === 'check') {
        checkView.style.display = '';
        graphSection.classList.add('hidden');
        btnCheck.className = 'px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium transition-colors';
        btnGraph.className = 'px-3 py-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-white font-medium transition-colors';
    } else {
        checkView.style.display = 'none';
        graphSection.classList.remove('hidden');
        btnCheck.className = 'px-3 py-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-white font-medium transition-colors';
        btnGraph.className = 'px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium transition-colors';
        loadKnowledgeGraph();
    }
}

// ============================================================
// 知识图谱
// ============================================================

async function loadKnowledgeGraph() {
    const container = document.getElementById('knowledge-graph');
    if (!container) return;

    // 如果已加载，只做适配
    if (knowledgeGraph) {
        setTimeout(() => knowledgeGraph.fit({ animation: true }), 100);
        return;
    }

    try {
        const resp = await fetch('/api/knowledge/graph');
        const data = await resp.json();

        const nodes = new vis.DataSet(data.nodes || []);
        const edges = new vis.DataSet(data.edges || []);

        const options = {
            nodes: {
                borderWidth: 2,
                borderWidthSelected: 3,
                shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 5 },
                scaling: {
                    min: 12,
                    max: 50,
                    label: { enabled: true, min: 14, max: 20 },
                },
            },
            edges: {
                smooth: { type: 'continuous', roundness: 0.5 },
                width: 1,
                selectionWidth: 2,
            },
            physics: {
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -80,
                    centralGravity: 0.01,
                    springLength: 180,
                    springConstant: 0.08,
                    damping: 0.4,
                },
                stabilization: { iterations: 200, updateInterval: 25 },
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
                zoomView: true,
                dragView: true,
                navigationButtons: false,
            },
            layout: {
                improvedLayout: true,
            },
            groups: {
                attack_dimension: {
                    shape: 'diamond',
                    color: { background: '#7c3aed', border: '#a78bfa' },
                    font: { color: '#c4b5fd', size: 14, face: 'sans-serif' },
                    borderWidth: 3,
                },
                category: {
                    shape: 'dot',
                    size: 28,
                    borderWidth: 2,
                    font: { color: '#93c5fd', size: 13, face: 'sans-serif' },
                },
                case: {
                    shape: 'box',
                    borderWidth: 1,
                    font: { color: '#e5e7eb', size: 11, face: 'sans-serif' },
                },
            },
        };

        knowledgeGraph = new vis.Network(container, { nodes, edges }, options);

        // 点击节点显示详情
        knowledgeGraph.on('click', function (params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                if (node && node.title) {
                    showGraphPopup(node, params.event);
                }
            }
        });

        // 自动适配
        setTimeout(() => knowledgeGraph.fit({ animation: { duration: 1000, easingFunction: 'easeInOutQuad' } }), 500);

    } catch (e) {
        console.error('加载知识图谱失败:', e);
        container.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500">知识图谱加载失败</div>';
    }
}

function showGraphPopup(node, event) {
    // 移除旧popup
    const old = document.querySelector('.graph-node-popup');
    if (old) old.remove();

    const popup = document.createElement('div');
    popup.className = 'graph-node-popup fade-in';
    popup.innerHTML = node.title || node.label;
    popup.style.left = (event.center.x + 15) + 'px';
    popup.style.top = (event.center.y - 60) + 'px';
    document.body.appendChild(popup);

    // 3秒后自动消失
    setTimeout(() => popup.remove(), 3000);
}

// ============================================================
// 工具函数
// ============================================================

function resetUI() {
    const safe = (fn) => { try { fn(); } catch (e) { /* ignore missing element */ } };

    safe(() => document.getElementById('report-section').classList.add('hidden'));
    safe(() => document.getElementById('progress-section').classList.add('hidden'));

    // 重置4个Agent面板
    ['agent1', 'agent2', 'agent3', 'agent4'].forEach((id, i) => {
        safe(() => {
            const panel = document.getElementById(`${id}-panel`);
            panel.classList.remove('active', 'complete', 'skipped');
            panel.classList.add('opacity-50');
        });

        safe(() => {
            const statusEl = document.getElementById(`${id}-status`);
            const defaultTexts = ['等待输入', '等待指纹官完成', '等待侦察兵完成', '等待仲裁官完成'];
            statusEl.textContent = defaultTexts[i];
            statusEl.className = 'text-xs text-gray-500 ml-auto';
        });

        safe(() => {
            const progressBar = document.getElementById(`${id}-progress`);
            if (progressBar) progressBar.querySelector('div').style.width = '0%';
        });

        safe(() => {
            const content = document.getElementById(`${id}-content`);
            if (content) content.classList.add('hidden');
        });

        if (id === 'agent1') {
            safe(() => { document.getElementById('agent1-result').innerHTML = ''; });
            safe(() => { document.getElementById('agent1-thinking').classList.add('hidden'); });
        }
        if (id === 'agent2' || id === 'agent3' || id === 'agent4') {
            safe(() => {
                const c = document.getElementById(`${id}-content`);
                if (c) c.innerHTML = '';
            });
        }
    });

    // 重置报告区
    safe(() => document.getElementById('prescription-section').classList.add('hidden'));
    safe(() => document.getElementById('debunk-section').classList.add('hidden'));
    safe(() => document.getElementById('evaluation-section').classList.add('hidden'));
    safe(() => document.getElementById('malice-hypothesis').classList.add('hidden'));
    safe(() => document.getElementById('feedback-status').classList.add('hidden'));
    safe(() => {
        const fbYes = document.getElementById('btn-feedback-yes');
        const fbNo = document.getElementById('btn-feedback-no');
        if (fbYes) fbYes.disabled = false;
        if (fbNo) fbNo.disabled = false;
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function escapeAttr(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}
