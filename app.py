    st.download_button("⬇ Export scanner CSV",view_df.to_csv(index=False).encode("utf-8"),
                       file_name="minervini_rs_scanner.csv",mime="text/csv")
    st.caption("Simplified candidate = RS 1W>0 & RS 1M>0 & Price>MA50>MA200 & RVOL>1 & U/D proxy>1.5. It does NOT implement all original Minervini trend-template/VCP conditions; U/D is NOT the official Up/Down Volume metric.")

# Streamlit components v2: a native event listener catches hovered ticker HTML
# within RS bubbles, SPDR bubbles, rankings and all ticker-bearing result tables.
# After 500ms the existing full-size Streamlit dialog opens automatically.
# Touchscreens can still click the href as a fallback.
RSM_HOVER_JS = r"""
export default function(component) {
  const { setTriggerValue } = component;
  let timer = null;
  let active = null;
  function tickerNode(target) {
    return target && target.closest ? target.closest('[data-rsm-ticker]') : null;
  }
  function onOver(event) {
    if (event.pointerType === 'touch') return;
    const node = tickerNode(event.target);
    if (!node) return;
    const ticker = node.getAttribute('data-rsm-ticker');
    if (!ticker || ticker === active) return;
    clearTimeout(timer);
    active = ticker;
    timer = setTimeout(() => setTriggerValue('hovered', ticker), 500);
  }
  function onOut(event) {
    const node = tickerNode(event.target);
    if (!node || (event.relatedTarget && node.contains(event.relatedTarget))) return;
    clearTimeout(timer);
    active = null;
  }
  document.addEventListener('pointerover', onOver, true);
  document.addEventListener('pointerout', onOut, true);
  // Header sorting is client-side: no server rerun and no loss of hover links.
  function onTableSort(e) {
    const button = e.target && e.target.closest ? e.target.closest('.rsm-sort-head') : null;
    if (!button) return;
    const th=button.closest('th');
    const table=button.closest('table.rsm-list-table');
    if (!table || !th || !table.tBodies.length) return;
    e.preventDefault();
    const col=Number(button.getAttribute('data-rsm-sortcol'));
    if (!Number.isInteger(col)) return;
    const current=th.getAttribute('aria-sort');
    const descending=/RS|RVOL|U\/D|Price|Weight|Cap|Change|Momentum|MA50|MA200/i.test(button.textContent);
    const direction=current==='ascending'?'descending':current==='descending'?'ascending':descending?'descending':'ascending';
    const rows=[...table.tBodies[0].rows];
    const item=(tr)=>tr.cells[col]?.textContent?.trim() || '';
    const numeric=(s)=>{
      const raw=s.replace(/[,%$\s]/g,'').replace(/^[−–]/,'-');
      return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw)?Number(raw):null;
    };
    rows.sort((a,b)=>{
      const A=item(a), B=item(b), x=numeric(A), y=numeric(B);
      let d=x!==null&&y!==null?x-y:A.localeCompare(B,undefined,{numeric:true,sensitivity:'base'});
      if (!A || A==='—') d=1;
      if (!B || B==='—') d=-1;
      return direction==='ascending'?d:-d;
    });
    table.querySelectorAll('th').forEach(h=>{
      h.setAttribute('aria-sort','none');
      const arrow=h.querySelector('.rsm-sort-arrow');if(arrow)arrow.textContent='⇅';
    });
    th.setAttribute('aria-sort',direction);
    button.querySelector('.rsm-sort-arrow').textContent=direction==='ascending'?'↑':'↓';
    table.tBodies[0].replaceChildren(...rows);
  }
  document.addEventListener('click',onTableSort,true);
  // Plotly Sector Rotation dots contain the ETF ticker in point.customdata.
  // Avoid attaching to generic plots without that attribute.
  const bound = new WeakSet();
  function bindPlotly() {
    document.querySelectorAll('div.js-plotly-plot').forEach((graph) => {
      if (bound.has(graph) || typeof graph.on !== 'function') return;
      bound.add(graph);
      graph.on('plotly_hover', (evt) => {
        const point = evt && evt.points && evt.points[0];
        const value = point && point.customdata;
        const ticker = Array.isArray(value) ? value[0] : value;
        if (typeof ticker !== 'string' || !/^[A-Z0-9^][A-Z0-9.^=_-]{0,22}$/.test(ticker)) return;
        clearTimeout(timer);
        active=ticker;
        timer=setTimeout(() => setTriggerValue('hovered',ticker), 500);
      });
      graph.on('plotly_unhover',() => {clearTimeout(timer);active=null;});
    });
  }
  const observer=new MutationObserver(() => bindPlotly());
  observer.observe(document.body,{subtree:true,childList:true});
  bindPlotly();
  return () => {
    clearTimeout(timer);
    observer.disconnect();
    document.removeEventListener('pointerover', onOver, true);
    document.removeEventListener('pointerout', onOut, true);
    document.removeEventListener('click',onTableSort,true);
  };
}
"""
hover_router=st.components.v2.component('rsm_ticker_hover_router',js=RSM_HOVER_JS)
hover_result=hover_router(key='rsm_hover_router_mount',on_hovered_change=lambda: None)
_hover_symbol=valid_ticker(getattr(hover_result,'hovered',None))
if _hover_symbol:
    # Trigger values are transient; re-hovering the SAME ticker must work too.
    st.session_state['_rsm_popup_request']=_hover_symbol

# Only one dialog is launched per Streamlit rerun, regardless of source.
# Avoid opening again on unrelated filter updates after a selected dataframe row.
_popup_now=valid_ticker(st.session_state.pop("_rsm_popup_request",None))
if _popup_now:
    show_ticker_popup(_popup_now)

st.divider()
st.markdown("<span class='rsm-note'>DATA SOURCES · Constituents: public S&P 500 lists · Market cap: Nasdaq snapshot via zyhe16/top-us-stock-tickers · Daily price/volume and continuous futures: Yahoo Finance via yfinance · ETF holdings: Yahoo Finance or Stock Analysis · Market breadth: derived from available constituents. No execution, no brokerage credentials, no guaranteed real-time data.</span>",unsafe_allow_html=True)

# RS Matrix v9: workspace order and exact filtered-bubbles CSV export.
