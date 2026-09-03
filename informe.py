"""
Plantilla HTML del informe: misma estructura, CSS y componentes que el
informe de referencia (amercados 01sep2026.html): cabecera con titular,
barra pegajosa, ticker animado, indice rapido, 10 secciones numeradas,
grafico SVG del dolar y pie con descargo.
"""
import html
import datetime as dt
import config as C
import datos as DS
import grafico
from redactor import fmt, pct, _fecha_larga, _fecha_corta, _antiguedad, _q

CSS = r"""
  :root{
    /* ---- tema oscuro (marca) ---- */
    --bg:#0F1114;--bg2:#15181C;--paper:#171A1F;--plot:#131619;--andes:#1B1F24;
    --ink:#F1EFEA;--text:#D6D5D0;--text2:#B7B8B3;--soft:#8C9199;--soft2:#5E646C;--white:#FFFFFF;
    --line:#262B31;--line2:#343A42;--grid:#22272D;
    --copper:#D08A55;--copper-ink:#E8CDB2;--coppersoft:#3A2A1D;
    --ice:#7FB0C4;
    --green:#5FB283;--green-ink:#A5DDBE;--greenbg:#16241C;
    --red:#D06A5C;--red-ink:#EBAFA4;--redbg:#2C1B19;
    --shadow:0 10px 30px rgba(0,0,0,.35);
    --f-display:"Fraunces","Iowan Old Style","Palatino Linotype",Georgia,serif;
    --f-body:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --f-mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    font-size:16px;color-scheme:dark;
  }
  :root[data-theme="light"]{
    --bg:#F2F3F5;--bg2:#EAECEF;--paper:#FFFFFF;--plot:#F7F8FA;--andes:#E3E6EA;
    --ink:#14171B;--text:#2A2F36;--text2:#4A5058;--soft:#6B727B;--soft2:#9AA1A9;--white:#14171B;
    --line:#DCE0E5;--line2:#C9CED5;--grid:#E6E9ED;
    --copper:#B5642E;--copper-ink:#7A4320;--coppersoft:#F4E6DA;
    --ice:#3E7F97;
    --green:#2E8B57;--green-ink:#1F6A42;--greenbg:#E4F3EA;
    --red:#B8433A;--red-ink:#8E2F28;--redbg:#F8E4E1;
    --shadow:0 10px 30px rgba(20,23,27,.08);
    color-scheme:light;
  }
  *{box-sizing:border-box;}
  html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;}
  @media (prefers-reduced-motion:reduce){html{scroll-behavior:auto;} .ticker-track{animation:none!important;} *{transition:none!important;}}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--f-body);line-height:1.55;-webkit-font-smoothing:antialiased;overflow-x:hidden;-webkit-tap-highlight-color:rgba(208,138,85,.25);transition:background .25s,color .25s;}
  img,svg{max-width:100%;}
  main{max-width:680px;margin:0 auto;padding:0 0 48px;}
  a{color:inherit;}
  :focus-visible{outline:2px solid var(--copper);outline-offset:2px;border-radius:3px;}
  .num,.tv,.card .v,.commod-card .cv,tbody td:not(:first-child),.lvl .row b,.delta .d-row b{font-family:var(--f-mono);font-variant-numeric:tabular-nums;letter-spacing:-.01em;}

  /* ---- movimiento ---- */
  @keyframes fadeUp{from{opacity:0;transform:translateY(14px);}to{opacity:1;transform:none;}}
  @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(95,178,131,.55);}70%{box-shadow:0 0 0 7px rgba(95,178,131,0);}100%{box-shadow:0 0 0 0 rgba(95,178,131,0);}}
  @keyframes glow{0%,100%{opacity:.55;}50%{opacity:.9;}}
  header .anim{opacity:0;animation:fadeUp .7s cubic-bezier(.2,.8,.2,1) forwards;}
  header .anim:nth-child(1){animation-delay:.05s} header .anim:nth-child(2){animation-delay:.18s} header .anim:nth-child(3){animation-delay:.3s}
  header .anim:nth-child(4){animation-delay:.45s} header .anim:nth-child(5){animation-delay:.55s} header .anim:nth-child(6){animation-delay:.65s}
  header::before{content:"";position:absolute;top:-120px;right:-80px;width:320px;height:320px;border-radius:50%;background:radial-gradient(circle,rgba(208,138,85,.22) 0%,rgba(208,138,85,0) 65%);animation:glow 9s ease-in-out infinite;pointer-events:none;}
  .reveal{opacity:0;transform:translateY(16px);transition:opacity .6s cubic-bezier(.2,.8,.2,1),transform .6s cubic-bezier(.2,.8,.2,1);}
  .reveal.in{opacity:1;transform:none;}
  .card,.commod-card,.chart-card{transition:border-color .2s,transform .25s,box-shadow .25s;}
  .card:hover,.commod-card:hover{transform:translateY(-2px);box-shadow:var(--shadow);}
  svg .draw{stroke-dasharray:2000;stroke-dashoffset:2000;}
  .go svg .draw{animation:drawLine 1.6s cubic-bezier(.4,0,.2,1) forwards;}
  .go svg .draw.d2{animation-delay:.25s} .go svg .draw.d3{animation-delay:.45s}
  @keyframes drawLine{to{stroke-dashoffset:0;}}
  svg .bar{transform:scaleX(0);transform-box:fill-box;}
  svg .bar.pos{transform-origin:left center;} svg .bar.neg{transform-origin:right center;}
  .go svg .bar{animation:growBar .7s cubic-bezier(.2,.8,.2,1) forwards;}
  @keyframes growBar{to{transform:scaleX(1);}}
  svg .fill{opacity:0;transition:opacity 1s ease .9s;} .go svg .fill{opacity:1;}
  .live{display:inline-flex;align-items:center;gap:6px;font-size:.66rem;color:var(--soft);text-transform:uppercase;letter-spacing:.08em;}
  .live i{width:7px;height:7px;border-radius:50%;background:var(--soft2);display:inline-block;}
  .live.on i{background:var(--green);animation:pulse 2s infinite;}
  .spark{width:44px;height:14px;vertical-align:middle;margin-left:4px;}
  .range-btns{display:flex;gap:4px;position:absolute;top:12px;right:12px;}
  .range-btns button{appearance:none;border:1px solid var(--line);background:var(--bg2);color:var(--soft);font:inherit;font-size:.62rem;padding:3px 8px;border-radius:999px;cursor:pointer;}
  .range-btns button.on{color:var(--copper);border-color:var(--copper);background:var(--coppersoft);}
  .rango{display:none;} .rango.on{display:block;}
  @media (prefers-reduced-motion:reduce){header .anim{animation:none;opacity:1;} .reveal{opacity:1;transform:none;transition:none;} svg .draw{stroke-dasharray:none;stroke-dashoffset:0;animation:none!important;} svg .bar{transform:none;animation:none!important;} svg .fill{opacity:1;} header::before{animation:none;} .live.on i{animation:none;}}

  /* barra de progreso de lectura */
  #progress{position:fixed;top:0;left:0;height:3px;width:0;background:linear-gradient(90deg,var(--copper),var(--ice));z-index:100;transition:width .1s linear;}

  header{position:relative;padding:22px 22px 0;overflow:hidden;background:linear-gradient(180deg,var(--bg2) 0%,var(--bg) 100%);}
  .logo-slot{display:flex;align-items:baseline;margin-bottom:22px;}
  .logo-slot .wordmark{font-family:var(--f-display);font-size:2rem;font-weight:500;letter-spacing:.005em;font-variation-settings:"opsz" 96;}
  .logo-slot .wordmark .a{color:var(--copper);} .logo-slot .wordmark .rest{color:var(--ink);}
  .logo-slot .rule{flex:1;height:1px;background:linear-gradient(90deg,var(--copper) 0%,rgba(208,138,85,0) 100%);margin-left:14px;margin-bottom:8px;}
  .eyebrow{text-transform:uppercase;letter-spacing:.2em;font-size:.62rem;color:var(--copper);font-weight:600;margin-bottom:12px;}
  h1{font-family:var(--f-display);font-size:1.7rem;line-height:1.2;margin:0 0 8px;color:var(--ink);font-weight:500;text-wrap:balance;font-variation-settings:"opsz" 72;}
  .sub{font-size:.82rem;color:var(--soft);margin-bottom:14px;}
  .range{display:flex;justify-content:space-between;gap:12px;font-size:.68rem;color:var(--soft);padding-bottom:14px;}
  .andes{width:100%;height:58px;display:block;}
  .headline-frame{border-top:1px solid var(--copper);border-bottom:1px solid var(--copper);padding:14px 0;margin-bottom:16px;}
  .headline-label{text-transform:uppercase;letter-spacing:.18em;font-size:.6rem;color:var(--copper);font-weight:600;margin-bottom:8px;}

  /* ticker */
  .ticker-wrap{background:var(--paper);border-top:1px solid var(--line);border-bottom:1px solid var(--line);overflow:hidden;position:relative;padding:10px 0;cursor:pointer;}
  .ticker-track{display:flex;width:max-content;animation:ticker-scroll 40s linear infinite;}
  .ticker-wrap:hover .ticker-track,.ticker-wrap.paused .ticker-track{animation-play-state:paused;}
  .ticker-item{display:flex;align-items:baseline;gap:7px;padding:0 22px;white-space:nowrap;border-right:1px solid var(--line);}
  .ticker-item .tk{font-size:.66rem;color:var(--soft);text-transform:uppercase;letter-spacing:.06em;}
  .ticker-item .tv{font-size:.88rem;font-weight:600;color:var(--ink);}
  .ticker-item .td{font-size:.72rem;font-weight:600;}
  @keyframes ticker-scroll{from{transform:translateX(0);}to{transform:translateX(-50%);}}

  /* barra pegajosa: marca + navegacion + controles */
  .sticky-bar{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--line);}
  .sb-top{padding:8px 22px;display:flex;align-items:center;justify-content:space-between;gap:10px;}
  .sb-top .wm{font-family:var(--f-display);font-size:1.05rem;font-weight:500;}
  .sb-top .wm .a{color:var(--copper);} .sb-top .wm .rest{color:var(--ink);}
  .sb-top .sdate{font-size:.64rem;color:var(--soft);text-transform:uppercase;letter-spacing:.06em;margin-left:auto;margin-right:8px;}
  .btn{appearance:none;border:1px solid var(--line2);background:var(--paper);color:var(--text);border-radius:999px;font:inherit;font-size:.7rem;padding:5px 10px;cursor:pointer;display:inline-flex;align-items:center;gap:5px;line-height:1;transition:border-color .2s,background .2s;}
  .btn:hover{border-color:var(--copper);}
  .btn svg{width:13px;height:13px;}
  .sb-nav{display:flex;gap:6px;overflow-x:auto;padding:0 22px 8px;scrollbar-width:none;-ms-overflow-style:none;}
  .sb-nav::-webkit-scrollbar{display:none;}
  .sb-nav a{flex:0 0 auto;font-size:.68rem;color:var(--soft);text-decoration:none;padding:4px 10px;border-radius:999px;border:1px solid transparent;white-space:nowrap;transition:all .2s;}
  .sb-nav a.active{color:var(--copper);border-color:var(--copper);background:var(--coppersoft);}
  .sb-nav a:hover{color:var(--ink);}
  .sb-nav a.fold{margin-left:auto;border-color:var(--line);}

  .quickindex{padding:18px 22px;border-bottom:1px solid var(--line);}
  .quickindex .qi-label{text-transform:uppercase;letter-spacing:.16em;font-size:.6rem;color:var(--copper);font-weight:600;margin-bottom:12px;}
  .quickindex .qi-row{display:flex;flex-wrap:wrap;align-items:baseline;font-size:.8rem;line-height:1.9;}
  .quickindex .qi-row a{color:var(--text);text-decoration:none;} .quickindex .qi-row a:hover{color:var(--copper);}
  .quickindex .qi-sep{color:var(--copper);margin:0 9px;opacity:.7;}

  .delta{padding:12px 22px;border-bottom:1px solid var(--line);background:var(--bg2);}
  .delta .d-lab{text-transform:uppercase;letter-spacing:.16em;font-size:.6rem;color:var(--copper);font-weight:600;margin-bottom:6px;}
  .delta .d-row{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.78rem;color:var(--text);}
  .delta .d-row span b{color:var(--ink);font-weight:600;}

  section{padding:26px 22px;border-bottom:1px solid var(--line);scroll-margin-top:86px;}
  section:last-of-type{border-bottom:none;}
  .secnum{font-family:var(--f-display);font-size:.7rem;color:var(--copper);letter-spacing:.12em;margin-bottom:6px;}
  .sec-head{display:flex;align-items:center;justify-content:space-between;gap:10px;cursor:pointer;user-select:none;}
  .sec-head h2{margin:0 0 14px;}
  .sec-head .chev{width:22px;height:22px;flex:0 0 auto;color:var(--soft);transition:transform .25s;margin-bottom:14px;}
  section.collapsed .sec-head .chev{transform:rotate(-90deg);}
  section.collapsed .sec-body{display:none;}
  section.collapsed .sec-head h2{margin-bottom:0;} section.collapsed .sec-head .chev{margin-bottom:0;}
  h2{font-family:var(--f-display);font-size:1.2rem;color:var(--ink);font-weight:500;text-wrap:balance;font-variation-settings:"opsz" 48;}
  h3{font-size:.8rem;color:var(--copper);margin:20px 0 8px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;}
  p{margin:0 0 12px;font-size:.92rem;color:var(--text);text-align:left;max-width:66ch;}
  strong{color:var(--ink);font-weight:600;}

  ul.newsflash{list-style:none;margin:0;padding:0;}
  ul.newsflash li{padding:13px 0;border-bottom:1px solid var(--line);font-size:.92rem;line-height:1.55;color:var(--text);position:relative;padding-left:16px;}
  ul.newsflash li:last-child{border-bottom:none;}
  ul.newsflash li::before{content:"";position:absolute;left:0;top:11px;width:6px;height:1px;background:var(--copper);}
  ul.newsflash li .tag{display:inline-block;font-size:.6rem;text-transform:uppercase;letter-spacing:.08em;font-weight:600;color:var(--copper);margin-right:6px;}
  ul.plain{list-style:none;margin:0;padding:0;}
  ul.plain li{padding:11px 0;border-bottom:1px solid var(--line);font-size:.88rem;line-height:1.58;color:var(--text);position:relative;padding-left:16px;}
  ul.plain li:last-child{border-bottom:none;}
  ul.plain li::before{content:"";position:absolute;left:0;top:12px;width:6px;height:1px;background:var(--copper);}
  ul.plain li .tag{display:inline-block;font-size:.6rem;text-transform:uppercase;letter-spacing:.08em;font-weight:600;color:var(--copper);margin-right:6px;font-family:var(--f-mono);}
  ul li a{text-decoration:none;border-bottom:1px solid transparent;transition:border-color .2s;} ul li a:hover{border-bottom-color:var(--copper);}

  .stripe{display:flex;gap:10px;overflow-x:auto;margin-bottom:16px;padding-bottom:4px;scrollbar-width:thin;}
  .card{flex:0 0 auto;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:104px;transition:border-color .2s,transform .2s;}
  .card:hover{border-color:var(--line2);}
  .card .k{font-size:.6rem;color:var(--soft);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;}
  .card .v{font-size:1rem;font-weight:600;color:var(--ink);} .card .d{font-size:.68rem;margin-top:4px;}
  .up{color:var(--green);} .down{color:var(--red);} .flat{color:var(--soft);}

  .table-wrap{overflow-x:auto;margin:12px 0 16px;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:10px;background:var(--paper);}
  table{border-collapse:collapse;width:100%;min-width:420px;font-size:.8rem;}
  thead th{background:var(--bg2);color:var(--copper);text-align:left;padding:9px 11px;font-weight:600;white-space:nowrap;font-size:.64rem;text-transform:uppercase;letter-spacing:.07em;border-bottom:1px solid var(--line);cursor:pointer;user-select:none;}
  thead th:hover{color:var(--ink);}
  thead th.sorted::after{content:" ↓";color:var(--soft);} thead th.sorted.asc::after{content:" ↑";}
  tbody td{padding:9px 11px;border-bottom:1px solid var(--line);white-space:nowrap;color:var(--text);}
  tbody tr:last-child td{border-bottom:none;} tbody tr:nth-child(even){background:color-mix(in srgb,var(--bg2) 60%,var(--paper));}
  tbody tr:hover td{background:var(--coppersoft);}

  .chart-card{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:14px 12px 10px;margin:14px 0;position:relative;}
  .chart-title{font-size:.82rem;font-weight:600;color:var(--ink);margin-bottom:2px;}
  .chart-meta{font-size:.65rem;color:var(--soft);margin-bottom:10px;}
  .chart-card svg .hit{fill:transparent;cursor:crosshair;}
  .tip{position:fixed;z-index:120;pointer-events:none;background:var(--ink);color:var(--bg);font-family:var(--f-mono);font-size:.7rem;line-height:1.4;padding:6px 9px;border-radius:6px;box-shadow:var(--shadow);opacity:0;transition:opacity .12s;white-space:nowrap;transform:translate(-50%,calc(-100% - 12px));}
  .tip.on{opacity:1;}

  .callout{background:var(--coppersoft);border-left:3px solid var(--copper);padding:10px 12px;font-size:.78rem;color:var(--copper-ink);margin:12px 0;border-radius:4px;}

  .commod-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0 4px;}
  .commod-card{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:14px;}
  .commod-card .ck{display:flex;align-items:center;gap:6px;font-size:.64rem;text-transform:uppercase;letter-spacing:.08em;color:var(--soft);font-weight:600;margin-bottom:10px;}
  .commod-card .cv{font-size:1.15rem;color:var(--ink);font-weight:600;margin-bottom:6px;}
  .commod-card .cd{font-size:.78rem;font-weight:600;}

  .gauge{margin:6px 0 14px;}
  .gauge .g-lab{display:flex;justify-content:space-between;font-size:.62rem;color:var(--soft);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;}
  .gauge .g-bar{position:relative;height:8px;border-radius:4px;background:linear-gradient(90deg,var(--green) 0%,var(--line) 50%,var(--red) 100%);}
  .gauge .g-mark{position:absolute;top:-5px;width:4px;height:18px;border-radius:2px;background:var(--ink);box-shadow:0 0 0 2px var(--bg);transform:translateX(-50%);transition:left .6s cubic-bezier(.2,.8,.2,1);}
  .gauge .g-txt{font-family:var(--f-display);font-size:1.1rem;color:var(--ink);margin-top:10px;}
  .kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0 4px;}
  .kpi .card{min-width:0;padding:10px 10px;}
  .kpi .card .v{font-size:.9rem;}
  @media (max-width:440px){.kpi{grid-template-columns:repeat(2,1fr);}}
  .corr{display:inline-block;width:46px;height:5px;border-radius:3px;background:var(--line);position:relative;vertical-align:middle;margin-left:6px;}
  .corr i{position:absolute;top:0;height:5px;border-radius:3px;}
  .lvl{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0;}
  .lvl .card{min-width:0;}
  .lvl .row{display:flex;justify-content:space-between;font-size:.84rem;padding:4px 0;border-bottom:1px solid var(--line);}
  .lvl .row:last-child{border-bottom:none;} .lvl .row b{color:var(--ink);font-weight:600;}
  .pctl{position:relative;height:6px;border-radius:3px;background:linear-gradient(90deg,var(--green),var(--line) 50%,var(--red));margin-top:8px;}
  .pctl i{position:absolute;top:-3px;width:3px;height:12px;background:var(--ink);border-radius:2px;transform:translateX(-50%);}
  .fng{position:relative;height:8px;border-radius:4px;background:linear-gradient(90deg,var(--red) 0%,var(--soft) 50%,var(--green) 100%);margin:8px 0 4px;}
  .fng i{position:absolute;top:-4px;width:4px;height:16px;border-radius:2px;background:var(--ink);box-shadow:0 0 0 2px var(--paper);transform:translateX(-50%);}
  .strat{display:grid;grid-template-columns:1fr;gap:10px;margin:10px 0;}
  .strat .card{min-width:0;}
  .strat .card .v{font-size:.92rem;} .strat .card .d{font-size:.74rem;color:var(--text2);margin-top:5px;line-height:1.45;}

  /* pestañas */
  .tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin:14px 0 8px;}
  .tabs button{appearance:none;background:none;border:0;border-bottom:2px solid transparent;color:var(--soft);font:inherit;font-size:.78rem;font-weight:600;padding:8px 12px;cursor:pointer;margin-bottom:-1px;}
  .tabs button.on{color:var(--copper);border-bottom-color:var(--copper);}
  .tab-panel{display:none;} .tab-panel.on{display:block;}

  #totop{position:fixed;right:16px;bottom:18px;z-index:90;opacity:0;pointer-events:none;transition:opacity .25s;box-shadow:var(--shadow);}
  #totop.on{opacity:1;pointer-events:auto;}

  footer{padding:20px 22px;font-size:.66rem;color:var(--soft);line-height:1.6;border-top:1px solid var(--line);}
  footer b{color:var(--copper);}
  @page{size:A4;margin:0;}
  @media print{
    *{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
    html,body{background:var(--bg);margin:0;}
    body{padding:0 0 24px;}
    .ticker-track{animation:none;}
    .sticky-bar,#progress,#totop,.tip{display:none!important;}
    .reveal,header .anim{opacity:1!important;transform:none!important;animation:none!important;}
    svg .draw{stroke-dasharray:none!important;stroke-dashoffset:0!important;animation:none!important;} svg .bar{transform:none!important;animation:none!important;} svg .fill{opacity:1!important;}
    .range-btns{display:none;} .rango{display:none;} .rango[data-rango="60"]{display:block;} header::before{display:none;}
    section.collapsed .sec-body{display:block;} .tab-panel{display:block;} .tabs{display:none;}
    .chart-card,.commod-card,.card,.table-wrap,li,.callout{break-inside:avoid;}
    h2,h3{break-after:avoid;}
    main{max-width:none;padding:0 6mm 8mm;}
  }
"""

ANDES = ('<svg class="andes" viewBox="0 0 400 58" preserveAspectRatio="none">'
         '<polyline points="0,58 30,34 55,45 90,18 120,40 150,27 185,48 215,23 250,42 280,14 315,38 350,29 400,45 400,58 0,58" fill="#1F2328"/>'
         '<polyline points="0,58 30,34 55,45 90,18 120,40 150,27 185,48 215,23 250,42 280,14 315,38 350,29 400,45" fill="none" stroke="#C97A45" stroke-width="1" opacity="0.55"/></svg>')

SECCIONES = [("sec1", "Lo más relevante"), ("sec2", "Panorama internacional"), ("sec3", "Chile"),
             ("sec4", "Riesgos geopolíticos"), ("sec5", "Inflación y tasas"), ("sec6", "Tipo de cambio"),
             ("sec7", "Dólar en profundidad"), ("sec8", "Oro, cobre y plata"), ("sec9", "Mercado bursátil"),
             ("sec10", "Cripto"), ("sec11", "Agenda económica"), ("sec12", "Riesgos de la jornada")]
ROMANOS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def _cls(chg):
    if chg is None:
        return "flat"
    return "up" if chg > 0.005 else ("down" if chg < -0.005 else "flat")


def _flecha(chg, dec=1, texto=None):
    if chg is None:
        return '<span class="flat">—</span>'
    c = _cls(chg)
    sym = "▲" if c == "up" else ("▼" if c == "down" else "—")
    return f'<span class="{c}">{sym} {texto if texto is not None else pct(chg, dec)}</span>'


def _valor(q, dec=None):
    if not q or q.get("price") is None:
        return "n/d"
    return fmt(q["price"], q.get("dec", 2) if dec is None else dec)


def _ticker(D, tz, b=None):
    u, e, cu, br = _q(D, "usdclp"), _q(D, "eurclp"), _q(D, "cobre"), _q(D, "brent")
    ch = D.get("chile") or {}
    ip = D.get("ipsa")
    items = []
    if b and b.get("nivel"):
        ip = None
        items_ipsa = ("IPSA (estimado)", fmt(b["nivel"], 0), _flecha(b["var"], 2))
    elif b:
        ip = None
        items_ipsa = ("IPSA (est. sesión)", "", _flecha(b["var"], 2))
    else:
        items_ipsa = None
    if u:
        ahora = dt.datetime.now(tz)
        abierto = ahora.weekday() < 5 and 9 <= ahora.hour < 17
        sp_u = _spark(u.get("candles"))
        if abierto:
            items.append(("Dólar (spot)", "$" + fmt(u["price"]), _flecha(u["chg"], 2) + sp_u))
        else:
            # mercado chileno cerrado: se muestra el ULTIMO CIERRE (como el original)
            cierres = DS.cierres_diarios(u["candles"], 2, tz)
            if len(cierres) == 2:
                c1, c0 = cierres[-1], cierres[-2]
                dia = ["lun.", "mar.", "mié.", "jue.", "vie.", "sáb.", "dom."][c1["fecha"].weekday()]
                items.append((f"Dólar (cierre {dia})", "$" + fmt(c1["c"]), _flecha((c1["c"] - c0["c"]) / c0["c"] * 100, 2) + sp_u))
            else:
                items.append(("Dólar (spot)", "$" + fmt(u["price"]), _flecha(u["chg"], 2)))
    if items_ipsa:
        items.append(items_ipsa)
    elif ip:
        items.append(("IPSA (cierre, prensa)", ("≈" if ip.get("aprox") else "") + fmt(ip["price"], 0 if ip.get("aprox") else 2), _flecha(ip.get("chg"))))
    if e:
        items.append(("Euro", "$" + fmt(e["price"]), _flecha(e["chg"])))
    if ch.get("uf"):
        items.append(("UF", "$" + fmt(ch["uf"]["valor"]), '<span class="flat">—</span>'))
    if cu:
        items.append(("Cobre", "US$" + fmt(cu["price"]), _flecha(cu["chg"]) + _spark(cu.get("candles"))))
    if br:
        items.append(("Petróleo (Brent)", "US$" + fmt(br["price"]), _flecha(br["chg"]) + _spark(br.get("candles"))))
    h = "".join(f'<div class="ticker-item"><span class="tk">{k}</span><span class="tv">{v}</span><span class="td">{d}</span></div>'
                for k, v, d in items)
    return h + h   # duplicado para que la cinta sea continua


def _li(items, cls="plain", tags=None):
    if tags:
        return f'<ul class="{cls}">' + "".join(
            f'<li><span class="tag">{it["tag"]}</span>{it["html"]}</li>' for it in items) + "</ul>"
    return f'<ul class="{cls}">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def _sec_cambio(D, tz, cont):
    u = _q(D, "usdclp")
    ch = D.get("chile") or {}
    if not u:
        return "<p>Sin datos del dólar hoy (Yahoo no respondió).</p>"
    cierres = DS.cierres_diarios(u["candles"], 5, tz)
    ult = cierres[-1] if cierres else None
    sem = (cierres[-1]["c"] - cierres[0]["c"]) if len(cierres) >= 2 else None
    f_ult = _fecha_corta(ult["fecha"]) if ult else ""
    f_ini = _fecha_corta(cierres[0]["fecha"]) if cierres else ""
    obs = ch.get("dolar")
    stripe = f'''<div class="stripe">
    <div class="card"><div class="k">Dólar spot — ahora</div><div class="v">${fmt(u["price"])}</div><div class="d {_cls(u["chg_abs"])}">{"▲" if u["chg_abs"] > 0 else ("▼" if u["chg_abs"] < 0 else "—")} {fmt(u["chg_abs"]).replace("-", "")} ({pct(u["chg"], 2)})</div></div>
    <div class="card"><div class="k">Cierre anterior</div><div class="v">${fmt(u["prev"])}</div><div class="d flat">{f_ult}</div></div>
    {"".join([f'<div class="card"><div class="k">Var. semana</div><div class="v" style="color:{"#C1655A" if sem > 0 else "#5FA97E"};">{"▲" if sem > 0 else "▼"} {fmt(sem).replace("-", "")}</div><div class="d flat">vs. {f_ini}</div></div>']) if sem is not None else ""}
    {"".join([f'<div class="card"><div class="k">Observado BCCh</div><div class="v">${fmt(obs["valor"])}</div><div class="d flat">{obs["fecha"][8:10]}-{["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"][int(obs["fecha"][5:7])-1]}</div></div>']) if obs else ""}
  </div>'''
    filas = []
    prev = None
    # El "dólar observado" que publica el BCCh el dia D es el PROMEDIO del dia
    # habil anterior; por eso a la fila del dia D le corresponde el observado
    # publicado el siguiente dia habil.
    obs_map = dict(ch.get("dolar_serie") or [])
    def _obs_de(fecha):
        f = fecha + dt.timedelta(days=1)
        for _ in range(4):
            if f.strftime("%Y-%m-%d") in obs_map:
                return obs_map[f.strftime("%Y-%m-%d")]
            f += dt.timedelta(days=1)
        return None
    for c in cierres:
        f = c["fecha"]
        var = ((c["c"] - prev) / prev * 100) if prev else None
        o = _obs_de(f)
        filas.append(f"<tr><td>{_fecha_corta(f)}</td><td>${fmt(c['c'])}</td><td>{_flecha(var, 2) if var is not None else '<span class=flat>—</span>'}</td><td>{('$' + fmt(o)) if o else '—'}</td></tr>")
        prev = c["c"]
    tabla = ('<div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Dólar (cierre spot)</th><th>Var. diaria</th><th>Observado BCCh (prom. del día)</th></tr></thead><tbody>'
             + "".join(filas) + "</tbody></table></div>")
    serie = DS.serie_mensual(u["candles"])
    svg, prom, resumen = grafico.usdclp_12m(serie, u["price"], "hoy")
    chart = ""
    if svg:
        m0, m1 = grafico._lab(serie[0][0]), grafico._lab(serie[-1][0])
        chart = f'''<div class="chart-card">
    <div class="chart-title">USD/CLP — variación vs. promedio de los últimos 12 meses</div>
    <div class="chart-meta">Cierres mensuales, {m0} a {m1} ({m1}: mes en curso, precio actual) · Línea de 0 = promedio del período (${fmt(prom, 0)})</div>
    {svg}
  </div>
  <p>{resumen}</p>'''
    return stripe + f"<p>{cont['cambio']}</p>" + tabla + chart


def _sec_commod(D, tz):
    tarjetas = []
    for k, emoji in (("brent", "🛢️"), ("cobre", "🧲"), ("oro", "🥇"), ("plata", "🥈")):
        q = _q(D, k)
        if not q:
            continue
        ant = _antiguedad(q, tz)
        nombre = q["nombre"] + (ant.replace(" (último dato: ", " — ").rstrip(")") if ant else "")
        tarjetas.append(f'<div class="commod-card"><div class="ck">{emoji} {nombre}</div><div class="cv">US${fmt(q["price"], q["dec"])}</div><div class="cd {_cls(q["chg"])}">{_flecha(q["chg"])}</div></div>')
    grid = '<div class="commod-grid">' + "".join(tarjetas) + "</div>"
    filas = []
    for k, etiqueta in (("oro", "Oro (US$/oz)"), ("cobre", "Cobre (US$/lb)"), ("plata", "Plata (US$/oz)"), ("wti", "Petróleo WTI (US$/bbl)")):
        q = _q(D, k)
        if not q:
            continue
        ant = _antiguedad(q, tz)
        filas.append(f"<tr><td>{etiqueta}{(' — último cierre conocido: ' + ant[16:-1]) if ant else ''}</td><td>{fmt(q['prev'], q['dec'])}</td><td>{fmt(q['price'], q['dec'])}</td><td>{_flecha(q['chg'])}</td></tr>")
    tabla = ('<div class="table-wrap"><table><thead><tr><th>Metal / energía</th><th>Cierre ant.</th><th>Hoy</th><th>Var.</th></tr></thead><tbody>'
             + "".join(filas) + "</tbody></table></div>")
    return grid + tabla


def _sec_santiago(b, tz):
    """Bloque 'Bolsa de Santiago' con las acciones del IPSA."""
    if not b:
        return ""
    ses = _fecha_corta(b["sesion"]) if b.get("sesion") else ""
    hora = dt.datetime.fromtimestamp(b["market_time"], tz) if b.get("market_time") else None
    abierto = hora and (dt.datetime.now(tz) - hora).total_seconds() < 30 * 60 and hora.weekday() < 5 and 9 <= hora.hour < 17
    estado = "en curso" if abierto else "cierre"
    nivel = f"{fmt(b['nivel'], 0)}" if b.get("nivel") else "n/d"
    nivel_d = (f"desde {fmt(b['nivel_base'], 2)} ({_fecha_corta(b['nivel_fecha'])}, prensa)" if b.get("nivel_base") else "sin cierre exacto de referencia")
    lider = b["sectores"][0] if b["sectores"] else None
    rezag = b["sectores"][-1] if b["sectores"] else None
    cards = f'''<div class="kpi">
    <div class="card"><div class="k">IPSA estimado · {estado} {ses}</div><div class="v {_cls(b["var"])}">{_flecha(b["var"], 2)}</div><div class="d flat">{b["n"]} acciones, ponderación aprox.</div></div>
    <div class="card"><div class="k">Nivel estimado</div><div class="v">{nivel}</div><div class="d flat">{nivel_d}</div></div>
    <div class="card"><div class="k">Amplitud</div><div class="v"><span class="up">{b["n_alzas"]} ▲</span> · <span class="down">{b["n_bajas"]} ▼</span></div><div class="d flat">alzas · bajas</div></div>
    <div class="card"><div class="k">Sectores</div><div class="v" style="font-size:.8rem">{(lider[0] + " " + pct(lider[1])) if lider else "n/d"}</div><div class="d flat">{("rezagado: " + rezag[0] + " " + pct(rezag[1])) if rezag else ""}</div></div>
  </div>'''
    def fila(a):
        return (f"<tr><td>{html.escape(a['nombre'])} <span style=\"color:var(--soft);font-size:.68rem\">{html.escape(a['sector'])}</span></td>"
                f"<td>${fmt(a['price'], 2 if a['price'] < 1000 else 0)}</td><td>{_flecha(a['chg'], 2)}</td></tr>")
    t_alzas = ('<div class="table-wrap"><table><thead><tr><th>Mayores alzas</th><th>Precio</th><th>Var.</th></tr></thead><tbody>'
               + "".join(fila(a) for a in b["alzas"]) + ("<tr><td colspan=3>Ninguna acción al alza</td></tr>" if not b["alzas"] else "") + "</tbody></table></div>")
    t_bajas = ('<div class="table-wrap"><table><thead><tr><th>Mayores bajas</th><th>Precio</th><th>Var.</th></tr></thead><tbody>'
               + "".join(fila(a) for a in b["bajas"]) + ("<tr><td colspan=3>Ninguna acción a la baja</td></tr>" if not b["bajas"] else "") + "</tbody></table></div>")
    sect = ('<div class="table-wrap"><table><thead><tr><th>Sector</th><th>Var. ponderada</th><th>Acciones</th></tr></thead><tbody>'
            + "".join(f"<tr><td>{html.escape(s)}</td><td>{_flecha(v, 2)}</td><td>{n}</td></tr>" for s, v, n, _ in b["sectores"]) + "</tbody></table></div>")
    chart = grafico.barras_bolsa(b)
    chart_html = f'''<div class="chart-card"><div class="chart-title">Acciones del IPSA — variación de la sesión</div>
    <div class="chart-meta">Las {b["n"]} acciones más grandes, de mayor alza a mayor baja · fuente Yahoo Finance (cierre anterior oficial de cada papel)</div>{chart}</div>''' if chart else ""
    nota = ("<p style=\"font-size:.76rem;color:var(--soft);\">El IPSA estimado se calcula con las acciones de arriba y pesos aproximados; el índice oficial "
            "lo publica la Bolsa de Santiago y puede diferir en décimas. Cuando la prensa informa el cierre exacto, el nivel se ancla a esa cifra.</p>")
    return cards + chart_html + t_alzas + t_bajas + sect + nota


def _sec_bolsa(D, tz):
    filas = []
    ip = D.get("ipsa")
    if ip:
        filas.append(f'<tr><td>IPSA (cierre, según <a href="{html.escape(ip.get("link", ""))}">{html.escape(ip["fuente"])}</a>)</td><td>{("≈" if ip.get("aprox") else "") + fmt(ip["price"], 0 if ip.get("aprox") else 2)}</td><td>{_flecha(ip.get("chg"))}</td></tr>')
    for k in ("ech", "spx", "es", "nq", "stoxx", "nikkei", "hsi", "shanghai", "vix", "btc"):
        q = _q(D, k)
        if not q:
            continue
        filas.append(f"<tr><td>{q['nombre']}{_antiguedad(q, tz)}</td><td>{(q['unidad'] if q['unidad'] not in ('%', '') else '')}{fmt(q['price'], q['dec'])}</td><td>{_flecha(q['chg'])}</td></tr>")
    return ('<div class="table-wrap"><table><thead><tr><th>Índice / activo</th><th>Último</th><th>Var.</th></tr></thead><tbody>'
            + "".join(filas) + "</tbody></table></div>")


def _sec_dolar(a, cont, tz):
    if not a:
        return "<p>Sin datos suficientes para el análisis del dólar hoy.</p>"
    sc = a["score"]
    pos = (sc + 100) / 2
    color_p = "#C1655A" if sc >= 15 else ("#5FA97E" if sc <= -15 else "#8B9099")
    gauge = f'''<div class="gauge">
    <div class="g-lab"><span>▼ presión a la baja</span><span>equilibrio</span><span>presión al alza ▲</span></div>
    <div class="g-bar"><div class="g-mark" style="left:{pos:.1f}%;"></div></div>
    <div class="g-txt" style="color:{color_p}">{a["presion"]} <span style="font-size:.78rem;color:var(--soft);font-family:-apple-system,Segoe UI,sans-serif;">· puntaje {sc:+d} / 100 · foto del momento, no pronóstico</span></div>
  </div>'''
    v = a.get("valor")
    vj = "n/d"
    vj_d = ""
    if v:
        est = "caro" if v["z"] >= 1 else ("barato" if v["z"] <= -1 else "en línea")
        vj = "$" + fmt(v["predicho"], 0)
        vj_d = f'<div class="d {"down" if v["z"] >= 1 else ("up" if v["z"] <= -1 else "flat")}">dólar {est} ({v["gap"]:+.0f})</div>'
    r = a.get("rsi")
    rsi_d = "" if r is None else ("sobrecompra" if r >= 70 else ("sobreventa" if r <= 30 else ("momentum alcista" if r >= 50 else "momentum bajista")))
    kpi = f'''<div class="kpi">
    <div class="card"><div class="k">Tendencia (20/50)</div><div class="v">{a["trend"][0].capitalize()}</div><div class="d flat">m20 {fmt(a["sma20"], 0)} · m50 {fmt(a["sma50"], 0)}</div></div>
    <div class="card"><div class="k">RSI 14</div><div class="v">{fmt(r, 0) if r is not None else "n/d"}</div><div class="d flat">{rsi_d}</div></div>
    <div class="card"><div class="k">Volatilidad</div><div class="v">{fmt(a["atr_pct"], 1) if a.get("atr_pct") else "n/d"}% / día</div><div class="d flat">rango típico ≈ ${fmt(a["price"] * (a["atr_pct"] or 0) / 100, 0)}</div></div>
    <div class="card"><div class="k">Valor justo</div><div class="v">{vj}</div>{vj_d}</div>
  </div>'''
    charts = {n: grafico.velas_dolar(a, n=n) for n in (30, 60, 120)}
    chart_html = f'''<div class="chart-card">
    <div class="chart-title">USD/CLP — últimos <span id="rango-lab">60</span> días</div>
    <div class="range-btns">{"".join(f'<button data-rango="{n}" class="{"on" if n == 60 else ""}">{n} d</button>' for n in (30, 60, 120))}</div>
    <div class="chart-meta">Cierres diarios y rango de cada día · medias móviles 20 y 50 · soportes y resistencias donde el precio giró varias veces · retroceso de Fibonacci más cercano</div>
    {"".join(f'<div class="rango {"on" if n == 60 else ""}" data-rango="{n}">{charts[n]}</div>' for n in (30, 60, 120))}
    {grafico.LEYENDA_VELAS}
  </div>''' if charts[60] else ""
    # motores
    filas = []
    emojis = {"cobre": "🧲", "dxy": "💵", "brl": "🇧🇷", "bono": "🏦"}
    for k, d in a["motores"].items():
        if not d:
            continue
        cr = a["correls"].get(k)
        ap = a["aportes"].get(k, 0)
        emp = '<span class="down">▲ al alza</span>' if ap > 1 else ('<span class="up">▼ a la baja</span>' if ap < -1 else '<span class="flat">— neutro</span>')
        if cr is None:
            barra, ctxt = "", "n/d"
        else:
            w = abs(cr) * 23
            left = 23 if cr >= 0 else 23 - w
            col = "#C1655A" if cr >= 0 else "#5FA97E"
            barra = f'<span class="corr"><i style="left:{left:.0f}px;width:{w:.0f}px;background:{col}"></i></span>'
            ctxt = f"{cr:+.2f}".replace(".", ",")
        rel = "inversa" if k == "cobre" else "directa"
        unidad = "%" if k == "bono" else ""
        filas.append(f"<tr><td>{emojis[k]} {a['nombres'][k]} <span style=\"color:var(--soft);font-size:.7rem\">({rel})</span></td>"
                     f"<td>{fmt(d['price'], 2)}{unidad}</td><td>{_flecha(d['chg'], 2)}</td><td>{ctxt}{barra}</td><td>{emp}</td></tr>")
    motores = ("<h3>Motores del peso</h3>"
               '<div class="table-wrap"><table><thead><tr><th>Motor</th><th>Último</th><th>Var. día</th><th>Correlación 40 d</th><th>Empuje hoy</th></tr></thead><tbody>'
               + "".join(filas) + "</tbody></table></div>"
               '<p style="font-size:.76rem;color:var(--soft);">Correlación: cuánto ha seguido el dólar a cada motor en las últimas semanas (−1 a +1). El cobre mueve al peso al revés (cobre sube, dólar baja); DXY, real y bono, en el mismo sentido. El empuje combina la variación de hoy con esa correlación.</p>')
    # niveles
    p = a["price"]
    res = "".join(f'<div class="row"><b>${fmt(x, 0)}</b><span class="down">+{pct((x / p - 1) * 100)[1:]}</span></div>' for x in a["resistencias"]) or '<div class="row"><span class="flat">sin nivel cercano</span></div>'
    sop = "".join(f'<div class="row"><b>${fmt(x, 0)}</b><span class="up">−{pct((1 - x / p) * 100)[1:]}</span></div>' for x in a["soportes"]) or '<div class="row"><span class="flat">sin nivel cercano</span></div>'
    fibtxt = ""
    if a.get("fib"):
        rc, pc = a["fib"]["cerca"]
        fibtxt = f'<p style="font-size:.8rem;">📐 Fibonacci: impulso reciente {a["fib"]["dir"]} entre ${fmt(a["fib"]["lo"], 0)} y ${fmt(a["fib"]["hi"], 0)}; el retroceso más cercano es <strong>{rc:.3f} = ${fmt(pc, 0)}</strong>, zona donde el precio suele reaccionar.</p>'.replace("0.", "0,")
    niveles = ('<h3>Niveles a vigilar</h3><div class="lvl">'
               f'<div class="card"><div class="k">Resistencias (arriba)</div>{res}</div>'
               f'<div class="card"><div class="k">Soportes (abajo)</div>{sop}</div></div>' + fibtxt)
    # contexto estrategico
    cards = []
    c = a.get("carry")
    if c:
        ef = "te pagan por tener pesos (apoyo estructural al peso)" if c["diff"] >= 0.25 else ("cuesta tener pesos (viento en contra)" if c["diff"] <= -0.25 else "carry casi neutro")
        cards.append(f'<div class="card"><div class="k">💰 Carry (tasas Chile − EE.UU.)</div><div class="v">TPM {fmt(c["tpm"], 2)}% − {fmt(c["us"], 2)}% = <strong>{pct(c["diff"], 2)[:-1]}</strong> pts</div><div class="d">{ef}. Factor de largo plazo, no señal diaria.</div></div>')
    rg = a.get("regimen")
    if rg:
        ef = "presión sobre el peso (aversión al riesgo emergente)" if rg["vix"] >= 22 else ("apoyo al peso (apetito por riesgo)" if rg["vix"] < 16 and rg["vix_chg"] <= 3 else "sin sesgo claro de riesgo")
        sp = f" · S&P 500 {pct(rg['spx_chg'])}" if rg.get("spx_chg") is not None else ""
        cards.append(f'<div class="card"><div class="k">🌡️ Régimen de riesgo global</div><div class="v">{rg["nivel"].capitalize()} · VIX {fmt(rg["vix"], 1)} ({pct(rg["vix_chg"])}){sp}</div><div class="d">{ef}.</div></div>')
    vl = a.get("valoracion")
    if vl:
        lect = "dólar barato / peso fuerte vs. su historia" if vl["pctl"] < 30 else ("dólar caro / peso débil vs. su historia" if vl["pctl"] > 70 else "en rango normal vs. su historia")
        cards.append(f'<div class="card"><div class="k">📐 Valoración 3 años</div><div class="v">Percentil <strong>{vl["pctl"]}</strong> / 100 · promedio ${fmt(vl["prom"], 0)}</div>'
                     f'<div class="pctl"><i style="left:{vl["pctl"]}%"></i></div>'
                     f'<div class="d">{lect}. Rango 3 años: ${fmt(vl["min"], 0)} – ${fmt(vl["max"], 0)}. Ubica el punto de partida, no da timing.</div></div>')
    estrat = "<h3>Contexto estratégico (semanas y meses)</h3><div class=\"strat\">" + "".join(cards) + "</div>" if cards else ""
    # señales y riesgos
    sen = "".join(f"<li>{html.escape(t)} <span style=\"color:var(--soft);font-size:.74rem\">({ap:+.0f})</span></li>" for t, ap in a["senales"][:6])
    senales = f"<h3>Por qué (señales que suman o restan)</h3><ul class=\"plain\">{sen}</ul>" if sen else ""
    rg_html = "".join(f"<li>{html.escape(x)}</li>" for x in a["riesgos"]) or "<li>Sin riesgos técnicos destacados hoy.</li>"
    riesgos = f"<h3>Riesgos del dólar</h3><ul class=\"plain\">{rg_html}</ul>"
    lectura = f"<p>{cont.get('dolar', '')}</p>" if cont.get("dolar") else ""
    nota = '<div class="callout">Tablero cuantitativo del momento (nowcast). Validado con datos de 5 años: el puntaje de presión describe qué empuja al dólar ahora, pero NO anticipa el movimiento del día siguiente. Sirve para entender y gestionar riesgo, no para predecir.</div>'
    return gauge + lectura + kpi + chart_html + motores + niveles + estrat + senales + riesgos + nota


def _sec_cripto(k, cont, tz):
    if not k:
        return "<p>Sin datos cripto hoy.</p>"
    import cripto as CR
    btc = next((m for m in k["monedas"] if m["tk"] == "BTC"), None)
    f, g = k.get("fng"), k.get("global")
    cards = '<div class="kpi">'
    if btc:
        cards += f'<div class="card"><div class="k">₿ Bitcoin</div><div class="v">US${fmt(btc["price"], 0)}</div><div class="d {_cls(btc["chg"])}">{_flecha(btc["chg"])} hoy</div></div>'
    if f:
        cards += (f'<div class="card"><div class="k">Miedo y codicia</div><div class="v">{f["valor"]} <span style="font-size:.72rem;color:var(--soft)">/ 100</span></div>'
                  f'<div class="fng"><i style="left:{f["valor"]}%"></i></div><div class="d flat">{CR.clase_es(f["clase"])}{(" · ayer " + str(f["ayer"])) if f.get("ayer") is not None else ""}</div></div>')
    if g:
        cards += f'<div class="card"><div class="k">Dominancia BTC</div><div class="v">{fmt(g["btc_dom"], 1)}%</div><div class="d flat">ether {fmt(g["eth_dom"], 1)}%</div></div>'
        cards += f'<div class="card"><div class="k">Cap. total</div><div class="v">US${fmt(g["mcap"] / 1e12, 2)} B</div><div class="d {_cls(g["mcap_24h"])}">{_flecha(g["mcap_24h"])} 24 h</div></div>'
    cards += "</div>"
    filas = "".join(f"<tr><td>{m['nombre']} <span style=\"color:var(--soft);font-size:.7rem\">{m['tk']}</span></td><td>US${fmt(m['price'], 2 if m['price'] < 100 else 0)}</td>"
                    f"<td>{_flecha(m['chg'])}</td><td>{_flecha(m['v7']) if m.get('v7') is not None else '—'}</td><td>{_flecha(m['v30']) if m.get('v30') is not None else '—'}</td></tr>"
                    for m in k["monedas"])
    tabla = ('<div class="table-wrap"><table><thead><tr><th>Moneda</th><th>Precio</th><th>Hoy</th><th>7 días</th><th>30 días</th></tr></thead><tbody>' + filas + "</tbody></table></div>")
    chart = ""
    if btc and len(btc.get("candles") or []) >= 30:
        cs = btc["candles"][-30:]
        lo, hi = min(c["c"] for c in cs), max(c["c"] for c in cs)
        pad = (hi - lo) * 0.1 or 1
        lo, hi = lo - pad, hi + pad
        X0, X1, Y0, Y1 = 4, 356, 8, 78
        xs = [X0 + (X1 - X0) * j / (len(cs) - 1) for j in range(len(cs))]
        ys = [Y1 - (c["c"] - lo) / (hi - lo) * (Y1 - Y0) for c in cs]
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        col = "#5FA97E" if cs[-1]["c"] >= cs[0]["c"] else "#C1655A"
        chart = (f'<div class="chart-card"><div class="chart-title">Bitcoin — 30 días</div><div class="chart-meta">Cierres diarios · {fmt(lo + pad, 0)} – {fmt(hi - pad, 0)} US$</div>'
                 f'<svg viewBox="0 0 360 86" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;">'
                 f'<defs><linearGradient id="btcA" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{col}" stop-opacity="0.3"/><stop offset="100%" stop-color="{col}" stop-opacity="0"/></linearGradient></defs>'
                 f'<polygon class="fill" points="{pts} {xs[-1]:.1f},{Y1} {xs[0]:.1f},{Y1}" fill="url(#btcA)"/><polyline class="draw" points="{pts}" fill="none" stroke="{col}" stroke-width="1.8" stroke-linejoin="round"/>'
                 f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="2.6" fill="#fff" stroke="#15171A"/></svg></div>')
    lectura = f"<p>{cont.get('cripto', '')}</p>" if cont.get("cripto") else ""
    nota = '<p style="font-size:.76rem;color:var(--soft);">Fuentes: Yahoo Finance (precios), alternative.me (miedo y codicia), CoinGecko (dominancia y capitalización). Cambios de 7 y 30 días sobre cierres diarios.</p>'
    return lectura + cards + chart + tabla + nota


def _franja_delta(meta):
    """'Desde el informe anterior': cuanto se movio cada activo clave."""
    dl = meta.get("delta")
    if not dl or not dl.get("items"):
        return ""
    items = "".join(f'<span>{html.escape(n)} <b>{v}</b> {_flecha(chg, 1)}</span>' for n, v, chg in dl["items"])
    return f'<div class="delta"><div class="d-lab">Desde el informe del {dl["desde"]}</div><div class="d-row">{items}</div></div>'


def _sec_agenda(A, meta):
    filas = "".join(
        f"<tr><td>{_fecha_corta(e['fecha'])}{(' ' + e['hora']) if e['hora'] else ''}</td><td>{html.escape(e['titulo'])}"
        f"{(' · esperado ' + html.escape(e['forecast'])) if e.get('forecast') else ''}</td><td>{e['impacto']}</td></tr>"
        for e in A[:14])
    if not filas:
        filas = "<tr><td colspan=3>Sin eventos relevantes en los próximos días.</td></tr>"
    out = ('<div class="table-wrap"><table><thead><tr><th>Fecha (hora Chile)</th><th>Evento</th><th>Impacto</th></tr></thead><tbody>'
           + filas + "</tbody></table></div>")
    res = meta.get("resultados") or []
    if res:
        out += "<h3>Datos ya publicados hoy</h3><ul class=\"plain\">" + "".join(
            f"<li><strong>{r['hora']} {html.escape(r['titulo'])}:</strong> {html.escape(str(r['actual']))}"
            f"{(' (esperado ' + html.escape(r['forecast']) + ')') if r['forecast'] else ''}</li>" for r in res) + "</ul>"
    return out


_COLORES = {
    "#C97A45": "var(--copper)", "#C1655A": "var(--red)", "#5FA97E": "var(--green)", "#EDEDEA": "var(--ink)",
    "#8B9099": "var(--soft)", "#15171A": "var(--bg)", "#E3C9AE": "var(--copper-ink)", "#D3D4D2": "var(--text)",
    "#7FA8B8": "var(--ice)", "#2B2F35": "var(--line)", "#DEDFE0": "var(--text)", "#1A1D21": "var(--paper)",
    "#5F6570": "var(--soft2)", "#3A2A1E": "var(--coppersoft)", "#E4A79E": "var(--red-ink)", "#B9BCC2": "var(--text2)",
    "#9AD1B0": "var(--green-ink)", "#3A3F46": "var(--line2)", "#3A2220": "var(--redbg)", "#262A30": "var(--grid)",
    "#23272C": "var(--grid)", "#1F2328": "var(--andes)", "#1B2A21": "var(--greenbg)", "#16191D": "var(--plot)",
    "#1C1F23": "var(--bg2)", "#fff": "var(--white)",
}


def _mercado_abierto(ahora):
    feriado = ahora.strftime("%m-%d") in C.FERIADOS_CL or ahora.strftime("%Y-%m-%d") in C.FERIADOS_CL
    return ahora.weekday() < 5 and not feriado and (9 <= ahora.hour < 17 or (ahora.hour == 9 and ahora.minute >= 30))


def _spark(candles, n=12, ancho=44, alto=14):
    """Mini-grafico de los ultimos n cierres (para el ticker)."""
    cs = [c["c"] for c in (candles or [])[-n:]]
    if len(cs) < 3:
        return ""
    lo, hi = min(cs), max(cs)
    rng = (hi - lo) or 1
    pts = " ".join(f"{ancho * k / (len(cs) - 1):.1f},{alto - 1 - (v - lo) / rng * (alto - 2):.1f}" for k, v in enumerate(cs))
    col = "var(--green)" if cs[-1] >= cs[0] else "var(--red)"
    return f'<svg class="spark" viewBox="0 0 {ancho} {alto}"><polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.3" stroke-linejoin="round"/></svg>'


def _tokenizar(html_txt):
    """Reemplaza los colores fijos de graficos/estilos inline por variables
    CSS, para que el modo claro y el oscuro funcionen tambien en los SVG."""
    for k, v in _COLORES.items():
        html_txt = html_txt.replace(k, v)
    return html_txt


def render(D, N, A, cont, meta, tz):
    ahora = meta["ahora"]
    fecha_larga = _fecha_larga(ahora)
    fecha_iso = ahora.strftime("%Y-%m-%d")
    fecha_corta = f"{ahora.day:02d} {['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][ahora.month-1]} {ahora.year}"
    qi = '<span class="qi-sep">|</span>'.join(f'<a href="#{sid}">{nombre}</a>' for sid, nombre in SECCIONES)
    modo = cont.get("modo")
    aviso = ""
    if modo != "ia":
        aviso = f'<div class="callout">Edición automática por reglas (titulares agrupados por sección). Redacción con IA no disponible hoy: {html.escape(meta.get("ia_motivo") or "")}.</div>'
    # I  (+ "Última hora": lo mas reciente, con antigüedad)
    s1 = _li(cont["relevante"], "newsflash", tags=True)
    uh = (N or {}).get("ultima_hora") or []
    if uh:
        import noticias as _NT
        s1 += ('<h3>Última hora <span style="font-weight:400;color:var(--soft);text-transform:none;letter-spacing:0">· publicado en las últimas horas</span></h3><ul class="plain">'
               + "".join(f'<li><span class="tag" style="color:var(--soft)">{_NT.hace(it)}</span>'
                         f'<a href="{html.escape(it.get("link") or "")}">{html.escape(it["titulo"])}</a>'
                         f' <span style="color:var(--soft);font-size:.78rem">· {html.escape(it.get("fuente") or "")}</span></li>' for it in uh)
               + "</ul>")
    # II
    s2 = ""
    for b in cont["internacional"]:
        s2 += f"<h3>{b['h3']}</h3>" if b.get("h3") else ""
        s2 += "".join(f"<p>{p}</p>" for p in b.get("parrafos") or [])
        if b.get("items"):
            s2 += _li(b["items"])
    s3 = _li(cont["chile"])
    s4 = _li(cont["geopolitica"])
    s5 = "".join(f"<p>{p}</p>" for p in cont["tasas"]) or "<p>Sin novedades relevantes en tasas hoy.</p>"
    s6 = _sec_cambio(D, tz, cont)
    s7 = _sec_dolar(meta.get("dolar"), cont, tz)
    s8 = _sec_commod(D, tz) + f"<p>{cont['commodities']}</p>"
    s9 = (f"<p>{cont['bolsa']}</p>"
          + '<div class="tabs"><button class="on" data-tab="scl">Bolsa de Santiago</button><button data-tab="glob">Bolsas globales</button></div>'
          + '<div class="tab-panel on" data-tab="scl">' + (_sec_santiago(meta.get("bolsa"), tz) or "<p>Sin datos de la Bolsa de Santiago hoy.</p>") + "</div>"
          + '<div class="tab-panel" data-tab="glob">' + _sec_bolsa(D, tz) + "</div>")
    s10 = _sec_cripto(meta.get("cripto"), cont, tz)
    s11 = _sec_agenda(A, meta)
    s12 = _li(cont["riesgos"])
    cuerpos = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12]
    titulos = ["Lo más relevante", "Panorama internacional", "Chile: política y economía", "Riesgos geopolíticos",
               "Inflación y tasas de política monetaria", "Tipo de cambio", "Dólar en profundidad", "Oro, cobre y plata",
               "Mercado bursátil", "Cripto", "Agenda económica", "Principales riesgos de la jornada"]
    chev = '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>'
    secs = "".join(f'<section id="{SECCIONES[i][0]}"><div class="secnum">{ROMANOS[i]}.</div><div class="sec-head"><h2>{titulos[i]}</h2>{chev}</div><div class="sec-body">{cuerpos[i]}</div></section>'
                   for i in range(12))
    nav = "".join(f'<a href="#{sid}">{nombre}</a>' for sid, nombre in SECCIONES)
    fuentes = ("Fuentes: Yahoo Finance (dólar, euro, commodities, tasas y bolsas globales), mindicador.cl (UF, dólar observado, TPM), "
               "Google Noticias (titulares de prensa chilena e internacional), ForexFactory (calendario). "
               "El IPSA se toma de los titulares de prensa porque no existe una fuente gratuita en tiempo real; el litio no se incluye por la misma razón.")
    doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="format-detection" content="telephone=no">
<meta name="theme-color" content="#0F1114">
<title>{C.NOMBRE} — {fecha_larga.split(' ', 1)[1]}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
</head>
<body>
<main>
<header>
  <div class="logo-slot anim"><div class="wordmark"><span class="a">A</span><span class="rest">Mercados</span></div><div class="rule"></div></div>
  <div class="eyebrow anim">{C.EYEBROW}</div>
  <div class="headline-frame anim"><div class="headline-label">El Titular AM</div><h1>{cont['titular']}</h1></div>
  <div class="sub anim">Lectura de 5 min · Mercados globales y locales · <span class="live {'on' if _mercado_abierto(ahora) else ''}"><i></i>{'Bolsa de Santiago abierta' if _mercado_abierto(ahora) else 'mercado local cerrado'}</span></div>
  <div class="range anim"><span>{C.CIUDAD}, {fecha_larga}</span><span>{("Texto de las " + meta["texto_de"] + " · datos actualizados a las ") if meta.get("texto_de") else "Datos hasta las "}{ahora:%H:%M} hrs <span id="hace" data-ts="{int(ahora.timestamp())}"></span></span></div>
  <div class="anim">{ANDES}</div>
</header>
<div class="sticky-bar">
  <div class="sb-top"><span class="wm"><span class="a">A</span><span class="rest">Mercados</span></span><span class="sdate">{fecha_corta}</span>
    <button class="btn" id="theme" aria-label="Cambiar tema"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg><span>Claro</span></button>
    <button class="btn" id="share" aria-label="Compartir"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M12 3v13M7 8l5-5 5 5"/></svg><span>Compartir</span></button>
  </div>
  <nav class="sb-nav">{nav}<a href="#" id="fold" class="fold">Plegar todo</a></nav>
</div>
<div class="ticker-wrap"><div class="ticker-track">{_ticker(D, tz, meta.get("bolsa"))}</div></div>
<div class="quickindex"><div class="qi-label">En este informe</div><div class="qi-row">{qi}</div></div>
{_franja_delta(meta)}
{aviso}
{secs}
</main>

<div id="progress"></div>
<div class="tip" id="tip"></div>
<button id="totop" class="btn" aria-label="Volver arriba">↑ arriba</button>
<script>
(function(){{
  var root=document.documentElement;
  // tema: guardado > por defecto oscuro (marca)
  try{{var t=localStorage.getItem('amercados-theme'); if(t) root.setAttribute('data-theme',t);}}catch(e){{}}
  function setTheme(t){{root.setAttribute('data-theme',t); try{{localStorage.setItem('amercados-theme',t);}}catch(e){{}} var b=document.getElementById('theme'); if(b) b.querySelector('span').textContent = t==='light'?'Oscuro':'Claro';}}
  var bt=document.getElementById('theme'); if(bt){{bt.querySelector('span').textContent = root.getAttribute('data-theme')==='light'?'Oscuro':'Claro'; bt.addEventListener('click',function(){{setTheme(root.getAttribute('data-theme')==='light'?'dark':'light');}});}}
  // compartir
  var sh=document.getElementById('share'); if(sh){{ if(!navigator.share && !navigator.clipboard){{sh.style.display='none';}}
    sh.addEventListener('click',function(){{var url=location.href.indexOf('http')===0?location.href:'https://joalvarezaratto-bit.github.io/amercados/'; var data={{title:document.title,text:document.querySelector('h1').textContent,url:url}};
      if(navigator.share){{navigator.share(data).catch(function(){{}});}} else if(navigator.clipboard){{navigator.clipboard.writeText(url); sh.querySelector('span').textContent='Copiado'; setTimeout(function(){{sh.querySelector('span').textContent='Compartir';}},1500);}} }});}}
  // progreso + boton arriba
  var pr=document.getElementById('progress'), tt=document.getElementById('totop');
  function onScroll(){{var h=document.documentElement; var p=(h.scrollTop||document.body.scrollTop)/((h.scrollHeight-h.clientHeight)||1); pr.style.width=(p*100)+'%'; tt.classList.toggle('on',(h.scrollTop||document.body.scrollTop)>600);}}
  window.addEventListener('scroll',onScroll,{{passive:true}}); onScroll();
  tt.addEventListener('click',function(){{window.scrollTo({{top:0,behavior:'smooth'}});}});
  // ticker: tocar para pausar
  var tw=document.querySelector('.ticker-wrap'); if(tw) tw.addEventListener('click',function(){{tw.classList.toggle('paused');}});
  // secciones plegables
  document.querySelectorAll('section .sec-head').forEach(function(h){{h.setAttribute('role','button'); h.setAttribute('tabindex','0');
    function tg(){{h.parentNode.classList.toggle('collapsed');}}
    h.addEventListener('click',tg); h.addEventListener('keydown',function(e){{if(e.key==='Enter'||e.key===' '){{e.preventDefault();tg();}}}});}});
  // navegacion con seccion activa
  var links=[].slice.call(document.querySelectorAll('.sb-nav a')).filter(function(a){{return (a.getAttribute('href')||'').length>1;}}); var secs=links.map(function(a){{return document.querySelector(a.getAttribute('href'));}});
  if('IntersectionObserver' in window){{var cur=null; var io=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{cur=e.target.id;}}}}); links.forEach(function(a){{var on=a.getAttribute('href')==='#'+cur; a.classList.toggle('active',on); if(on) a.scrollIntoView({{block:'nearest',inline:'center',behavior:'smooth'}});}});}},{{rootMargin:'-40% 0px -55% 0px'}}); secs.forEach(function(s){{if(s) io.observe(s);}});}}
  // tablas ordenables
  function num(s){{s=s.replace(/[^\d,\-−.]/g,'').replace('−','-'); if(/,\d{{1,2}}$/.test(s)) s=s.replace(/\./g,'').replace(',','.'); else s=s.replace(/,/g,''); var v=parseFloat(s); return isNaN(v)?null:v;}}
  document.querySelectorAll('table').forEach(function(tb){{var ths=tb.querySelectorAll('thead th'); ths.forEach(function(th,ci){{th.title='Ordenar'; th.addEventListener('click',function(){{var asc=th.classList.contains('sorted')&&!th.classList.contains('asc'); ths.forEach(function(x){{x.classList.remove('sorted','asc');}}); th.classList.add('sorted'); if(asc) th.classList.add('asc');
    var rows=[].slice.call(tb.querySelectorAll('tbody tr')); rows.sort(function(a,b){{var ta=a.children[ci]?a.children[ci].textContent.trim():'', tb2=b.children[ci]?b.children[ci].textContent.trim():''; var na=num(ta), nb=num(tb2); var r=(na!==null&&nb!==null)?na-nb:ta.localeCompare(tb2,'es'); return asc?r:-r;}}); var body=tb.querySelector('tbody'); rows.forEach(function(r){{body.appendChild(r);}});}});}});}});
  // pestañas
  document.querySelectorAll('.tabs').forEach(function(t){{var bs=t.querySelectorAll('button'); bs.forEach(function(b){{b.addEventListener('click',function(){{bs.forEach(function(x){{x.classList.remove('on');}}); b.classList.add('on'); var wrap=t.parentNode; wrap.querySelectorAll('.tab-panel').forEach(function(p){{p.classList.toggle('on',p.getAttribute('data-tab')===b.getAttribute('data-tab'));}});}});}});}});
  // tooltips en graficos (elementos con data-tip)
  var tip=document.getElementById('tip');
  function show(e,el){{tip.innerHTML=el.getAttribute('data-tip'); tip.classList.add('on'); var x=e.touches?e.touches[0].clientX:e.clientX, y=e.touches?e.touches[0].clientY:e.clientY; tip.style.left=Math.max(70,Math.min(window.innerWidth-70,x))+'px'; tip.style.top=y+'px';}}
  document.querySelectorAll('[data-tip]').forEach(function(el){{el.addEventListener('mousemove',function(e){{show(e,el);}}); el.addEventListener('mouseleave',function(){{tip.classList.remove('on');}}); el.addEventListener('touchstart',function(e){{show(e,el);}},{{passive:true}}); el.addEventListener('touchend',function(){{setTimeout(function(){{tip.classList.remove('on');}},1200);}});}});
  // revelar al hacer scroll + arrancar animaciones de graficos
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // solo se 'esconden' para animar los bloques que estan BAJO el primer pantallazo; lo visible nunca se oculta
  var vh=window.innerHeight||800; document.querySelectorAll('section, .delta, .quickindex').forEach(function(s){{if(s.getBoundingClientRect().top>vh*0.9) s.classList.add('reveal');}});
  function revealByScroll(){{var lim=(window.innerHeight||800)+ (window.scrollY||0) - 40; document.querySelectorAll('.reveal:not(.in)').forEach(function(s){{if(s.getBoundingClientRect().top+(window.scrollY||0)<lim) s.classList.add('in');}});}}
  window.addEventListener('scroll',revealByScroll,{{passive:true}}); window.addEventListener('resize',revealByScroll);
  if('IntersectionObserver' in window && !reduce){{var ro=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{e.target.classList.add('in'); ro.unobserve(e.target);}}}});}},{{rootMargin:'0px 0px -8% 0px'}}); document.querySelectorAll('.reveal').forEach(function(s){{ro.observe(s);}});
    var go=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{e.target.classList.add('go'); go.unobserve(e.target);}}}});}},{{threshold:.35}}); document.querySelectorAll('.chart-card').forEach(function(c){{go.observe(c);}});}}
  else{{document.querySelectorAll('.reveal').forEach(function(s){{s.classList.add('in');}}); document.querySelectorAll('.chart-card').forEach(function(c){{c.classList.add('go');}});}}
  setTimeout(function(){{document.querySelectorAll('.reveal:not(.in)').forEach(function(s){{s.classList.add('in');}});}},2500);
  // cifras que cuentan hasta su valor (tarjetas)
  function countUp(el){{var txt=el.textContent; var m=txt.match(/-?[0-9][0-9.,]*/); if(!m) return; var raw=m[0]; var dec=(raw.match(/,(\d+)$/)||[,''])[1].length; var v=parseFloat(raw.replace(/\./g,'').replace(',','.')); if(isNaN(v)||Math.abs(v)>1e9) return;
    var t0=null, dur=900; function fmt(x){{var s=x.toFixed(dec); var p=s.split('.'); p[0]=p[0].replace(/\B(?=(\d{{3}})+(?!\d))/g,'.'); return p.join(',');}}
    function step(ts){{if(!t0) t0=ts; var k=Math.min(1,(ts-t0)/dur); k=1-Math.pow(1-k,3); el.textContent=txt.replace(raw,fmt(v*k)); if(k<1) requestAnimationFrame(step); else el.textContent=txt;}}
    requestAnimationFrame(step);}}
  if(!reduce && 'IntersectionObserver' in window){{var co=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{countUp(e.target); co.unobserve(e.target);}}}});}},{{threshold:.6}}); document.querySelectorAll('.kpi .card .v, .stripe .card .v, .commod-card .cv').forEach(function(el){{if(!el.querySelector('span,svg')) co.observe(el);}});}}
  // "hace X min"
  var hc=document.getElementById('hace'); if(hc){{var ts=parseInt(hc.getAttribute('data-ts'),10)*1000; function upd(){{var m=Math.round((Date.now()-ts)/60000); hc.textContent = m<1?'· recién':(m<60?'· hace '+m+' min':(m<1440?'· hace '+Math.round(m/60)+' h':'· hace '+Math.round(m/1440)+' d'));}} upd(); setInterval(upd,30000);}}
  // plegar / desplegar todo
  var fd=document.getElementById('fold'); if(fd){{fd.addEventListener('click',function(e){{e.preventDefault(); var secs=document.querySelectorAll('section'); var plegar=fd.textContent.indexOf('Plegar')===0; secs.forEach(function(s){{s.classList.toggle('collapsed',plegar);}}); fd.textContent=plegar?'Desplegar todo':'Plegar todo';}});}}
  // selector de rango del grafico del dolar
  document.querySelectorAll('.range-btns button').forEach(function(b){{b.addEventListener('click',function(){{var card=b.closest('.chart-card'); card.querySelectorAll('.range-btns button').forEach(function(x){{x.classList.remove('on');}}); b.classList.add('on'); var r=b.getAttribute('data-rango'); card.querySelectorAll('.rango').forEach(function(d){{d.classList.toggle('on',d.getAttribute('data-rango')===r);}}); var lab=document.getElementById('rango-lab'); if(lab) lab.textContent=r; card.classList.remove('go'); void card.offsetWidth; card.classList.add('go');}});}});
  // animar el marcador de presion
  var gm=document.querySelector('.g-mark'); if(gm){{var L=gm.style.left; gm.style.left='50%'; setTimeout(function(){{gm.style.left=L;}},80);}}
}})();
</script>
<footer>
  <b>{C.NOMBRE}</b> · {C.CIUDAD}, {fecha_larga} · Datos hasta las {ahora:%H:%M} hrs · Información de carácter referencial e informativo, elaborada automáticamente a partir de fuentes públicas de mercado y titulares de prensa. Describe lo ocurrido y el estado actual; no es pronóstico, no constituye asesoría financiera ni recomendación de inversión.<br>{fuentes}{(' · Redacción: IA (' + html.escape(meta.get('ia_uso', C.AI_MODEL)) + ')') if modo == 'ia' else ''}
</footer>
</body>
</html>"""
    head, sep, body = doc.partition("</style>")
    return head + sep + _tokenizar(body)
