(function(){
  function n(v){return Number(v||0)}
  function fmt(v){return n(v).toLocaleString('en-US',{maximumFractionDigits:0})}
  function sd(d){const p=String(d||'').split('-');return p.length===3?`${p[2]}\n${p[1]}`:String(d||'-')}
  function esc2(t){return String(t??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
  function stackedChart(rows){
    if(!rows.length)return '<div class="notice">Belum ada data history untuk chart.</div>';
    const W=1040,H=430,L=58,R=25,T=45,B=70,PH=H-T-B,PW=W-L-R;
    const max=Math.max(1,...rows.map(x=>n(x.submitted)+n(x.pending)+n(x.retried)+n(x.failed)));
    const step=PW/rows.length,bar=Math.max(18,Math.min(34,step*.62));
    const y=v=>T+PH-(n(v)/max)*PH;
    const h=v=>Math.max(0,(n(v)/max)*PH);
    let grid='',ticks='';
    for(let i=0;i<=4;i++){const val=Math.round(max*i/4),yy=y(val);grid+=`<line class="activity-grid" x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}"/>`;ticks+=`<text class="activity-tick" x="${L-10}" y="${yy+4}" text-anchor="end">${fmt(val)}</text>`}
    const bars=rows.map((x,i)=>{const cx=L+step*i+step/2,bx=cx-bar/2;let top=T+PH;const parts=[['pending','activity-pending'],['retried','activity-retry'],['submitted','activity-submit'],['failed','activity-failed']];let out='';for(const [key,cls] of parts){const hh=h(x[key]);top-=hh;if(hh>0)out+=`<rect class="${cls}" x="${bx}" y="${top}" width="${bar}" height="${hh}" rx="4"></rect>`}const total=n(x.submitted)+n(x.pending)+n(x.retried)+n(x.failed);return `${out}<text class="activity-value" x="${cx}" y="${Math.max(16,top-8)}" text-anchor="middle">${fmt(total)}</text><text class="activity-tick" x="${cx}" y="${H-40}" text-anchor="middle">${esc2(sd(x.date)).split('&#10;')[0]||sd(x.date).split('\n')[0]}</text><text class="activity-tick" x="${cx}" y="${H-18}" text-anchor="middle">${sd(x.date).split('\n')[1]||''}</text>`}).join('');
    return `<div class="activity-chart-wrap"><svg class="activity-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="OptimAI activity statistics"><line class="activity-axis" x1="${L}" y1="${T}" x2="${L}" y2="${T+PH}"/><line class="activity-axis" x1="${L}" y1="${T+PH}" x2="${W-R}" y2="${T+PH}"/>${grid}${ticks}${bars}</svg></div><div class="activity-legend"><span class="activity-pill"><span class="activity-dot pending"></span>Pending</span><span class="activity-pill"><span class="activity-dot retry"></span>Retry</span><span class="activity-pill"><span class="activity-dot submit"></span>Submit</span><span class="activity-pill"><span class="activity-dot failed"></span>Failed</span></div>`;
  }
  window.renderCharts=async function(){
    if(window.currentPage&&currentPage!=='charts')return;
    const el=document.getElementById('charts');
    let activity='Loading...',daily='Loading...',reward='Loading...';
    try{
      const d=await api('/api/history/daily');
      const arr=(d.days||[]).slice().reverse().map(([date,x])=>({date,submitted:n(x.totals?.submitted),pending:n(x.totals?.pending),retried:n(x.totals?.retried),failed:n(x.totals?.failed),account_total:n(x.account_total)}));
      activity=stackedChart(arr);daily=barRows(arr,'submitted');reward=barRows(arr,'account_total');
    }catch(e){activity=daily=reward=e.message}
    const top=[...state.nodes].sort((a,b)=>metric(b,'submitted')-metric(a,'submitted')).slice(0,14).map(x=>({name:x.name,submitted:metric(x,'submitted')}));
    el.innerHTML=`<div class="activity-card"><div class="activity-head"><div><h3>Rewards / Activity Statistics</h3><p>The chart follows daily monitor history. Stack = Pending + Retry + Submit + Failed.</p></div><button class="activity-refresh" onclick="loadAll()">⟳ Refresh</button></div>${activity}</div><div class="panel"><h3>📊 Submit per Node Hari Ini</h3>${barRows(top,'submitted')}</div><div class="panel"><h3>💰 Total Akun Harian</h3>${reward}</div><div class="panel"><h3>📅 Submit Riwayat Harian</h3>${daily}</div>`;
  };
})();
