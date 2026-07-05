(function(){
  const esc=t=>String(t??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

  async function api(path,opt={}){
    const res=await fetch(path,opt);
    if(res.status===401){location.href='/login';throw new Error('Login required')}
    if(!res.ok){let m=await res.text();try{m=JSON.parse(m).detail||m}catch(e){}throw new Error(m)}
    return res.json();
  }

  function ensureInstallNodeMenu(){
    if(!document.getElementById('install-node-optimai')){
      document.querySelector('main.main').insertAdjacentHTML('beforeend','<section id="install-node-optimai" class="page hidden"></section>');
    }
    if(!document.querySelector('.nav button[data-page="install-node-optimai"]')){
      document.querySelector('.nav').insertAdjacentHTML('beforeend','<button data-page="install-node-optimai" onclick="showInstallNodePage()"><span class="nav-icon">📦</span><span class="nav-label">Install Node OptimAI</span></button>');
    }
  }

  function buildInstallCommand(host){
    return `ssh -tt ${host} "curl -fsSL https://raw.githubusercontent.com/deklan400/optimai-monitor/main/scripts/install_optimai_node.sh -o /tmp/install_optimai_node.sh && bash /tmp/install_optimai_node.sh"`;
  }

  window.showInstallNodePage=async function(){
    ensureInstallNodeMenu();
    document.querySelectorAll('.page').forEach(x=>x.classList.add('hidden'));
    document.getElementById('install-node-optimai').classList.remove('hidden');
    document.querySelectorAll('.nav button,.bottom-nav button').forEach(x=>x.classList.toggle('active',x.dataset.page==='install-node-optimai'));
    document.getElementById('page-title').textContent='Install Node OptimAI';
    document.getElementById('sub-title').textContent='Pilih VPS target lalu generate command install';

    const el=document.getElementById('install-node-optimai');
    el.innerHTML='<div class="panel"><h3>📦 Install Node OptimAI</h3><p class="muted">Loading daftar VPS...</p></div>';

    try{
      const data=await api('/api/vps');
      const nodes=data.vps||[];
      const options=nodes.map(n=>`<option value="${esc(n.host||'')}">${esc(n.name)} — ${esc(n.host||'')}</option>`).join('');
      const rows=nodes.map(n=>`<tr><td><b>${esc(n.name)}</b><div class="host">${esc(n.host||'')}</div></td><td>Siap install / cek manual</td><td><button class="btn small ok" onclick="pickInstallNode('${esc(n.host||'')}')">Pilih</button></td></tr>`).join('');

      el.innerHTML=`
        <div class="panel">
          <h3>📦 Install Node OptimAI</h3>
          <p class="muted">Pilih VPS, lalu generate command. Nanti saat command jalan di terminal, OptimAI akan minta email dan password secara manual.</p>
          <div class="form">
            <div class="form-row"><label>Pilih VPS Target</label><select id="install-host" class="form-input">${options}</select></div>
            <div class="form-actions"><button class="btn ok" onclick="generateInstallCommand()">Generate Command</button></div>
          </div>
          <div id="install-output" style="margin-top:16px"></div>
        </div>
        <div class="panel"><h3>Daftar VPS</h3><table><thead><tr><th>VPS</th><th>Status</th><th>Aksi</th></tr></thead><tbody>${rows||'<tr><td colspan="3">Belum ada VPS terdaftar.</td></tr>'}</tbody></table></div>`;
    }catch(e){
      el.innerHTML=`<div class="panel"><div class="notice">Error: ${esc(e.message)}</div></div>`;
    }
  };

  window.pickInstallNode=function(host){
    const el=document.getElementById('install-host');
    if(el) el.value=host;
    window.scrollTo({top:0,behavior:'smooth'});
  };

  window.generateInstallCommand=function(){
    const host=document.getElementById('install-host')?.value||'';
    if(!host){alert('Pilih VPS dulu bro');return;}
    const cmd=buildInstallCommand(host);
    document.getElementById('install-output').innerHTML=`<div class="notice">Copy command ini ke terminal VPS bot. Setelah jalan, installer akan minta email OptimAI lalu password/verify dari CLI.</div><pre>${esc(cmd)}</pre>`;
  };

  ensureInstallNodeMenu();
})();
