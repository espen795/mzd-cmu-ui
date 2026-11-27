/* OEMPLUS-B2 rit-live proto: B2DriveView.js (ontwerp 2026-11-27, host-only, ES5/Presto, ASCII).
 * Prototype van de weergave + navigatie voor het paneel "Rit & rijstijl" (zie ../../ONTWERP-RIT.md).
 * Gebruikt door de mockups (tools/build_mocks_rit.py) en bedoeld als startpunt voor de bouwer (ML4):
 *   B2DriveView.build(panelDiv)          -> vaste DOM (kop, lijn, body, voet), 1x
 *   B2DriveView.render(panelDiv, model)  -> vult de ZICHTBARE pagina (innerHTML van body + kop/voet)
 *   B2DriveView.nav(model, eventId)      -> {consumed:true/false, page:n, action:null|"reconnect"}
 *   B2DriveView.touch(model, x0, x1, y1) -> idem voor swipe/tik (paneel-coordinaten)
 *   B2DriveView.startPage(data)          -> 0 (Deze rit) of 3 (Vorige rit, niveau N)
 * model = { page, data (laatste geldige snapshot = ruw frame API v1, zie LIVE-RIJSTIJL-API-v1.md, of null), rxAgeS (s sinds laatste frame lokaal),
 *           drive (bool, al met hysterese bepaald door de controller), transport ("ws"/"jsonp"/"xhr"/null),
 *           retryS (s tot volgende poging) }
 * Geen timers, geen netwerk, geen globale listeners in dit bestand: dat doet OemplusLive.js / de paneelklasse. */
(function (W) {
    var PAGES = [
        { id : "nu",      title : "Deze rit",              short : "Deze rit" },
        { id : "schakel", title : "Schakelen",             short : "Schakelen" },
        { id : "gas",     title : "Optrekken &amp; remmen", short : "Optrekken" },
        { id : "vorige",  title : "Vorige rit",            short : "Vorige rit" },
        { id : "deel",    title : "Deelcijfers",           short : "Deelcijfers" },
        { id : "trend",   title : "Trend",                 short : "Trend" },
        { id : "uitleg",  title : "Uitleg",                short : "Uitleg" }
    ];
    var STALE_S = 5;
    var ARROW = "\u2192", UP = "\u25B2", DOWN = "\u25BC", DASH = "&ndash;", MID = " &middot; ";

    function isNum(v) { return typeof v === "number" && !isNaN(v); }
    function num(v, d) { return isNum(v) ? v.toFixed(d).replace(".", ",") : DASH; }
    function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
    function pct(v, max) { if (!isNum(v) || max <= 0) { return 0; } var p = v / max * 100; return p < 0 ? 0 : (p > 100 ? 100 : Math.round(p)); }
    function obj(o) { return (o && typeof o === "object") ? o : null; }
    var MONTHS = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];
    function dateNl(s) {
        var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s || ""));
        return m ? (parseInt(m[3], 10) + " " + MONTHS[parseInt(m[2], 10) - 1]) : esc(s || DASH);
    }


    /* v1.5 (review): de pagina's lezen DIRECT de echte API v1 (docs/designs/LIVE-RIJSTIJL-API-v1.md):
     *   nu{kmh,rpm_schatting,rijdend}, rit{km,rijdend_min,cijfer,oordeel,cijfer_voorlopig,schakelingen,soepel,hard_optrekken,
     *   hard_remmen,opschakelen_rpm,recent{venster_s,schakelingen,soepel,merkbaar,hard,calm_2min,...},ruwste{min,van,naar,kmh,oordeel}},
     *   vorige_rit{start,km,rijdend_min,cijfer,oordeel,deelcijfers{naam:cijfer},tip,trend[]}, top-level age_s/seg.
     * Geen vertaling naar het oude contract (trip / last_trip); model.data blijft altijd het ruwe frame.
     * Belangrijk: rit.soepel/rit.schakelingen = HELE rit; rit.recent.* = alleen de laatste 2 min (nooit door elkaar). */
    var PART_SHORT = {
        "Inkoppelen (koppeling op)" : "Inkoppelen", "Gas los / koppeling in" : "Gas los / koppeling",
        "Schakelmoment" : "Schakelmoment", "Rustig optrekken" : "Rustig optrekken", "Anticiperen / remmen" : "Anticiperen",
        "Motorvriendelijk" : "Motorvriendelijk", "Constante snelheid" : "Constant rijden"
    };
    function rit(d) { return d ? obj(d.rit) : null; }
    function vor(d) { return d ? obj(d.vorige_rit) : null; }
    function nu(d) { return d ? obj(d.nu) : null; }

    /* ---- toestand ---- */
    function conn(m) {
        if (!m || !obj(m.data)) { return "none"; }
        if (!isNum(m.rxAgeS) || m.rxAgeS > STALE_S) { return "old"; }
        if (isNum(m.data.age_s) && m.data.age_s > STALE_S) { return "nostream"; }   // Pi leeft, D-Bus-stroom niet
        return "live";
    }
    function engineOff(d) { var n = nu(d); return !n || !isNum(n.rpm_schatting); }
    function calmWord(c) { return !isNum(c) ? "Rit loopt" : (c >= 0.6 ? "Rustig" : "Onrustig"); }
    function calmCls(c) { return !isNum(c) ? "B2DriveFillNone" : (c >= 0.6 ? "B2DriveFillOk" : "B2DriveFillWarn"); }

    function chip(m, st) {
        if (st === "none") { return '<span class="B2DriveChipDot B2DriveDotGrey"></span><span class="B2DriveChipTxt">geen data</span>'; }
        if (st === "old") { return '<span class="B2DriveChipDot B2DriveDotAmber"></span><span class="B2DriveChipTxt B2DriveAmber">oud' + MID + Math.round(m.rxAgeS) + ' s</span>'; }
        if (st === "nostream") { return '<span class="B2DriveChipDot B2DriveDotAmber"></span><span class="B2DriveChipTxt B2DriveAmber">geen autodata</span>'; }
        if (m.drive) { return '<span class="B2DriveChipDot B2DriveDotOk"></span><span class="B2DriveChipTxt">rijdend</span>'; }
        if (engineOff(m.data)) { return '<span class="B2DriveChipDot B2DriveDotGrey"></span><span class="B2DriveChipTxt">motor uit</span>'; }
        return '<span class="B2DriveChipDot B2DriveDotOk"></span><span class="B2DriveChipTxt">live</span>';
    }

    /* ---- bouwstenen ---- */
    function tile(x, y, w, h, kicker, value, sub) {
        return '<div class="B2DriveTile' + (h < 100 ? ' B2DriveTileS' : '') + '" style="left:' + x + 'px;top:' + y + 'px;width:' + w + 'px;height:' + h + 'px">' +
            '<div class="B2DriveKick">' + kicker + '</div><div class="B2DriveVal">' + value + '</div>' +
            (sub ? '<div class="B2DriveSub">' + sub + '</div>' : '') + '</div>';
    }
    function empty(t1, t2, t3) {
        return '<div class="B2DriveEmpty"><div class="B2DriveEmptyRing"></div><div class="B2DriveEmptyT1">' + t1 + '</div>' +
            '<div class="B2DriveEmptyT2">' + t2 + '</div>' + (t3 ? '<div class="B2DriveEmptyT3">' + t3 + '</div>' : '') + '</div>';
    }
    function noTrip() { return empty("Nog geen ritgegevens", "De eerste analyse komt 10&ndash;60 s na de start.", ""); }
    function noLast() { return empty("Nog geen vorige rit", "Die komt na de eerste afgeronde rit", "van minstens 0,5 km."); }
    function gearTxt(g) { return (g === null || g === undefined || g === "") ? DASH : esc(String(g)); }

    /* ---- pagina's (lezen de echte API v1) ---- */
    function pNu(m) {
        var t = rit(m.data);
        if (!t) { return noTrip(); }
        var sm = isNum(t.soepel) && isNum(t.schakelingen) ? (t.soepel + ' <span class="B2DriveUnit">van</span> ' + t.schakelingen) : DASH;
        var rc = obj(t.recent), c = rc && isNum(rc.calm_2min) ? rc.calm_2min : null;
        /* cijfer: cijfer_voorlopig (< 10 km of < 10 min) NOOIT als eindcijfer tonen */
        var cij, cijSub;
        if (t.cijfer_voorlopig === true || !isNum(t.cijfer)) { cij = '<span class="B2DriveVal30">volgt</span>'; cijSub = "na 10 km en 10 min"; }
        else { cij = num(t.cijfer, 1) + ' <span class="B2DriveUnit">/ 10</span>'; cijSub = t.oordeel ? esc(t.oordeel) : ""; }
        var calm = '<div class="B2DriveTile" style="left:348px;top:140px;width:328px;height:124px"><div class="B2DriveKick">RUST &middot; LAATSTE 2 MIN</div>' +
            '<div class="B2DriveVal B2DriveVal30">' + (engineOff(m.data) ? "motor uit" : calmWord(c)) + '</div>' +
            '<div class="B2DriveMiniTrack"><div class="B2DriveFill ' + calmCls(c) + '" style="width:' + (isNum(c) ? pct(c, 1) : 0) + '%"></div></div></div>';
        return tile(0, 0, 328, 124, "AFSTAND", num(t.km, 1) + ' <span class="B2DriveUnit">km</span>', num(t.rijdend_min, 0) + " min rijden") +
            tile(348, 0, 328, 124, "CIJFER DEZE RIT", cij, cijSub) +
            tile(0, 140, 328, 124, "SOEPEL GESCHAKELD", sm, "hele rit") +
            calm;
    }
    function pSchakel(m) {
        var t = rit(m.data);
        if (!t || !isNum(t.schakelingen)) { return noTrip(); }
        var tot = t.schakelingen, s = isNum(t.soepel) ? t.soepel : 0, rest = tot - s;
        if (rest < 0) { rest = 0; }
        var seg = function (v, cls) { return v > 0 ? '<div class="B2DriveSeg ' + cls + '" style="width:' + pct(v, tot) + '%"></div>' : ''; };
        var rc = obj(t.recent), rTxt = rc && isNum(rc.schakelingen) ?
            (rc.schakelingen > 0 ? ('laatste 2 min: ' + rc.schakelingen + 'x (' + (rc.soepel || 0) + ' soepel, ' + (rc.merkbaar || 0) + ' merkbaar, ' + (rc.hard || 0) + ' hard)')
                : 'laatste 2 min: niet geschakeld') : '';
        var w = obj(t.ruwste), worst = w ? (gearTxt(w.van) + ' ' + ARROW + ' ' + gearTxt(w.naar) + (isNum(w.min) ? ' <span class="B2DriveUnit">min ' + Math.round(w.min) + '</span>' : '')) : DASH;
        return '<div class="B2DriveHero">' + tot + '<span class="B2DriveHeroUnit">schakelingen deze rit</span></div>' +
            '<div class="B2DriveStack">' + (tot > 0 ? seg(s, "B2DriveFillOk") + seg(rest, "B2DriveFillWarnSoft") : '') + '</div>' +
            '<div class="B2DriveLegend"><span class="B2DriveSw B2DriveFillOk"></span>' + s + ' soepel' +
            '<span class="B2DriveSw B2DriveFillWarnSoft"></span>' + rest + ' niet soepel</div>' +
            (rTxt ? '<div class="B2DriveRecent">' + rTxt + '</div>' : '') +
            tile(0, 184, 328, 84, "OPSCHAKELEN ROND", (isNum(t.opschakelen_rpm) ? "~" + (Math.round(t.opschakelen_rpm / 50) * 50) : DASH) + ' <span class="B2DriveUnit">tpm</span>', "") +
            tile(348, 184, 328, 84, "RUWSTE MOMENT", worst, "");
    }
    function pGas(m) {
        var t = rit(m.data);
        if (!t) { return noTrip(); }
        var rc = obj(t.recent);
        var r2 = function (v) { return rc && isNum(v) ? ("laatste 2 min: " + v) : ""; };
        return tile(0, 0, 328, 124, "HARD OPTREKKEN", (isNum(t.hard_optrekken) ? t.hard_optrekken : DASH) + ' <span class="B2DriveUnit">keer</span>', r2(rc && rc.hard_optrekken)) +
            tile(348, 0, 328, 124, "HARD REMMEN", (isNum(t.hard_remmen) ? t.hard_remmen : DASH) + ' <span class="B2DriveUnit">keer</span>', r2(rc && rc.hard_remmen)) +
            tile(0, 140, 676, 124, "HOOGSTE SNELHEID DEZE RIT", num(t.max_kmh, 0) + ' <span class="B2DriveUnit">km/h</span>', "stevig = optrekken &gt; 0,25 g of remmen &gt; 0,30 g");
    }
    function trendDelta(l) {
        var tr = l.trend;
        if (Object.prototype.toString.call(tr) !== "[object Array]" || tr.length < 2 || !isNum(tr[tr.length - 2]) || !isNum(l.cijfer)) { return ""; }
        var d = l.cijfer - tr[tr.length - 2];
        if (Math.abs(d) < 0.05) { return '<div class="B2DriveDelta">gelijk aan de rit ervoor</div>'; }
        return '<div class="B2DriveDelta"><span class="' + (d > 0 ? "B2DriveUpArrow" : "B2DriveDownArrow") + '">' + (d > 0 ? UP : DOWN) + '</span> ' +
            num(Math.abs(d), 1) + ' t.o.v. de rit ervoor</div>';
    }
    function tipShort(t) {   /* max ~5 regels (BOUW: Presto kent geen meerregel-ellipsis) -> afkappen op een woordgrens */
        t = String(t || "").replace(/\s+/g, " ");
        if (t.length <= 230) { return t; }
        var c = t.lastIndexOf(" ", 226);
        return t.substring(0, c > 150 ? c : 226) + " \u2026";
    }
    function pVorige(m) {
        var l = vor(m.data);
        if (!l || !isNum(l.cijfer)) { return noLast(); }
        var dm = /^(\d{4}-\d{2}-\d{2})/.exec(String(l.start || ""));
        return '<div class="B2DriveScore">' + num(l.cijfer, 1) + '</div><div class="B2DriveScoreSub">van 10' + MID + 'eigen schaal</div>' +
            '<div class="B2DriveFacts"><div>' + dateNl(dm ? dm[1] : "") + (l.oordeel ? MID + esc(l.oordeel) : "") + '</div><div>' + num(l.km, 0) + ' km' + MID + num(l.rijdend_min, 0) + ' min</div>' +
            trendDelta(l) + '</div>' +
            (l.tip ? '<div class="B2DriveTip"><div class="B2DriveTipTxt"><span class="B2DriveKick B2DriveTipKick">TIP </span>' + esc(tipShort(l.tip)) + '</div></div>' : '');
    }
    function pDeel(m) {
        var l = vor(m.data), p = l && obj(l.deelcijfers);
        if (!p) { return noLast(); }
        var keys = [], low = null, i, k, v, h = "";
        for (k in p) { if (p.hasOwnProperty(k)) { keys.push(k); } }   /* volgorde = API/PDF */
        keys = keys.slice(0, 7);
        for (i = 0; i < keys.length; i++) { v = p[keys[i]]; if (isNum(v) && (low === null || v < p[low])) { low = keys[i]; } }
        for (i = 0; i < keys.length; i++) {
            k = keys[i]; v = p[k];
            h += '<div class="B2DrivePart' + (k === low ? ' B2DrivePartLow' : '') + '" style="top:' + (i * 38) + 'px">' +
                '<div class="B2DrivePLabel">' + esc(PART_SHORT[k] || k) + '</div><div class="B2DrivePTrack"><div class="B2DriveFill ' +
                (!isNum(v) ? "B2DriveFillNone" : (v < 6 ? "B2DriveFillWarn" : (v >= 8 ? "B2DriveFillOk" : "B2DriveFillOkDim"))) + '" style="width:' + pct(v, 10) + '%"></div></div>' +
                '<div class="B2DrivePVal">' + num(v, 1) + '</div></div>';
        }
        return h;
    }
    function pTrend(m) {
        var l = vor(m.data), tr = l && l.trend, i, n, v, h = "", sum = 0, cnt = 0, slots = 8, x;
        if (Object.prototype.toString.call(tr) !== "[object Array]" || tr.length === 0) { return noLast(); }
        tr = tr.slice(-slots); n = tr.length;
        for (i = 0; i < slots; i++) {
            x = i * 84 + 20;
            v = (i >= slots - n) ? tr[i - (slots - n)] : null;
            var last = (i === slots - 1);
            if (isNum(v)) {
                sum += v; cnt++;
                h += '<div class="B2DriveTVal" style="left:' + (x - 20) + 'px;top:' + (176 - Math.round(v * 14) - 34) + 'px">' + num(v, 1) + '</div>' +
                    '<div class="B2DriveTBar ' + (last ? "B2DriveFillOk" : "B2DriveFillOkDim") + '" style="left:' + x + 'px;top:' + (176 - Math.round(v * 14)) + 'px;height:' + Math.round(v * 14) + 'px"></div>';
            } else {
                h += '<div class="B2DriveTEmpty" style="left:' + x + 'px"></div>';
            }
            h += '<div class="B2DriveTLab' + (last ? ' B2DriveTLabLast' : '') + '" style="left:' + (x - 20) + 'px">' + (last ? "vorige" : (isNum(v) ? "-" + (slots - 1 - i) : "")) + '</div>';
        }
        return '<div class="B2DriveTBase"></div>' + h +
            '<div class="B2DriveFootLine">Gemiddeld ' + (cnt ? num(sum / cnt, 1) : DASH) + ' over ' + cnt + (cnt === 1 ? ' rit' : ' ritten') + MID + 'hoger = rustiger</div>';
    }
    function pUitleg(m, st) {
        var d = obj(m.data), tr = { ws : "WebSocket", jsonp : "script (JSONP)", xhr : "XHR" };
        var connTxt = st === "none" ? ("niet verbonden" + MID + "volgende poging over " + (isNum(m.retryS) ? m.retryS : DASH) + " s")
            : ((tr[m.transport] || "?") + MID + "laatste data " + num(m.rxAgeS, 1) + " s geleden");
        return '<div class="B2DriveTxt" style="top:0">Cijfers 0&ndash;10 zijn een <b>eigen schaal</b>, geen Mazda i-DM.</div>' +
            '<div class="B2DriveTxt" style="top:34px">Ritcijfer is voorlopig tot 10 km en 10 min.</div>' +
            '<div class="B2DriveTxt" style="top:68px">Stevig: optrekken &gt; 0,25 g' + MID + 'remmen &gt; 0,30 g</div>' +
            '<div class="B2DriveTxt" style="top:102px">Toerental is een schatting (&plusmn; 10 %).</div>' +
            '<div class="B2DriveSep" style="top:144px"></div>' +
            '<div class="B2DriveTxt B2DriveTxt2" style="top:156px">Pi' + MID + connTxt + '</div>' +
            '<div class="B2DriveTxt B2DriveTxt2" style="top:190px">' + (d && d.seg ? "segment " + esc(String(d.seg).replace(/\.raw$/, "")) + MID : "") +
            (st === "none" ? "Pi start ~1 min na contact aan" : (st === "nostream" ? "Pi ok, nog geen D-Bus-stroom" : "data van de auto ok")) + '</div>' +
            '<div class="B2DriveTxt B2DriveTxt3" style="top:226px">Druk op de draaiknop = nu opnieuw verbinden</div>';
    }

    /* ---- publiek ---- */
    function build(panel) {
        panel.innerHTML = '<div class="B2DriveHead"><div class="B2DriveTitle"></div><div class="B2DriveChip"></div></div>' +
            '<div class="B2DriveRule"></div><div class="B2DriveBody"></div>' +
            '<div class="B2DriveFoot"><div class="B2DrivePrev"></div><div class="B2DriveDots"></div><div class="B2DriveNext"></div></div>';
        var c = panel.childNodes;
        panel.b2 = { title : c[0].childNodes[0], chip : c[0].childNodes[1], body : c[2], prev : c[3].childNodes[0], dots : c[3].childNodes[1], next : c[3].childNodes[2] };
        return panel.b2;
    }
    /* Besluit de gebruiker: ook rijdend GEEN rustscherm-lock -- gewoon de pagina's (opent op Deze rit), zelf doorscrollen met
     * draaien/kantelen mag; rustig/groot, verversen max 1x/s (controller), geen animaties/pop-ups. Rijdend: geen touch. */
    function render(panel, m) {
        var e = panel.b2 || build(panel);
        var st = conn(m), p = PAGES[m.page] || PAGES[0], html, i, dots = "";
        if (st === "none" && p.id !== "uitleg") {
            html = empty("Nog geen ritdata", "De Pi start ongeveer 1 minuut na contact aan.", "Opnieuw proberen over " + (isNum(m.retryS) ? m.retryS : DASH) + " s");
        } else {
            html = ({ nu : pNu, schakel : pSchakel, gas : pGas, vorige : pVorige, deel : pDeel, trend : pTrend, uitleg : pUitleg })[p.id](m, st);
        }
        e.title.innerHTML = p.title;
        e.chip.innerHTML = chip(m, st);
        e.body.className = "B2DriveBody B2DrivePage-" + p.id + ((st === "old" || st === "nostream") ? " B2DriveStale" : "");
        e.body.innerHTML = html;
        for (i = 0; i < PAGES.length; i++) {
            dots += '<span class="B2DriveDot' + (i === m.page ? " B2DriveDotCur" : "") + '" data-page="' + i + '"></span>';
        }
        e.dots.innerHTML = dots;
        e.dots.style.marginLeft = "-" + Math.round(PAGES.length * 26 / 2) + "px";
        e.prev.innerHTML = m.page > 0 ? "&lsaquo; " + PAGES[m.page - 1].short : "";
        e.next.innerHTML = m.page < PAGES.length - 1 ? PAGES[m.page + 1].short + " &rsaquo;" : "";
        panel.className = "B2DrivePanel" + (m.drive ? " B2DriveDriving" : "");
    }
    function go(m, d) {
        var n = m.page + d;
        if (n < 0 || n >= PAGES.length) { return { consumed : true, page : m.page, action : null }; }   /* geen wrap (OEM-lijsten ook niet) */
        return { consumed : true, page : n, action : null };
    }
    /* Mazda-bediening (tuiEvents uit Multicontroller/MMUI, zie ONTWERP-RIT.md par.2).
     * heldMs = tijd tussen selectStart en select (de controller meet dit, zoals List2Ctrl met longPressTimeout 1500). */
    var LONG_MS = 1500;
    function nav(m, ev, heldMs) {
        var r = { consumed : false, page : m.page, action : null };
        switch (ev) {
        case "cw": case "rightStart":
            return go(m, 1);      /* ook rijdend (besluit de gebruiker) */
        case "ccw": case "leftStart":
            return go(m, -1);
        case "select":
            r.consumed = true;
            if (heldMs >= LONG_MS) { r.action = "close"; return r; }   /* lang indrukken = paneel dicht, terug naar de lijst (ook rijdend) */
            if (PAGES[m.page].id === "uitleg") { r.action = "reconnect"; } else { r.page = 0; }
            return r;
        case "left": case "right": case "up": case "down": case "upStart": case "downStart":
        case "selectStart": case "selectHold": case "leftHold": case "rightHold": case "upHold": case "downHold":
        case "acceptFocusInit": case "acceptFocusFromLeft": case "acceptFocusFromRight": case "acceptFocusFromTop": case "acceptFocusFromBottom":
            r.consumed = true;
            return r;
        default:
            return r;   /* controllerActive, touchActive, lostFocus, goBack, ...: door naar het OEM-template */
        }
    }
    /* touch: x/y in paneel-coordinaten (paneel = 740x416 op pagina 60,64). Alleen bij stilstand. */
    function touch(m, x0, x1, y1) {
        var r = { consumed : true, page : m.page, action : null }, dx = x1 - x0;
        if (m.drive) { return r; }
        if (dx <= -80) { return go(m, 1); }
        if (dx >= 80) { return go(m, -1); }
        if (y1 >= 352) {
            var left = 382 - Math.round(PAGES.length * 26 / 2), idx = Math.floor((x1 - left) / 26);
            if (idx >= 0 && idx < PAGES.length) { r.page = idx; return r; }
            if (x1 < 200) { return go(m, -1); }
            if (x1 > 540) { return go(m, 1); }
        }
        return r;
    }
    /* startpagina: Vorige rit (3) zolang de huidige rit < 0,5 km (of nog geen rit-analyse) en er een vorige rit is */
    function startPage(d) {
        var t = rit(obj(d)), l = vor(obj(d));
        return (l && isNum(l.cijfer) && (!t || !isNum(t.km) || t.km < 0.5)) ? 3 : 0;
    }
    W.B2DriveView = { PAGES : PAGES, STALE_S : STALE_S, LONG_MS : LONG_MS, build : build, render : render, nav : nav, touch : touch, startPage : startPage, conn : conn };
})(window);
