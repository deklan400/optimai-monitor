(function(){
  const esc = (text) => String(text ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  let pendingNames = [];

  async function postSwap(names, sizeGb){
    const res = await fetch('/api/install-node/swap', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({names: names, size_gb: Number(sizeGb)})
    });
    if(res.status === 401){ location.href = '/login'; throw new Error('Login required'); }
    if(!res.ok){
      let msg = await res.text();
      try{ msg = JSON.parse(msg).detail || msg; }catch(e){}
      throw new Error(msg);
    }
    return res.json();
  }

  function selectedNames(){
    return Array.from(document.querySelectorAll('.ino:checked,.ino-check:checked')).map(x => x.value).filter(Boolean);
  }

  function outputBox(){
    return document.getElementById('install-output');
  }

  function ensureModal(){
    if(document.getElementById('swap-center-modal')) return;
    const style = document.createElement('style');
    style.textContent = `
      .swap-center-backdrop{position:fixed;inset:0;background:rgba(2,6,23,.72);display:none;align-items:center;justify-content:center;z-index:99999;padding:18px;backdrop-filter:blur(6px)}
      .swap-center-backdrop.show{display:flex}
      .swap-center-box{width:min(430px,100%);border:1px solid rgba(148,163,184,.24);border-radius:20px;background:linear-gradient(180deg,#18243b,#0f172a);box-shadow:0 24px 80px rgba(0,0,0,.5);padding:20px;color:#eaf2ff}
      .swap-center-box h3{margin:0 0 8px;font-size:22px;font-weight:950}
      .swap-center-box p{margin:0 0 14px;color:#9fb3d1;font-size:14px;line-height:1.45}
      .swap-center-box input{width:100%;background:#0b1221;border:1px solid rgba(148,163,184,.25);border-radius:14px;padding:13px 14px;color:#fff;font-size:18px;outline:none}
      .swap-center-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:16px}
      .swap-center-btn{border:0;border-radius:12px;padding:10px 18px;color:#fff;font-weight:900;cursor:pointer}
      .swap-center-cancel{background:#334155}.swap-center-ok{background:#d97706}
    `;
    document.head.appendChild(style);
    document.body.insertAdjacentHTML('beforeend', `
      <div id="swap-center-modal" class="swap-center-backdrop">
        <div class="swap-center-box">
          <h3>💾 Tambah Swap</h3>
          <p>Masukkan ukuran swap dalam GB. Contoh: 16, 32, 50, 80.</p>
          <input id="swap-center-input" type="number" min="1" max="256" value="32">
          <div class="swap-center-actions">
            <button class="swap-center-btn swap-center-cancel" id="swap-center-cancel">Cancel</button>
            <button class="swap-center-btn swap-center-ok" id="swap-center-ok">OK</button>
          </div>
        </div>
      </div>`);
    document.getElementById('swap-center-cancel').onclick = closeSwapModal;
    document.getElementById('swap-center-ok').onclick = submitSwapModal;
    document.getElementById('swap-center-modal').addEventListener('click', function(e){ if(e.target === this) closeSwapModal(); });
  }

  function openSwapModal(names){
    pendingNames = names || [];
    ensureModal();
    const modal = document.getElementById('swap-center-modal');
    const input = document.getElementById('swap-center-input');
    input.value = '32';
    modal.classList.add('show');
    setTimeout(() => input.focus(), 60);
  }

  function closeSwapModal(){
    const modal = document.getElementById('swap-center-modal');
    if(modal) modal.classList.remove('show');
  }

  async function submitSwapModal(){
    const gb = Number(document.getElementById('swap-center-input').value || 0);
    if(!gb || gb < 1 || gb > 256){ alert('Ukuran swap harus 1 sampai 256 GB bro'); return; }
    closeSwapModal();
    const out = outputBox();
    if(out) out.innerHTML = '<div class="notice">Membuat swap '+esc(gb)+'GB...</div>';
    try{
      const data = await postSwap(pendingNames, gb);
      if(out){
        out.innerHTML = (data.results || []).map(r => `<div class="panel"><h3>${r.ok ? '✅' : '❌'} ${esc(r.name)}</h3><pre>${esc(r.output || '')}</pre></div>`).join('');
      }
      if(typeof window.checkAllInstallNodes === 'function') await window.checkAllInstallNodes();
    }catch(e){
      if(out) out.innerHTML = `<div class="notice">Error: ${esc(e.message)}</div>`;
    }
  }

  window.swapSelectedNodes = function(){
    const names = selectedNames();
    if(!names.length){ alert('Pilih VPS dulu bro'); return; }
    openSwapModal(names);
  };

  window.swapOneNode = function(name){
    document.querySelectorAll('.ino,.ino-check').forEach(x => { x.checked = (x.value === name); });
    window.swapSelectedNodes();
  };

  window.openSwapModal = openSwapModal;
  window.closeSwapModal = closeSwapModal;
  ensureModal();
})();
