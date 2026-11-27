/* OEMPLUS-B2 v1.5: OemplusLive.js -- transport + toestand voor live ritdata van de Pi (192.168.0.1:8765).
 * ES5 only (Presto 2.12 / Opera 12.10), ASCII, marker OEMPLUS-B2. Geen DOM behalve 1 tijdelijke script-tag (JSONP).
 *
 * Transport (fallback-orde per verbindingscyclus): WebSocket ws://HOST:8765/live -> JSONP <script> /live.js -> XHR /live.json.
 *   - WS: open; geen geldig frame binnen 3 s -> dicht en door naar JSONP. WS die werkte maar > 5 s stil is -> dicht, nieuwe cyclus.
 *   - JSONP/XHR: 1 verzoek tegelijk, timeout 4 s, bij succes elke 2 s pollen (API-advies). Fout tijdens pollen -> nieuwe cyclus.
 *   - Alle drie mislukt -> wachten met backoff 2 -> 4 -> 8 -> 16 -> 30 s, dan opnieuw vanaf WS. Reset na een geldig frame.
 * Een hartslag-interval (1 s) en hooguit 1 open WS / 1 script-tag / 1 XHR, alleen zolang er >= 1 abonnee is.
 * Bij 0 abonnees: WS dicht, tag weg, XHR afgebroken, interval weg (niets blijft lopen op de CMU).
 * Geldig frame = object met v === 1 en numerieke ts; anders bad++ en negeren. Alleen /live wordt opgehaald (geen /trip.js). */
(function (W) {  // W = window
    var HOST = (W.OEMPLUS_LIVE_HOST || "192.168.0.1");
    var PORT = (W.OEMPLUS_LIVE_PORT || 8765);
    var BASE = "http://" + HOST + ":" + PORT;
    var WS_URL = "ws://" + HOST + ":" + PORT + "/live";
    var BACKOFF = [2, 4, 8, 16, 30];
    var WS_FIRST_MS = 3000, WS_IDLE_MS = 5000, REQ_TIMEOUT_MS = 4000, POLL_MS = 2000, BEAT_MS = 1000;

    var S = {
        subs : [], transport : null, last : null, rxMs : 0, bad : 0, retryS : 0,
        started : false, beat : null,
        phase : "idle",      // idle | ws-wait | ws | jsonp-try | jsonp | xhr-try | xhr | backoff
        phaseT : 0, retryAt : 0, backoffIdx : 0,
        ws : null, tag : null, cbName : null, xhr : null, reqT : 0, lastReq : 0, reqId : 0
    };

    function now() { return new Date().getTime(); }
    function log(m) {
        try { if (W.OemplusInject && W.OemplusInject._liveLog) { W.OemplusInject._liveLog(m); return; } } catch (e) { }
        try { if (W.console && W.console.log) { W.console.log("OEMPLUS-LIVE " + m); } } catch (e2) { }
    }
    function valid(d) { return (d && typeof d === "object" && d.v === 1 && typeof d.ts === "number") ? d : null; }
    function ageS() { return S.rxMs ? Math.round((now() - S.rxMs) / 100) / 10 : null; }
    function emit() {
        var d = S.last, a = ageS();
        for (var i = 0; i < S.subs.length; i++) { try { S.subs[i](d, a, S); } catch (e) { log("sub fout " + e); } }
    }
    function onData(data) {
        var v = valid(data);
        if (!v) { S.bad++; if (S.bad < 5 || S.bad % 50 === 0) { log("ongeldig frame (bad=" + S.bad + ")"); } return false; }
        S.last = v; S.rxMs = now(); S.backoffIdx = 0; S.retryS = 0;
        emit();
        return true;
    }
    /* running_log roteert na ~800 regels (L0-les): alleen verbonden/verloren loggen en de eerste 2 mislukte cycli,
     * daarna stil tot er weer verbinding is (geen regel per poging/frame). */
    function quiet() { return S.backoffIdx >= 2 && !S.transport; }
    function setPhase(p) {
        if (S.phase !== p && (p === "ws" || p === "jsonp" || p === "xhr" || p === "idle" || !quiet())) { log("fase " + S.phase + " -> " + p); }
        S.phase = p; S.phaseT = now();
    }

    /* ---- opruimen per transport ---- */
    function wsKill() {
        try { if (S.ws) { var w = S.ws; S.ws = null; w.onopen = null; w.onmessage = null; w.onerror = null; w.onclose = null; w.close(); } } catch (e) { S.ws = null; }
    }
    function tagKill() {
        try { if (S.tag && S.tag.parentNode) { S.tag.parentNode.removeChild(S.tag); } } catch (e) { }
        S.tag = null;
        if (S.cbName) { try { W[S.cbName] = function () { }; } catch (e2) { } S.cbName = null; }
    }
    function xhrKill() {
        try { if (S.xhr) { var x = S.xhr; S.xhr = null; x.onreadystatechange = null; x.abort(); } } catch (e) { S.xhr = null; }
    }
    function killAll() { wsKill(); tagKill(); xhrKill(); }

    /* ---- WebSocket ---- */
    function wsStart() {
        killAll();
        setPhase("ws-wait");
        try {
            var w = new WebSocket(WS_URL);
            S.ws = w;
            w.onmessage = function (ev) {
                if (S.ws !== w) { return; }
                var d = null;
                try { d = JSON.parse(ev.data); } catch (e) { S.bad++; return; }
                if (onData(d) && S.phase !== "ws") { S.transport = "ws"; setPhase("ws"); }
            };
            w.onerror = function () { };
            w.onclose = function () {
                if (S.ws !== w) { return; }
                S.ws = null;
                if (S.phase === "ws") { log("ws dicht na werken -> nieuwe cyclus"); backoff(); }
                else { jsonpTry(); }
            };
        } catch (e) { S.ws = null; log("ws except " + e); jsonpTry(); }
    }

    /* ---- JSONP (script-tag, unieke callback per verzoek) ---- */
    function jsonpReq(okPhase) {
        tagKill();
        S.reqId++;
        var id = S.reqId, name = "OemplusLiveCb" + (id % 1000);
        S.cbName = name; S.reqT = now(); S.lastReq = S.reqT;
        try {
            W[name] = function (data) {
                if (id !== S.reqId) { return; }
                tagKill();
                if (onData(data)) { S.transport = "jsonp"; setPhase("jsonp"); } else { reqFail("jsonp"); }
            };
            var tag = document.createElement("script");
            tag.onerror = function () { if (id === S.reqId) { tagKill(); reqFail("jsonp"); } };
            tag.src = BASE + "/live.js?t=" + S.reqT + "&cb=" + name;
            S.tag = tag;
            document.getElementsByTagName("head")[0].appendChild(tag);
        } catch (e) { log("jsonp except " + e); tagKill(); reqFail("jsonp"); }
    }
    function jsonpTry() { killAll(); setPhase("jsonp-try"); jsonpReq(); }

    /* ---- XHR ---- */
    function xhrReq() {
        xhrKill();
        S.reqId++;
        var id = S.reqId;
        S.reqT = now(); S.lastReq = S.reqT;
        try {
            var x = new XMLHttpRequest();
            S.xhr = x;
            x.open("GET", BASE + "/live.json?t=" + S.reqT, true);
            x.onreadystatechange = function () {
                if (x.readyState !== 4 || id !== S.reqId) { return; }
                S.xhr = null;
                var d = null;
                if (x.status === 200) { try { d = JSON.parse(x.responseText); } catch (e) { S.bad++; } }
                if (d && onData(d)) { S.transport = "xhr"; setPhase("xhr"); } else { reqFail("xhr"); }
            };
            x.send(null);
        } catch (e) { log("xhr except " + e); xhrKill(); reqFail("xhr"); }
    }
    function xhrTry() { killAll(); setPhase("xhr-try"); xhrReq(); }

    /* fout van een verzoek: in de probeer-keten -> volgende transport; tijdens pollen -> nieuwe cyclus (backoff) */
    function reqFail(kind) {
        if (S.phase === "jsonp-try") { xhrTry(); return; }
        backoff();
    }
    function backoff() {
        killAll();
        if (S.transport) { log("transport " + S.transport + " weg"); }
        S.transport = null;
        var s = BACKOFF[Math.min(S.backoffIdx, BACKOFF.length - 1)];
        if (S.backoffIdx < BACKOFF.length - 1) { S.backoffIdx++; }
        S.retryS = s; S.retryAt = now() + s * 1000;
        setPhase("backoff");
        if (S.backoffIdx <= 2) { log("retry over " + s + " s" + (S.backoffIdx === 2 ? " (verdere pogingen stil)" : "")); }
        emit();   // abonnees zien retryS/oud
    }

    /* ---- hartslag: timeouts, pollen, backoff aftellen (1 interval, alleen met abonnees) ---- */
    function beat() {
        try {
            if (!S.started) { return; }
            var n = now(), p = S.phase;
            if (p === "ws-wait") {
                if (n - S.phaseT >= WS_FIRST_MS) { if (!quiet()) { log("ws: geen frame in 3 s -> jsonp"); } jsonpTry(); }
            } else if (p === "ws") {
                if (n - S.rxMs > WS_IDLE_MS) { log("ws stil > 5 s"); backoff(); }
            } else if (p === "jsonp-try" || p === "xhr-try" || ((p === "jsonp" || p === "xhr") && (S.tag || S.xhr))) {
                if (n - S.reqT >= REQ_TIMEOUT_MS) { if (!quiet()) { log(p + " timeout"); } tagKill(); xhrKill(); reqFail(p); }
            } else if (p === "jsonp" || p === "xhr") {
                if (n - S.lastReq >= POLL_MS) { if (p === "jsonp") { jsonpReq(); } else { xhrReq(); } }
            } else if (p === "backoff") {
                S.retryS = Math.max(0, Math.ceil((S.retryAt - n) / 1000));
                if (n >= S.retryAt) { S.retryS = 0; wsStart(); }
            }
        } catch (e) { log("beat fout " + e); }
    }

    function start() {
        if (S.started) { return; }
        S.started = true; S.backoffIdx = 0; S.retryS = 0;
        log("start host=" + HOST + ":" + PORT);
        S.beat = setInterval(beat, BEAT_MS);
        wsStart();
    }
    function stopAll() {
        S.started = false;
        if (S.beat) { clearInterval(S.beat); S.beat = null; }
        killAll();
        S.transport = null; S.retryS = 0;
        setPhase("idle");
        log("stop");
    }

    W.OemplusLive = {
        subscribe : function (fn) {
            if (typeof fn !== "function") { return; }
            if (S.subs.indexOf(fn) === -1) { S.subs.push(fn); }
            start();
            try { fn(S.last, ageS(), S); } catch (e) { }
        },
        unsubscribe : function (fn) {
            var i = S.subs.indexOf(fn);
            if (i >= 0) { S.subs.splice(i, 1); }
            if (S.subs.length === 0 && S.started) { stopAll(); }
        },
        reconnectNow : function () {
            if (!S.started) { return; }
            S.backoffIdx = 0; S.retryS = 0;
            log("reconnectNow");
            wsStart();
        },
        status : function () {
            return {
                transport : S.transport, phase : S.phase, retryS : S.retryS, bad : S.bad,
                rxAgeS : ageS(), last : S.last, subs : S.subs.length, started : S.started,
                open : { ws : !!S.ws, tag : !!S.tag, xhr : !!S.xhr, beat : !!S.beat }
            };
        }
    };
    log("geladen OemplusLive.js");
})(window);
