(function(){
  const esc=t=>String(t??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

  function ensureInstallNodeMenu(){
    if(!document.getElementById('install-node-optimai')){
      document.querySelector('main.main').insertAdjacentHTML('beforeend','<section id="install-node-optimai" class="page hidden"></section>');
    }
    if(!document.querySelector('.nav button[data-page="install-node-optimai"]')){
      document.querySelector('.nav').insertAdjacentHTML('beforeend','<button data-page="install-node-optimai" onclick="showInstallNodePage()"><span class="nav-icon">📦</span><span class="nav-label">Install Node OptimAI</span></button>');
    }
  }

  function nodeStatusText(n){
    if(n.status==='running') return '✅ Running';
    return '⚠️ Belum running / belum install';
  }

  function buildInstallCommand(host,email){
    const safeEmail = String(email||'EMAIL_LU').replace(/'/g,'');
    return `ssh ${host}\n\napt update -y && apt upgrade -y && \\\napt install -y curl docker.io && \\\nsystemctl start docker && systemctl enable docker && \\\nrm -f /usr/local/bin/optimai-cli && rm -rf ~/.optimai && \\\ncurl -L https://optimai.network/download/cli-node/linux -o optimai-cli && \\\nchmod +x optimai-cli && mv optimai-cli /usr/local/bin/optimai-cli && \\\noptimai-cli auth login --email ${safeEmail} && \\\ncat <<'EOF' > /etc/systemd/system/optimai.service\n[Unit]\nDescription=OptimAI Node\nAfter=docker.service\nRequires=docker.service\n\n[Service]\nType=simple\nUser=root\nExecStart=/usr/local/bin/optimai-cli node start\nRestart=always\nRestartSec=15\n\n[Install]\nWantedBy=multi-user.target\nEOF\nsystemctl daemon-reload && \\\nsystemctl enable optimai && \\\nsystemctl start optimai && \\\nsleep 3 && \\\nsystemctl status optimai --no-pager`;
  }

  window.showInstallNodePage=function(){
    ensureInstallNodeMenu();
    document.querySelectorAll('.page').forEach(x=>x.classList.add('hidden'));
    document.getElementById('install-node-optimai').classList.remove('hidden');
    document.querySelectorAll('.nav button,.bottom-nav button').forEach(x=>x.classList.toggle('active',x.dataset.page==='install-node-optimai'));
    document.getElementById('page-title').textContent='Install Node OptimAI';
    document.getElementById('sub-title').textContent='Pilih VPS target lalu generate command install';

    const nodes=(window.state&&state.nodes)||[];
    const options=nodes.map(n=>`<option value="${esc(n.host||'')}">${esc(n.name)} — ${esc(n.host||'')}</option>`).join('');
    const rows=nodes.map(n=>`<tr><td><b>${esc(n.name)}</b><div class="host">${esc(n.host||'')}</div></td><td>${nodeStatusText(n)}</td><td><button class="btn small ok" onclick="pickInstallNode('${esc(n.host||'')}')">Pilih</button></td></tr>`).join('');

    document.getElementById('install-node-optimai').innerHTML=`
      <div class="panel">
        <h3>📦 Install Node OptimAI</h3>
        <p class="muted">Password OptimAI tidak lewat Telegram. Isi email, pilih VPS, lalu generate command.</p>
        <div class="form">
          <div class="form-row"><label>Pilih VPS Target</label><select id="install-host" class="form-input">${options}</select></div>
          <div class="form-row"><label>Email OptimAI</label><input id="install-email" class="form-input" placeholder="email@domain.com"></div>
          <div class="form-actions"><button class="btn ok" onclick="generateInstallCommand()">Generate Command</button></div>
        </div>
        <div id="install-output" style="margin-top:16px"></div>
      </div>
      <div class="panel"><h3>Daftar VPS</h3><table><thead><tr><th>VPS</th><th>Status</th><th>Aksi</th></tr></thead><tbody>${rows||'<tr><td colspan="3">Belum ada VPS terdaftar.</td></tr>'}</tbody></table></div>`;
  };

  window.pickInstallNode=function(host){
    const el=document.getElementById('install-host');
    if(el) el.value=host;
    window.scrollTo({top:0,behavior:'smooth'});
  };

  window.generateInstallCommand=function(){
    const host=document.getElementById('install-host')?.value||'';
    const email=document.getElementById('install-email')?.value.trim()||'';
    if(!host || !email){alert('Pilih VPS dan isi email dulu bro');return;}
    const cmd=buildInstallCommand(host,email);
    document.getElementById('install-output').innerHTML=`<div class="notice">Copy command ini, paste di terminal VPS bot. Kalau OptimAI minta password, isi manual di terminal.</div><pre>${esc(cmd)}</pre>`;
  };

  ensureInstallNodeMenu();
})();
