(function(){
  function ensureInstallNodeMenu(){
    if(!document.getElementById('install-node-optimai')){
      document.querySelector('main.main').insertAdjacentHTML('beforeend','<section id="install-node-optimai" class="page hidden"></section>');
    }
    if(!document.querySelector('.nav button[data-page="install-node-optimai"]')){
      document.querySelector('.nav').insertAdjacentHTML('beforeend','<button data-page="install-node-optimai" onclick="showInstallNodePage()"><span class="nav-icon">📦</span><span class="nav-label">Install Node OptimAI</span></button>');
    }
  }
  window.showInstallNodePage=function(){
    ensureInstallNodeMenu();
    document.querySelectorAll('.page').forEach(x=>x.classList.add('hidden'));
    document.getElementById('install-node-optimai').classList.remove('hidden');
    document.querySelectorAll('.nav button,.bottom-nav button').forEach(x=>x.classList.toggle('active',x.dataset.page==='install-node-optimai'));
    document.getElementById('page-title').textContent='Install Node OptimAI';
    document.getElementById('sub-title').textContent='Daftarkan VPS dulu, lalu install node dari menu ini';
    document.getElementById('install-node-optimai').innerHTML='<div class="panel"><h3>📦 Install Node OptimAI</h3><p class="muted">Menu sudah aktif. Tahap berikutnya kita sambungkan form install aman.</p><div class="notice">Password OptimAI tidak akan dikirim lewat Telegram.</div></div>';
  };
  ensureInstallNodeMenu();
})();
