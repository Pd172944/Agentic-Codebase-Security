"""Generate the webapp with visualizations and PR text."""

HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Vulnerability Evaluation</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; background: #f8f9fa; color: #1e293b; padding: 20px; }
        .container { max-width: 1800px; margin: 0 auto; }
        header { background: linear-gradient(135deg, #1e40af 0%, #0f172a 100%); color: white; padding: 30px; border-radius: 6px; margin-bottom: 20px; }
        h1 { font-size: 2em; margin-bottom: 8px; }
        .subtitle { opacity: 0.9; font-size: 0.95em; }
        .controls { background: white; padding: 20px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #e2e8f0; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
        input[type="number"] { padding: 10px; border: 1px solid #cbd5e1; border-radius: 4px; width: 100px; }
        button { padding: 10px 20px; border: none; border-radius: 4px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background: #1e40af; color: white; }
        .btn-primary:hover { background: #1e3a8a; }
        .btn-warning { background: #f59e0b; color: white; }
        .btn-danger { background: #dc2626; color: white; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 6px; border: 1px solid #e2e8f0; }
        .card h3 { color: #475569; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 15px; }
        .metric { font-size: 2em; font-weight: 600; color: #0f172a; }
        .progress-bar { background: #e2e8f0; height: 28px; border-radius: 6px; overflow: hidden; margin-top: 10px; }
        .progress-fill { background: linear-gradient(90deg, #1e40af 0%, #3b82f6 100%); height: 100%; transition: width 0.3s; display: flex; align-items: center; justify-content: center; color: white; font-weight: 500; }
        .log-container { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 15px; height: 150px; overflow-y: auto; font-family: monospace; font-size: 12px; }
        .log-entry { padding: 3px 0; color: #64748b; border-bottom: 1px solid #f1f5f9; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #f8fafc; color: #64748b; font-weight: 600; font-size: 0.75em; text-transform: uppercase; padding: 12px; text-align: left; border-bottom: 2px solid #e2e8f0; }
        td { padding: 12px; border-bottom: 1px solid #f1f5f9; font-size: 0.9em; }
        tr:hover { background: #f8fafc; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 3px; font-size: 0.8em; font-weight: 500; }
        .badge-success { background: #dcfce7; color: #166534; }
        .badge-danger { background: #fee2e2; color: #991b1b; }
        .badge-warning { background: #fef3c7; color: #92400e; }
        .status { font-size: 1.1em; color: #1e40af; font-weight: 600; }
        .chart-container { height: 250px; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); }
        .modal-content { background: white; margin: 2% auto; border-radius: 8px; width: 95%; max-width: 1400px; max-height: 95vh; overflow: hidden; }
        .modal-header { background: linear-gradient(135deg, #1e40af 0%, #0f172a 100%); color: white; padding: 20px 30px; position: relative; }
        .modal-close { position: absolute; top: 15px; right: 20px; font-size: 28px; cursor: pointer; opacity: 0.8; }
        .modal-close:hover { opacity: 1; }
        .modal-body { padding: 25px; max-height: calc(95vh - 80px); overflow-y: auto; }
        .pr-text-container { background: #f8fafc; border: 2px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 15px 0; position: relative; }
        .pr-text-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #e2e8f0; }
        .pr-text-header h4 { color: #1e40af; font-size: 1.1em; }
        .copy-btn { background: #1e40af; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 0.9em; }
        .copy-btn:hover { background: #1e3a8a; }
        .copy-btn.copied { background: #16a34a; }
        .pr-text-content { font-family: -apple-system, system-ui, sans-serif; font-size: 0.95em; line-height: 1.6; color: #374151; white-space: pre-wrap; }
        .code-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .code-block { background: #1e293b; border-radius: 6px; overflow: hidden; }
        .code-block-header { background: #0f172a; color: white; padding: 10px 15px; font-weight: 600; font-size: 0.85em; }
        .code-block pre { padding: 15px; color: #e2e8f0; font-family: monospace; font-size: 0.8em; overflow-x: auto; max-height: 300px; overflow-y: auto; margin: 0; }
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; padding: 15px; background: #f8fafc; border-radius: 6px; }
        .info-item .label { font-size: 0.7em; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }
        .info-item .value { font-size: 1.1em; font-weight: 600; color: #0f172a; }
        .view-btn { color: #1e40af; cursor: pointer; font-weight: 500; }
        .view-btn:hover { text-decoration: underline; }
        .tabs { display: flex; gap: 5px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #e2e8f0; border: none; border-radius: 4px 4px 0 0; cursor: pointer; }
        .tab.active { background: #1e40af; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI Security Vulnerability Evaluation</h1>
            <div class="subtitle">Benchmarking AI Agents on Python Security Fixes with PR-Ready Explanations</div>
        </header>

        <div class="controls">
            <label>Samples:</label>
            <input type="number" id="sampleCount" value="3" min="1" max="50">
            <button class="btn-primary" onclick="startEvaluation()">Start Evaluation</button>
            <button class="btn-warning" onclick="startDemo()">Demo Mode</button>
            <button class="btn-danger" onclick="stopEvaluation()">Stop</button>
            <span id="statusText" class="status">Ready</span>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Progress</h3>
                <div id="progressText" class="metric">0 / 0</div>
                <div class="progress-bar">
                    <div id="progressBar" class="progress-fill" style="width: 0%">0%</div>
                </div>
            </div>
            <div class="card">
                <h3>Current Task</h3>
                <div id="currentTask" style="margin-top: 10px; font-size: 1.1em;">Waiting to start...</div>
            </div>
        </div>

        <div class="grid-3">
            <div class="card">
                <h3>Success Rate</h3>
                <div class="chart-container"><canvas id="successChart"></canvas></div>
            </div>
            <div class="card">
                <h3>Similarity Scores</h3>
                <div class="chart-container"><canvas id="scoreChart"></canvas></div>
            </div>
            <div class="card">
                <h3>Performance</h3>
                <div class="chart-container"><canvas id="perfChart"></canvas></div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 20px;">
            <h3>Logs</h3>
            <div id="logs" class="log-container"></div>
        </div>

        <div class="card">
            <h3>Results</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Agent</th>
                        <th>Vulnerability</th>
                        <th>Score</th>
                        <th>Fixed?</th>
                        <th>Executes?</th>
                        <th>Time</th>
                        <th>Cost</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="resultsBody">
                    <tr><td colspan="9" style="text-align: center; color: #9ca3af;">No results yet</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <div id="detailModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Evaluation Details</h2>
                <span class="modal-close" onclick="closeModal()">&times;</span>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <script>
        let ws = null;
        let samples = [];
        let results = [];
        let successChart, scoreChart, perfChart;

        function initCharts() {
            const ctx1 = document.getElementById('successChart').getContext('2d');
            successChart = new Chart(ctx1, {
                type: 'doughnut',
                data: {
                    labels: ['Fixed', 'Not Fixed'],
                    datasets: [{
                        data: [0, 0],
                        backgroundColor: ['#16a34a', '#dc2626']
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });

            const ctx2 = document.getElementById('scoreChart').getContext('2d');
            scoreChart = new Chart(ctx2, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Similarity Score',
                        data: [],
                        backgroundColor: '#1e40af'
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 10 } } }
            });

            const ctx3 = document.getElementById('perfChart').getContext('2d');
            perfChart = new Chart(ctx3, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Time (s)',
                        data: [],
                        borderColor: '#1e40af',
                        tension: 0.1
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        function updateCharts() {
            const fixed = results.filter(r => r.vulnerability_fixed).length;
            const notFixed = results.length - fixed;
            successChart.data.datasets[0].data = [fixed, notFixed];
            successChart.update();

            scoreChart.data.labels = results.map((r, i) => `#${i+1}`);
            scoreChart.data.datasets[0].data = results.map(r => r.similarity_score);
            scoreChart.update();

            perfChart.data.labels = results.map((r, i) => `#${i+1}`);
            perfChart.data.datasets[0].data = results.map(r => r.time_taken);
            perfChart.update();
        }

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            ws.onopen = () => addLog('Connected to server');
            ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
            ws.onclose = () => setTimeout(connectWebSocket, 3000);
        }

        function handleMessage(msg) {
            if (msg.type === 'status') updateStatus(msg.data);
            else if (msg.type === 'log') addLog(msg.data);
            else if (msg.type === 'result') { addResult(msg.data); updateCharts(); }
            else if (msg.type === 'complete') { addLog('Complete!'); document.getElementById('statusText').textContent = 'Complete'; }
            else if (msg.type === 'error') addLog('ERROR: ' + msg.data);
            else if (msg.type === 'samples') samples = msg.data;
        }

        function updateStatus(state) {
            const pct = state.total > 0 ? Math.round((state.progress / state.total) * 100) : 0;
            document.getElementById('progressText').textContent = `${state.progress} / ${state.total}`;
            document.getElementById('progressBar').style.width = `${pct}%`;
            document.getElementById('progressBar').textContent = `${pct}%`;
            if (state.running) {
                document.getElementById('statusText').textContent = 'Running...';
                if (state.current_agent) document.getElementById('currentTask').textContent = `${state.current_agent} on #${state.current_example}`;
            }
        }

        function addLog(text) {
            const logs = document.getElementById('logs');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
            logs.appendChild(entry);
            logs.scrollTop = logs.scrollHeight;
        }

        function addResult(result) {
            results.push(result);
            const tbody = document.getElementById('resultsBody');
            if (tbody.children[0]?.colSpan === 9) tbody.innerHTML = '';

            const row = document.createElement('tr');
            const vuln = result.vulnerability.length > 40 ? result.vulnerability.substring(0, 37) + '...' : result.vulnerability;
            row.innerHTML = `
                <td>${result.example_id}</td>
                <td><strong>${result.agent_name}</strong></td>
                <td>${vuln}</td>
                <td><strong>${result.similarity_score.toFixed(1)}</strong>/10</td>
                <td><span class="badge ${result.vulnerability_fixed ? 'badge-success' : 'badge-danger'}">${result.vulnerability_fixed ? 'Yes' : 'No'}</span></td>
                <td><span class="badge ${result.code_executes ? 'badge-success' : 'badge-danger'}">${result.code_executes ? 'Yes' : 'No'}</span></td>
                <td>${result.time_taken.toFixed(2)}s</td>
                <td>$${result.cost.toFixed(4)}</td>
                <td><span class="view-btn" onclick="viewDetails(${results.length - 1})">View Details</span></td>
            `;
            tbody.appendChild(row);
        }

        function viewDetails(idx) {
            const r = results[idx];
            const s = samples.find(x => x.id === r.example_id) || {};

            document.getElementById('modalTitle').textContent = r.vulnerability;
            document.getElementById('modalBody').innerHTML = `
                <div class="info-grid">
                    <div class="info-item"><div class="label">Agent</div><div class="value">${r.agent_name}</div></div>
                    <div class="info-item"><div class="label">Score</div><div class="value">${r.similarity_score.toFixed(1)}/10</div></div>
                    <div class="info-item"><div class="label">Fixed</div><div class="value">${r.vulnerability_fixed ? 'Yes' : 'No'}</div></div>
                    <div class="info-item"><div class="label">Executes</div><div class="value">${r.code_executes ? 'Yes' : 'No'}</div></div>
                    <div class="info-item"><div class="label">Time</div><div class="value">${r.time_taken.toFixed(2)}s</div></div>
                    <div class="info-item"><div class="label">Cost</div><div class="value">$${r.cost.toFixed(4)}</div></div>
                </div>

                <div class="pr-text-container">
                    <div class="pr-text-header">
                        <h4>PR Description (Copy for GitHub)</h4>
                        <button class="copy-btn" onclick="copyPRText(this, ${idx})">Copy to Clipboard</button>
                    </div>
                    <div class="pr-text-content" id="prText${idx}">${escapeHtml(r.pr_description || 'No PR description available')}</div>
                </div>

                <div class="code-grid">
                    <div class="code-block">
                        <div class="code-block-header">Vulnerable Code</div>
                        <pre>${escapeHtml(s.vulnerable_code || 'N/A')}</pre>
                    </div>
                    <div class="code-block">
                        <div class="code-block-header">Agent Fixed Code</div>
                        <pre>${escapeHtml(r.agent_fixed_code || 'N/A')}</pre>
                    </div>
                </div>
            `;
            document.getElementById('detailModal').style.display = 'block';
        }

        function copyPRText(btn, idx) {
            const text = results[idx].pr_description || '';
            navigator.clipboard.writeText(text).then(() => {
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(() => { btn.textContent = 'Copy to Clipboard'; btn.classList.remove('copied'); }, 2000);
            });
        }

        function closeModal() { document.getElementById('detailModal').style.display = 'none'; }
        function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text || ''; return div.innerHTML; }

        async function startEvaluation() {
            results = [];
            const count = document.getElementById('sampleCount').value;
            const resp = await fetch(`/api/start?sample_count=${count}`, { method: 'POST' });
            const data = await resp.json();
            if (data.error) addLog('ERROR: ' + data.error);
            else { addLog('Starting evaluation...'); document.getElementById('resultsBody').innerHTML = '<tr><td colspan="9" style="text-align:center">Loading...</td></tr>'; }
        }

        async function startDemo() {
            results = [];
            const count = document.getElementById('sampleCount').value;
            const resp = await fetch(`/api/start_demo?sample_count=${count}`, { method: 'POST' });
            const data = await resp.json();
            if (data.error) addLog('ERROR: ' + data.error);
            else addLog('Starting demo...');
        }

        async function stopEvaluation() {
            await fetch('/api/stop', { method: 'POST' });
            addLog('Stopping...');
        }

        window.onclick = (e) => { if (e.target.classList.contains('modal')) closeModal(); }
        initCharts();
        connectWebSocket();
    </script>
</body>
</html>'''

# Read current app.py
with open('webapp/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the get_html_content function
import re

# Find the function and replace it
pattern = r'def get_html_content\(\).*?(?=\nif __name__|$)'
replacement = f'''def get_html_content() -> str:
    return """{HTML_TEMPLATE}"""

'''

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('webapp/app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated webapp/app.py with new HTML template")
