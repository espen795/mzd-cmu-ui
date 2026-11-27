/*
 OEMPLUS-INJECT v1.4 (2026-11-27) -- B2 home-UI + B2-submenu's in een DRAAIENDE v74-GUI, zonder Opera-reload.
 v1.4 = kopie van de GEFIXTE v1.2 (commit b61c219e) + P0 uit ui-mockup-v1.0/submenus/BOUWPLAN.md:
     - body-klasse OemplusB2 bij "B2 aan" (eraf bij uit), ALLEEN op niet-protected schermen (bewaker setSubClass,
     ECHT synchroon: wrapper op framework._callHandleContext leest de BINNENKOMENDE contextObj (uiaId/ctxtId) en
     haalt de klasse weg VOORDAT het origineel draait, plus een tweede wrapper op framework._transitionChange die
     voor de originele aanroep de klasse weghaalt op basis van focusStack[0] + de app-context en na de aanroep
     setSubClass() draait; vangnet = guardTick. Bij een fout in een wrapper: klasse eraf (fail-safe = OEM) en het
     origineel wordt ALTIJD aangeroepen. Protected lijst =
     SUBMENU-INVENTARIS-v74.md par.5: backupparking/camera, warnguide, mobile911, androidauto, carplay, emnavi,
     system DisplayOff/IdleStandby/WaitForEnding/IntroAnimation/QuickStartLoop/PowerDownAnimation, diag, tutorial);
   - CSS-lader die PATHS.subCss (B2Sub-00..40) in vaste volgorde laadt; ontbrekend bestand = overslaan zonder
     fout (P1-P4 landen later los). De links worden NIET per contextwissel verplaatst (rehang = stylesheet
     out/in per wissel = kans op een OEM-flits; specificiteit + !important wint sowieso van late lazy-CSS, H3);
     ze worden alleen bij "B2 aan" achteraan <head> gehangen;
   - P0-basis-CSS common/oemplusb2/css/B2Sub-00-base.css + assets (tools/assets/_lib.py + p0_base.py).
   De bestaande body.OemplusB2Home (home-specifiek) is ongewijzigd; OemplusB2 is de globale submenu-klasse.
 v1.2 = B2-home verbeteringen na de eerste live-test (docs/designs/LIVE-LOG-2026-11-26-inject.md):
 v1.1 = verwerking R-cmu-review (docs/reviews/REVIEW-INJECT-V1-R-cmu.md): H2, M1, M2, M3, M4, L4, L5.
 v1.2 = B2-home verbeteringen na de eerste live-test (docs/designs/LIVE-LOG-2026-11-26-inject.md):
   1. SBN (Status Bar Notification) blijft ZICHTBAAR op B2-home, maar in B2-stijl: de OEM-statusbalk is op home
      verborgen, de SbnCtrl (eigen control op document.body, top 1px) krijgt een donkere B2-onderlaag + subtiele
      slide-in via -o-transition (SbnCtrl-oemplusb2.css, nieuw sbnCss). De B2-kop zit rechts (klok y=71, rijen
      beginnen op y=121) en de bovenste 64 px zijn gereserveerd voor de banner (x 59-685, y 1-59, bottom 61 incl.
      1px-randen), dus de banner overlapt niets. Fix B2: de verborgen startpositie top:-60px geldt alleen zolang
      de watcher-klasse body.B2SbnWatch er is -> een SBN is nooit fail-hidden.
   2. Straatnaam-SBN's van de navigatie (MMUI_EMNAVI -> emnaviApp StateSbn_NextTurn -> Style05, type
      navigationNear/typeC of navigationFar/typeJ) worden ONDERDRUKT zolang B2 aan staat: ze zijn gefilterd in
      eigen wrappers op framework.common.startTimedSbn/showStateSbn/endStateSbn/cancelTimedSbn (instantie-eigenschappen;
      Common.js wordt niet herladen). Alleen die twee types; typeK staat al op de OEM-blacklist (Common.js:145-147)
      en veiligheids-/foutmeldingen (typeF errorNotification, typeI deviceRemoved, ...) raken we NOOIT aan.
      Een al getoonde straatnaam-SBN wordt bij 'B2 aan' direct beeindigd (endStateSbn), zodat de banner direct weg is.
   3. Contextpanelen worden bij 'B2 aan' direct gevuld uit de GECACHETE state van systemApp (de 4 statusberichten
      kwamen voor de injectie al binnen): _communicationsDataList (SelectNotifications/SelectCallHistory/SelectSms/
      SelectEmail label1), _masterApplicationDataList (SelectSchedMaint image2), _SchedMaintDueStatus, en de audio-
      status uit de _masterEntertainmentDataList/_masterApplicationDataList now-playing iconen. De B2-control
      leest die bij _b2Start in (zie MainMenuCtrl-oemplusb2.js).

 Geladen door de haak onderaan de 4 ecoenergy-templates (apps/ecoenergy/templates/<X>/js/<X>Tmplt.js), die de
 framework pas laadt bij de eerste opening van Applicaties > Brandstofverbruik (lazy, _addTmpltFiles). Met de bind-mount
 van de proefkopie over /jci/gui komt die eerste lezing dus uit de proefkopie.

 Bij elke opening van het eco-scherm legt OemplusInject.attach(tmpl) een keuzepaneel over het template:
   - "B2 aan (home + submenu's)"  laadt MainMenuCtrl-oemplusb2.js (= B2 v1.1 MainMenuCtrl.js, ongewijzigd) en zet
                                    window.MainMenuCtrl op een BEWAAKTE constructor (guardedCtor, H2): gooit de
                                    B2-constructor, dan wordt de halve B2-DOM verwijderd, alles teruggedraaid en op
                                    dezelfde plek de originele MainMenuCtrl gebouwd. Elke B2-methode die template/
                                    framework/systemApp aanroept zit in try/catch; bij een fout: B2 uit (volgende Home
                                    origineel) zonder dat de framework-transitie blijft hangen.
                                    CSS (M2/M3): originele MainMenuCtrl.css-link wordt uit de DOM gehaald (niet
                                    'disabled') en later op exact dezelfde plek teruggezet; nooit terwijl het OEM-home
                                    in beeld is (dan uitgesteld tot de eerste B2-constructie).
   - "B2 uit (tot herstart)"      alles terug: originele constructor, originele CSS, handlers, body-klasse weg.
   - "Info"                        status + versie + fouten.
   - "Verder naar Eco-scherm"      paneel weg; het originele eco-scherm werkt ongewijzigd (Terug = MMUI).
 Bewaker (M1/M4), elke 500 ms zodra B2 ooit aangevraagd is: window.MainMenuCtrl staat altijd op wat het hoort te zijn
 (bewaakte B2-constructor als aan, anders het origineel) en body.OemplusB2Home bestaat alleen in de home-context.
 Laden (M1/M3): succes = de registerCtrlLoaded("MainMenuCtrl")-aanroep aan het eind van het B2-bestand (geslikt);
 onload/onerror zijn alleen versnellers, de terugval is de timeout; een te laat binnenkomend bestand verandert niets.
 Niets wordt opgeslagen: alles leeft in RAM van de draaiende pagina. Herstart CMU = fabriek.
 ES5 only (Presto 2.12 / Opera 12.10); elke functie in try/catch; fout = geen wijziging + melding in Info/log.
*/

/* OEMPLUS-INJECT */
try { log.addSrcFile("OemplusInject.js", "system"); } catch (eOemplusSrc) { }

(function ()
{
    if (window.OemplusInject)
    {
        return;
    }

    var VERSION = "inject-v1.5 (2026-11-27)";
    var PATHS = {
        mmJs     : "apps/system/controls/MainMenu/js/MainMenuCtrl-oemplusb2.js",
        mmCss    : "apps/system/controls/MainMenu/css/MainMenuCtrl-oemplusb2.css",
        mmCssOrg : "apps/system/controls/MainMenu/css/MainMenuCtrl.css",
        sbCss    : "common/controls/StatusBar/css/StatusBarCtrl-oemplusb2.css",
        sbnCss   : "common/controls/Sbn/css/SbnCtrl-oemplusb2.css",
        /* OEMPLUS-INJECT v1.4 / P0: B2-submenu-CSS in VASTE volgorde (00 -> 10 -> 20 -> 30 -> 40). Een ontbrekend
         * bestand wordt overgeslagen zonder fout (de <link> 404t; de lader logt het), zodat P1-P4 later los
         * kunnen landen. Volgorde = tie-breaker bij gelijke specificiteit binnen B2 (BOUWPLAN). */
        subCss   : ["common/oemplusb2/css/B2Sub-00-base.css",
                    "common/oemplusb2/css/B2Sub-10-list2.css",
                    "common/oemplusb2/css/B2Sub-20-dialog3.css",
                    "common/oemplusb2/css/B2Sub-30-tabs-slider-button.css",
                    "common/oemplusb2/css/B2Sub-40-media-input.css",
                    /* v1.4 / P5-eco (optie B) + P6-phone: 50 en 60 landen los (BOUWPLAN eco-bel).
                     * Ontbrekend bestand = 404 = stil overgeslagen (bestaand P0-gedrag). */
                    "common/oemplusb2/css/B2Sub-50-eco.css",
                    "common/oemplusb2/css/B2Sub-60-phone.css",
                    /* v1.5: paneel "Rit & rijstijl" (BOUWPLAN-RIT); geladen met de andere B2Sub's,
                     * de JS (B2DriveView/OemplusLive) wordt lazy geladen bij eerste keer openen. */
                    "common/oemplusb2/css/B2Sub-70-drive.css"]
    };
    /* OEMPLUS-INJECT v1.4 / P0: body-klasse voor ALLE B2-submenu's (body.OemplusB2-prefix in B2Sub-*.css).
     * De klasse staat ALLEEN als S.subOn && niet protected (bewaker setSubClass, zie hieronder). */
    var SUB_CLASS = "OemplusB2";
    /* OEMPLUS-INJECT v1.4 / P0: protected schermen (SUBMENU-INVENTARIS-v74.md par.5 + DESIGN-SYSTEEM par.9).
     * Formaat: "uiaId" (hele app) of "uiaId/ctxtId". Camera staat VOOR alles: de bewaker moet de klasse
     * weghalen VOORDAT het camera-template gebouwd/paint (wrapper op _callHandleContext leest de binnenkomende
     * contextObj + wrapper op _transitionChange; vangnet = guardTick). */
    var PROTECTED_APPS = {
        "backupparking" : true,   // achteruitrijcamera / parking sensors (veiligheid)
        "warnguide"     : true,   // wettelijke waarschuwingen
        "mobile911"     : true,   // noodoproep 911
        "androidauto"   : true,   // AA projectie (NoCtrl)
        "carplay"       : true,   // CarPlay projectie (NoCtrl)
        "emnavi"        : true,   // native NNG navi
        "diag"          : true,   // diagnosemodus
        "tutorial"      : true    // eerste-keer-uitleg
    };
    var PROTECTED_CTXT = {
        "system/DisplayOff"          : true,
        "system/IdleStandby"         : true,
        "system/WaitForEnding"       : true,
        "system/IntroAnimation"      : true,
        "system/QuickStartLoop"      : true,
        "system/PowerDownAnimation"  : true
    };
    var NOTE_MSGS = ["StatusUpdateNotifications", "StatusUpdateAudioSource", "StatusUpdateMissedCallCount", "StatusUpdateSchedMaint"];
    /* OEMPLUS-INJECT v1.2: SBN-filter. Alleen de navigatie-straatnaam-SBN's (Style05, type navigationNear/typeC
     * of navigationFar/typeJ -- de enigen die Style05 gebruiken, emnaviApp.js:757) worden onderdrukt zolang B2 aan
     * staat. typeK is al geblokkeerd door de OEM-blacklist (Common.js:145-147). Veiligheidsmeldingen (errorNotification
     * typeF, deviceRemoved typeI, ...) worden NOOIT onderdrukt. */
    var SBN_NAV_TYPES = { "navigationNear" : true, "navigationFar" : true };
    var SBN_NAV_STYLE = "Style05";
    var SBN_APIS = ["startTimedSbn", "showStateSbn", "endStateSbn", "cancelTimedSbn"];
    var SBN_NAV_IDS = { "emnaviemnaviTurnByTurnStateSbn" : true, "emnaviemnaviTurnByTurnTimedSbn" : true };
    var SBN_DROPPED = ["emnaviTurnByTurnStateSbn", "emnaviTurnByTurnTimedSbn"];
    // B2-methoden die van buiten (MainMenuTmplt, framework, systemApp) worden aangeroepen -> elk in try/catch
    var GUARD_METHODS = ["handleControllerEvent", "startTransitionFrom", "endTransitionTo", "getContextCapture", "restoreContext",
                         "finishPartialActivity", "cleanUp", "setText", "getRemoteUiButtonStatus", "oemplusB2Update"];
    var LOAD_TIMEOUT_MS = 8000;
    var GUARD_MS = 500;
    var BODY_CLASS = "OemplusB2Home";

    var S = {
        on : false,            // B2 actief (window.MainMenuCtrl = bewaakte B2-constructor)
        loading : false,       // laadpoging loopt (paneel wacht op antwoord)
        expectReg : false,     // registerCtrlLoaded("MainMenuCtrl") van het B2-bestand wordt verwacht en geslikt
        regHooked : false,     // eigen wrapper op framework.registerCtrlLoaded staat
        origReg : null,        // originele framework.registerCtrlLoaded
        origCtor : null,       // originele (v74) MainMenuCtrl-constructor
        b2Ctor : null,         // B2-constructor (na laden)
        wrapper : null,        // bewaakte constructor (guardedCtor)
        origHandlers : {},     // msgId -> originele gebonden handler uit systemApp._messageTable
        links : {},            // eigen <link>-elementen
        removedOrg : [],       // uit de DOM gehaalde originele MainMenuCtrl.css-links: {node, parent, next}
        cssOn : false,         // B2-CSS actief (originele MainMenuCtrl.css-link uit de DOM)
        sbnHooked : false,     // eigen wrappers op framework.common.*Sbn* staan
        origSbnApis : {},      // api-naam -> originele Common-functie
        sbnDropped : 0,        // aantal onderdrukte nav-SBN's sinds 'aan'
        liveB2 : 0,            // aantal B2-instanties dat nog niet opgeruimd is
        b2Errors : 0,          // fouten in bewaakte B2-methoden/constructor
        guardTimer : null,
        subOn : false,         // OEMPLUS-INJECT v1.4 / P0: B2-submenu's aan (body.OemplusB2 + B2Sub-* links)
        subLinks : [],         // eigen B2Sub-<link>-elementen (in PATHS.subCss-volgorde)
        ctxtHooked : false,    // eigen wrapper op framework._callHandleContext staat
        origCallHandle : null, // originele framework._callHandleContext (lokaal VAR in de wrapper, zie F9)
        transHooked : false,   // eigen wrapper op framework._transitionChange staat
        origTransition : null, // originele framework._transitionChange
        pendingCtxt : null,    // binnenkomende protected context (uit _callHandleContext), voor _transitionChange
        transPending : null,   // v1.4 (live-flap): "uia/ctxt" van een protected transitie die NU loopt (tussen
                               // _callHandleContext en het _transitionChange-einde); setSubClass mag dan de
                               // klasse NIET terugzetten op basis van getCurrentApp() (dat is nog de OUDE app)
        lastSub : null,        // laatste bewaker-actie (alleen bij wissel gelogd, zie F4/V3)
        ritHooked : false,     // v1.5: runtime-patch item "Rit & rijstijl" in Applicaties staat
        ritItem : null,        // het item dat we in _masterApplicationDataList.items zetten (direct na ecoenergy)
        ritNames : [],         // appName-entries toegevoegd aan _applicationsCtxtWiseAppNames["Applications"]
        ritCtxts : [],         // context-namen waarvoor we appNames toevoegden
        ritPanel : null,       // levende RitPanel-instantie (of null)
        ritLiveSubs : 0,       // aantal OemplusLive-abonnees (paneel + home-contextregel)
        termHooked : false,    // v1.4 punt 8: runtime-patch Terminal-item op de geladen systemApp staat
        termOrigCb : null,     // originele _menuItemSelectCallback (prototype-functie, als bound in properties)
        termItem : null,       // het terminal-item dat we in _masterApplicationDataList.items zetten
        termNames : [],        // appName-entries die we aan _applicationsCtxtWiseAppNames["Applications"] toevoegen
        termCtxts : [],        // context-namen waarvoor we appNames toevoegden (voor opruimen)
        tpmsHooked : false,    // v1.4 / P5-eco: TPMS-wrappers (read-only) op warnguide + TPMS-divs staan
        tpmsOrigHandler : null,// originele handler (tabel-entry of prototype)
        tpmsOrigTable : null,  // de _messageTable waarin we wrapten
        tpmsDivs : [],         // [divL, divR] in .EcoStatusCtrl (aangemaakt per ecoStatusCtrl-instantie)
        tpmsState : "none",    // "none" (nooit data) | "ok" | "low" | "fault"
        tpmsSeen : false,      // true zodra warnguide ooit een WarningStatus-bericht kreeg
        tpmsPulseTimer : null, // puls-timer voor "Bandendruk laag"
        tpmsPulseOn : false,   // pulse-fase
        tpmsCtrlObs : null,    // MutationObserver op de ecoStatusCtrl-div (nieuwe instantie -> divs opnieuw)
        lastErr : "",
        events : [],           // korte geschiedenis voor Info
        panel : null           // huidig paneel (of null)
    };

    function msgOf(e)
    {
        return (e && e.message) ? e.message : String(e);
    }

    function note(txt)
    {
        try
        {
            S.events.push(txt);
            if (S.events.length > 6)
            {
                S.events.shift();
            }
            log.info("OEMPLUS-INJECT " + txt);
        }
        catch (e) { }
    }

    function fail(where, e)
    {
        try
        {
            S.lastErr = where + ": " + msgOf(e);
            log.warn("OEMPLUS-INJECT " + S.lastErr);
        }
        catch (e2) { }
    }

    function isHome()
    {
        try
        {
            return framework.getCurrentApp() === "system" && framework.getCurrCtxtId() === "HomeScreen";
        }
        catch (e)
        {
            return false;
        }
    }

    function dropBodyClass()
    {
        try
        {
            if (document.body.classList.contains(BODY_CLASS))
            {
                document.body.classList.remove(BODY_CLASS);
            }
            /* v1.4 / P0 (R-cmu F7): B2SbnWatch hangt NIET af van OemplusB2Home -- de B2-watcher zet/halt hem
             * zelf (MainMenuCtrl-oemplusb2.js _b2SbnWatch). Als de watcher wel stuk is EN de klasse toch
             * staat, fail-visible: weg damit de SBN-banner nooit verborgen blijft (fix B2). */
            if (document.body.classList.contains("B2SbnWatch") &&
                !(window.MainMenuCtrl && window.MainMenuCtrl.prototype && window.MainMenuCtrl.prototype._b2WatchSbn))
            {
                document.body.classList.remove("B2SbnWatch");
            }
        }
        catch (e) { }
    }

    /* ------------------------------------------------------------------ P0: submenu's (body.OemplusB2 + B2Sub-*.css) ------------------------------------------------------------------ */

    // true als de huidige (uiaId, ctxtId) protected is (SUBMENU-INVENTARIS-v74 par.5 / DESIGN-SYSTEEM par.9)
    function isProtected(uiaId, ctxtId)
    {
        try
        {
            if (uiaId && PROTECTED_APPS[uiaId])
            {
                return true;
            }
            if (uiaId && ctxtId && PROTECTED_CTXT[uiaId + "/" + ctxtId])
            {
                return true;
            }
        }
        catch (e) { }
        return false;
    }

    function currIds()
    {
        var uia = null, ctxt = null;
        try { uia = framework.getCurrentApp(); } catch (e1) { }
        try { ctxt = framework.getCurrCtxtId(); } catch (e2) { }
        return { uia : uia, ctxt : ctxt };
    }

    // Zet/verwijdert body.OemplusB2: alleen als subOn EN niet protected. Aangeroepen synchroon bij elke
    // contextwissel (hookCallHandle/hookTransition, op basis van de NIEUWE context) en als vangnet in
    // guardTick (binnen GUARD_MS). Logt een OEMPLUS-regel bij elke wissel (geen spam: alleen bij verandering).
    function setSubClass()
    {
        try
        {
            var ids = currIds();
            setSubClassFor(ids.uia, ids.ctxt);
        }
        catch (e)
        {
            fail("setSubClass", e);
        }
    }

    // kern: klasse op basis van een EXPLICIET (uia, ctxt)-paar (binnenkomende context of focusStack).
    // v1.4 (live-flap, LIVE-LOG 2026-11-27): zolang een protected transitie loopt (S.transPending), is de
    // binnenkomende/pending context LEIDEND en mag setSubClass NIET terugzetten op basis van getCurrentApp()
    // (dat is tijdens _callHandleContext nog de OUDE app -> klasse ging 3 ms later weer AAN: weg/gezet/weg).
    function setSubClassFor(uia, ctxt)
    {
        try
        {
            var has = document.body.classList.contains(SUB_CLASS);
            var want = S.subOn && !isProtected(uia, ctxt);
            if (S.transPending)
            {
                want = false;   // protected transitie loopt: klasse blijft weg todat de transitie klaar is
            }
            if (want && !has)
            {
                document.body.classList.add(SUB_CLASS);
                S.lastSub = "aan " + uia + "/" + ctxt;
                note("bewaker: OemplusB2 gezet (" + uia + "/" + ctxt + ")");
            }
            else if (!want && has)
            {
                document.body.classList.remove(SUB_CLASS);
                var prot = isProtected(uia, ctxt);
                S.lastSub = "weg (" + (prot ? "protected " : "uit ") + uia + "/" + ctxt + ")";
                note("bewaker: OemplusB2 weg (" + (prot ? "protected " : "subOn uit ") + uia + "/" + ctxt + ")");
            }
        }
        catch (e)
        {
            fail("setSubClassFor", e);
        }
    }

    // fail-safe helper: bij ELKE fout in een bewaker-wrapper -> klasse eraf (fail-safe = OEM-stijl)
    function failSafeDrop()
    {
        try
        {
            if (document.body.classList.contains(SUB_CLASS))
            {
                document.body.classList.remove(SUB_CLASS);
                S.lastSub = "weg (fail-safe)";
                note("bewaker: OemplusB2 weg (fail-safe na fout)");
            }
        }
        catch (eFS) { }
    }

    // Laadt de B2Sub-*.css in vaste volgorde achteraan <head> (ontbrekend bestand = 404, stil overgeslagen:
    // P1-P4 landen later los; apply controleert de md5 van alle 183 overlaybestanden, dus een 404 = echt absent).
    // De links worden NIET per contextwissel verplaatst (rehang = stylesheet out/in bij elke wissel = kans op
    // een OEM-flits; specificiteit + !important wint sowieso van late lazy-CSS, harnas H3).
    function subCssOn()
    {
        try
        {
            subCssOffLinks();
            S.subLinks = [];
            for (var i = 0; i < PATHS.subCss.length; i++)
            {
                var l = document.createElement("link");
                l.type = "text/css";
                l.rel = "stylesheet";
                l.href = PATHS.subCss[i];
                l.setAttribute("data-oemplusb2sub", String(i));
                document.querySelector("head").appendChild(l);
                S.subLinks.push(l);
            }
        }
        catch (e)
        {
            fail("subCssOn", e);
        }
    }

    function subCssOffLinks()
    {
        try
        {
            for (var i = 0; i < S.subLinks.length; i++)
            {
                var l = S.subLinks[i];
                if (l && l.parentNode)
                {
                    l.parentNode.removeChild(l);
                }
            }
        }
        catch (e) { }
        S.subLinks = [];
    }

    // v1.4 / P0 (R-cmu F1/V1): ECHT synchrone bewaker. _callHandleContext krijgt de NIEUWE context mee als
    // argument (GuiFramework.js: instance.handleContext(contextObj) zet _currentContext), maar zet zelf nog
    // NIET _currentAppUiaId/_currTmpltInstance (dat doet _transitionChange pas, na instantiateTemplate).
    // Daarom: (a) wrapper op _callHandleContext die de klasse op basis van contextObj weghaalt VOORDAT het
    // origineel draait (alleen weghalen, nooit zetten -- zetten gebeurt in _transitionChange/guardTick);
    // (b) wrapper op _transitionChange die VOOR de originele aanroep de klasse weghaalt op basis van
    // focusStack[0].id + de app-instance context en NA de aanroep setSubClass() draait (dan klopt
    // getCurrentApp()). Bij een fout in een wrapper: klasse eraf (fail-safe = OEM) en het origineel wordt
    // ALTIJD aangeroepen. De originele functie zit in een LOKALE var (F9), zodat unhook nooit een vreemde
    // wrapper met null-origineel achterlaat.
    function hookCallHandle()
    {
        try
        {
            if (S.ctxtHooked)
            {
                return;
            }
            if (typeof framework._callHandleContext !== "function")
            {
                note("bewaker: framework._callHandleContext ontbreekt -- alleen vangnet guardTick actief");
                return;
            }
            var orig = framework._callHandleContext;
            S.origCallHandle = orig;
            framework._callHandleContext = function (contextObj)
            {
                try
                {
                    if (contextObj && isProtected(contextObj.uiaId, contextObj.ctxtId))
                    {
                        // v1.4 (H1/live-flap): markeer de protected transitie als LOPEND; de klasse gaat er nu
                        // af (als hij er nog op stond) en setSubClass mag hem NIET terugzetten zolang de
                        // transitie loopt -- ook niet na het origineel (getCurrentApp() is dan nog de oude app).
                        S.transPending = contextObj.uiaId + "/" + contextObj.ctxtId;
                        S.pendingCtxt = S.transPending;
                        if (document.body.classList.contains(SUB_CLASS))
                        {
                            document.body.classList.remove(SUB_CLASS);
                            S.lastSub = "weg (protected " + contextObj.uiaId + "/" + contextObj.ctxtId + ")";
                            note("bewaker: OemplusB2 weg VOORDAT _callHandleContext draait (protected " +
                                 contextObj.uiaId + "/" + contextObj.ctxtId + ")");
                        }
                    }
                    else if (contextObj && !isProtected(contextObj.uiaId, contextObj.ctxtId))
                    {
                        S.pendingCtxt = null;   // niet-protected binnenkomend: geen protected transitie lopend
                        S.transPending = null;
                    }
                }
                catch (eH) { failSafeDrop(); }
                var r = orig.apply(framework, arguments);   // origineel ALTIJD aanroepen
                // v1.4: GEEN setSubClass() hier meer als een protected transitie loopt (H1: dat zette de klasse
                // 3 ms later terug met de OUDE app als bron -> flap weg/gezet/weg). Bij een niet-protected
                // binnenkomst mag de klasse er wel weer op (transPending is dan null).
                try
                {
                    if (!S.transPending)
                    {
                        setSubClass();
                    }
                }
                catch (eH2) { }
                return r;
            };
            framework._callHandleContext.oemplusInjectWrapper = true;
            S.ctxtHooked = true;
        }
        catch (e)
        {
            fail("hookCallHandle", e);
            failSafeDrop();
        }
    }

    function hookTransition()
    {
        try
        {
            if (S.transHooked)
            {
                return;
            }
            if (typeof framework._transitionChange !== "function")
            {
                note("bewaker: framework._transitionChange ontbreekt -- _callHandleContext + guardTick dekken het");
                return;
            }
            var origT = framework._transitionChange;
            S.origTransition = origT;
            framework._transitionChange = function (enabled)
            {
                try
                {
                    if (!enabled)
                    {
                        var nu = null, ctxt = null;
                        if (S.pendingCtxt)
                        {
                            var p = S.pendingCtxt.split("/");
                            nu = p[0]; ctxt = p[1];
                        }
                        else if (framework._focusStack && framework._focusStack.length > 0)
                        {
                            nu = framework._focusStack[0].id;
                            var inst = framework._appInstances[nu];
                            var cobj = inst && inst.getCurrentContext ? inst.getCurrentContext() : null;
                            if (cobj) { ctxt = cobj.ctxtId; }
                        }
                        if (nu && ctxt && isProtected(nu, ctxt) && document.body.classList.contains(SUB_CLASS))
                        {
                            // VOORDAT instantiateTemplate het nieuwe (protected) template bouwt:
                            document.body.classList.remove(SUB_CLASS);
                            S.lastSub = "weg (protected " + nu + "/" + ctxt + ")";
                            note("bewaker: OemplusB2 weg VOORDAT _transitionChange het template bouwt (protected " +
                                 nu + "/" + ctxt + ")");
                        }
                        // v1.4: bij een protected binnenkomst loopt de transitie nu echt: transPending zetten
                        // (ook als pendingCtxt het focusStack-pad nam) zodat setSubClass hem niet terugzet.
                        if (nu && ctxt && isProtected(nu, ctxt))
                        {
                            S.transPending = nu + "/" + ctxt;
                        }
                    }
                }
                catch (eT) { failSafeDrop(); }
                var r = origT.apply(framework, arguments);   // origineel ALTIJD aanroepen
                // v1.4: na de wissel is de transitie KLAAR -> transPending wissen, DAN pas setSubClass()
                // (getCurrentApp() klopt nu). Tijdens een lopende protected transitie bleef de klasse weg.
                try
                {
                    if (!enabled)
                    {
                        S.transPending = null;
                        S.pendingCtxt = null;
                    }
                    setSubClass();
                }
                catch (eT2) { }
                return r;
            };
            framework._transitionChange.oemplusInjectWrapper = true;
            S.transHooked = true;
        }
        catch (e)
        {
            fail("hookTransition", e);
            failSafeDrop();
        }
    }

    function unhookCallHandle()
    {
        try
        {
            if (S.ctxtHooked && S.origCallHandle && framework._callHandleContext &&
                framework._callHandleContext.oemplusInjectWrapper)
            {
                framework._callHandleContext = S.origCallHandle;
            }
        }
        catch (e)
        {
            fail("unhookCallHandle", e);
        }
        S.ctxtHooked = false;
        S.origCallHandle = null;
    }

    function unhookTransition()
    {
        try
        {
            if (S.transHooked && S.origTransition && framework._transitionChange &&
                framework._transitionChange.oemplusInjectWrapper)
            {
                framework._transitionChange = S.origTransition;
            }
        }
        catch (e)
        {
            fail("unhookTransition", e);
        }
        S.transHooked = false;
        S.origTransition = null;
    }

    /* ------------------------------------------------------------------ CSS (M2/M3) ------------------------------------------------------------------ */

    function addCss(key, href)
    {
        try
        {
            if (S.links[key] && S.links[key].parentNode)
            {
                return;
            }
            var l = document.createElement("link");
            l.type = "text/css";
            l.rel = "stylesheet";
            l.href = href;
            document.querySelector("head").appendChild(l);
            S.links[key] = l;
        }
        catch (e)
        {
            fail("addCss " + key, e);
        }
    }

    function removeCss(key)
    {
        try
        {
            var l = S.links[key];
            if (l && l.parentNode)
            {
                l.parentNode.removeChild(l);
            }
            S.links[key] = null;
        }
        catch (e)
        {
            fail("removeCss " + key, e);
        }
    }

    function endsWith(h, tail)
    {
        return h.length >= tail.length && h.substr(h.length - tail.length) === tail;
    }

    // originele MainMenuCtrl.css-link(s) uit de DOM halen (positie onthouden) / op dezelfde plek terugzetten
    function takeOrgCss()
    {
        var links = document.querySelectorAll("link");
        for (var i = 0; i < links.length; i++)
        {
            var h = links[i].getAttribute("href") || "";
            if (endsWith(h, PATHS.mmCssOrg) && links[i].parentNode)
            {
                S.removedOrg.push({ node : links[i], parent : links[i].parentNode, next : links[i].nextSibling });
                links[i].parentNode.removeChild(links[i]);
            }
        }
    }

    function restoreOrgCss()
    {
        // omgekeerde volgorde: 'next' van een eerder weggehaalde link kan zelf een weggehaalde link zijn
        for (var i = S.removedOrg.length - 1; i >= 0; i--)
        {
            var r = S.removedOrg[i];
            try
            {
                if (!r.node.parentNode)
                {
                    if (r.next && r.next.parentNode === r.parent)
                    {
                        r.parent.insertBefore(r.node, r.next);
                    }
                    else
                    {
                        r.parent.appendChild(r.node);
                    }
                }
            }
            catch (e)
            {
                fail("originele CSS terugzetten", e);
                try { document.querySelector("head").appendChild(r.node); } catch (e2) { }
            }
        }
        S.removedOrg = [];
    }

    function cssB2On()
    {
        if (S.cssOn)
        {
            return;
        }
        try
        {
            addCss("mmCss", PATHS.mmCss);
            addCss("sbCss", PATHS.sbCss);
            addCss("sbnCss", PATHS.sbnCss);   /* OEMPLUS-INJECT v1.2: B2-stijl voor de SBN-banner */
            takeOrgCss();
            S.cssOn = true;
        }
        catch (e)
        {
            fail("cssB2On", e);
        }
    }

    function cssB2Off()
    {
        try
        {
            restoreOrgCss();
            removeCss("mmCss");
            removeCss("sbCss");
            removeCss("sbnCss");
        }
        catch (e)
        {
            fail("cssB2Off", e);
        }
        S.cssOn = false;
    }

    /* ------------------------------------------------------------------ systemApp-haken ------------------------------------------------------------------ */

    // systemApp: _oemplusB2Note (identiek aan B2 systemApp.js) + omwikkelen van de gebonden handlers
    function b2Note(name, msg)
    {
        try
        {
            var payload = (msg && msg.params) ? msg.params.payload : null;
            if (!this._oemplusB2Data)
            {
                this._oemplusB2Data = {};
            }
            this._oemplusB2Data[name] = payload;
            if (this._currentContext && this._currentContext.ctxtId === "HomeScreen" && this._currentContextTemplate &&
                this._currentContextTemplate.mainMenuControl && typeof this._currentContextTemplate.mainMenuControl.oemplusB2Update === "function")
            {
                this._currentContextTemplate.mainMenuControl.oemplusB2Update(name, payload);
            }
        }
        catch (e)
        {
            try { log.warn("OEMPLUS-B2 _oemplusB2Note(" + name + "): " + (e && e.message ? e.message : e)); } catch (e2) { }
        }
    }

    function makeWrapper(sys, name, orig)
    {
        var w = function (msg)
        {
            try
            {
                if (!isHome())
                {
                    dropBodyClass();     // M4
                }
                if (S.on && typeof sys._oemplusB2Note === "function")
                {
                    sys._oemplusB2Note(name, msg);
                }
            }
            catch (e) { }
            return orig(msg);
        };
        w.oemplusInjectWrapper = true;
        return w;
    }

    function hookSystem()
    {
        var n = 0;
        try
        {
            var sys = framework.getAppInstance("system");
            if (!sys || !sys._messageTable)
            {
                fail("hookSystem", "systemApp niet gevonden");
                return 0;
            }
            if (typeof sys._oemplusB2Note !== "function")
            {
                sys._oemplusB2Note = b2Note;   // eigen instantie-eigenschap; prototype blijft ongemoeid
            }
            for (var i = 0; i < NOTE_MSGS.length; i++)
            {
                var name = NOTE_MSGS[i];
                var cur = sys._messageTable[name];
                if (typeof cur === "function" && !cur.oemplusInjectWrapper)
                {
                    S.origHandlers[name] = cur;
                    sys._messageTable[name] = makeWrapper(sys, name, cur);
                }
                if (sys._messageTable[name] && sys._messageTable[name].oemplusInjectWrapper)
                {
                    n++;
                }
            }
        }
        catch (e)
        {
            fail("hookSystem", e);
        }
        return n;
    }

    function unhookSystem()
    {
        try
        {
            var sys = framework.getAppInstance("system");
            if (!sys || !sys._messageTable)
            {
                return;
            }
            for (var name in S.origHandlers)
            {
                if (S.origHandlers.hasOwnProperty(name))
                {
                    sys._messageTable[name] = S.origHandlers[name];
                }
            }
            S.origHandlers = {};
            // _oemplusB2Note/_oemplusB2Data mogen blijven (ongebruikt zonder wrappers)
        }
        catch (e)
        {
            fail("unhookSystem", e);
        }
    }

    function hookCount()
    {
        var n = 0;
        try
        {
            var sys = framework.getAppInstance("system");
            for (var i = 0; i < NOTE_MSGS.length; i++)
            {
                if (sys && sys._messageTable[NOTE_MSGS[i]] && sys._messageTable[NOTE_MSGS[i]].oemplusInjectWrapper)
                {
                    n++;
                }
            }
        }
        catch (e) { }
        return n;
    }

    /* ------------------------------------------------------------------ SBN-filter (v1.2) ------------------------------------------------------------------
     * framework.common is een instantie (GuiFramework.js:2334: this.common = new Common()), dus prototype-patchen
     * werkt niet; net als bij systemApp._messageTable zetten we eigen wrappers als instantie-eigenschappen.
     * Onderdrukt wordt ALLEEN de navigatie-straatnaam-SBN: sbnStyle Style05 met type navigationNear/navigationFar
     * (emnaviApp.js:619-632, 729-762 -- de enige Style05-gebruiker) of het emnavi turn-by-turn id. Alles andere
     * (BT, audio, fouten, veiligheid) gaat ongewijzigd door. */

    function sbnIsNavSbn(uiaId, sbnId, type, properties)
    {
        try
        {
            if (SBN_NAV_IDS[(uiaId || "") + (sbnId || "")])
            {
                return true;
            }
            if (properties && properties.sbnStyle === SBN_NAV_STYLE && type && SBN_NAV_TYPES[type])
            {
                return true;
            }
        }
        catch (e) { }
        return false;
    }

    function makeSbnWrapper(name, orig)
    {
        var w = function (uiaId, sbnId, type, properties)
        {
            try
            {
                if (S.on && name !== "endStateSbn" && name !== "cancelTimedSbn" && sbnIsNavSbn(uiaId, sbnId, type, properties))
                {
                    S.sbnDropped++;
                    note("SBN onderdrukt (navigatie-straatnaam): " + uiaId + "/" + sbnId + " type=" + type);
                    return;   // geslikt: Common ziet de melding niet
                }
            }
            catch (e) { }
            return orig.apply(this, arguments);
        };
        w.oemplusInjectSbnWrapper = true;
        return w;
    }

    function hookSbn()
    {
        var n = 0;
        try
        {
            var c = framework.common;
            if (!c)
            {
                fail("hookSbn", "framework.common niet gevonden");
                return 0;
            }
            for (var i = 0; i < SBN_APIS.length; i++)
            {
                var name = SBN_APIS[i];
                var cur = c[name];
                if (typeof cur === "function" && !cur.oemplusInjectSbnWrapper)
                {
                    S.origSbnApis[name] = cur;
                    c[name] = makeSbnWrapper(name, cur);   // instantie-eigenschap; prototype ongemoeid
                }
                if (c[name] && c[name].oemplusInjectSbnWrapper)
                {
                    n++;
                }
            }
            if (n === SBN_APIS.length)
            {
                S.sbnHooked = true;
            }
        }
        catch (e)
        {
            fail("hookSbn", e);
        }
        return n;
    }

    function unhookSbn()
    {
        try
        {
            var c = framework.common;
            if (!c)
            {
                return;
            }
            for (var name in S.origSbnApis)
            {
                if (S.origSbnApis.hasOwnProperty(name))
                {
                    /* fix B10: delete i.p.v. terugzetten als instantie-eigenschap, zodat Common exact is
                     * zoals voor de inject (de originele functie was een prototype-functie). */
                    if (c.hasOwnProperty(name))
                    {
                        try { delete c[name]; } catch (eD) { c[name] = S.origSbnApis[name]; }
                    }
                    else
                    {
                        c[name] = S.origSbnApis[name];
                    }
                }
            }
            S.origSbnApis = {};
            S.sbnHooked = false;
        }
        catch (e)
        {
            fail("unhookSbn", e);
        }
    }

    function sbnHookCount()
    {
        var n = 0;
        try
        {
            var c = framework.common;
            for (var i = 0; i < SBN_APIS.length; i++)
            {
                if (c && c[SBN_APIS[i]] && c[SBN_APIS[i]].oemplusInjectSbnWrapper)
                {
                    n++;
                }
            }
        }
        catch (e) { }
        return n;
    }

    // Bij 'B2 aan': een eventueel nu getoonde straatnaam-SBN direct beeindigen (endStateSbn op de originele API).
    function endNavSbnNow()
    {
        try
        {
            var c = framework.common;
            if (!c)
            {
                return;
            }
            for (var i = 0; i < SBN_DROPPED.length; i++)
            {
                var id = SBN_DROPPED[i];
                if (c._displayedSbnId === ("emnavi" + id) || (c._sbnQueue && c._sbnQueue.indexOf("emnavi" + id) !== -1))
                {
                    var orig = S.origSbnApis["endStateSbn"] || (S.sbnHooked ? null : c.endStateSbn);
                    if (orig)
                    {
                        orig.call(c, "emnavi", id, "navigationNear");
                        note("getoonde nav-SBN beeindigd: " + id);
                    }
                }
            }
        }
        catch (e)
        {
            fail("endNavSbnNow", e);
        }
    }

    /* ------------------------------------------------------------------ bewaker (M1/M4) ------------------------------------------------------------------ */

    // aan: bewaakte B2-constructor. Uit maar B2-CSS nog actief (fout terwijl een B2-instantie leefde): ook de bewaakte
    // constructor, die dan eerst de CSS terugzet en het origineel bouwt. Anders: het origineel.
    function expectedCtor()
    {
        if (S.wrapper && (S.on || S.cssOn))
        {
            return S.wrapper;
        }
        return S.origCtor;
    }

    function guardTick()
    {
        try
        {
            var want = expectedCtor();
            if (want && window.MainMenuCtrl !== want)
            {
                window.MainMenuCtrl = want;
                note("bewaker: MainMenuCtrl teruggezet naar " + (want === S.origCtor ? "origineel" : "B2 (bewaakt)"));
            }
            if (!isHome())
            {
                dropBodyClass();
            }
            /* v1.4 (live-flap): setSubClass als vangnet, MAAR niet terwijl een protected transitie loopt
             * (transPending) -- dan is de pending/binnenkomende context leidend, niet getCurrentApp(). */
            if (!S.transPending)
            {
                setSubClass();      // OEMPLUS-INJECT v1.4 / P0: vangnet voor de submenu-bewaker
            }
            /* v1.4 / P5-eco: TPMS-divs in de huidige ecoStatusCtrl (bij elke contextwissel; de
             * ecoStatusCtrl wordt per ControlStatus-context opnieuw gebouwd) */
            if (S.tpmsHooked && S.subOn)
            {
                tpmsEnsureDivs();
            }
            /* v1.5 (v1.4-open punt): rij 3 eco (TPMS/accu-bubbels) verbergen zolang de UMP open staat.
             * Read-only: we lezen _umpPanelStatus van de levende eco-ctrl en zetten/verwijderen alleen
             * onze eigen marker-klasse B2UmpOpen op de template-div (B2Sub-50-eco.css doet de rest). */
            try
            {
                var ecoU = framework.getAppInstance && framework.getAppInstance("ecoenergy");
                var tU = ecoU && ecoU._currentContextTemplate;
                if (tU && tU.divElt)
                {
                    var up = false;
                    for (var kk in tU)
                    {
                        if (tU[kk] && typeof tU[kk].toggleUmpPanel === "function" && tU[kk]._umpPanelStatus === true)
                        {
                            up = true; break;
                        }
                    }
                    if (up) { tU.divElt.classList.add("B2UmpOpen"); }
                    else { tU.divElt.classList.remove("B2UmpOpen"); }
                }
            }
            catch (eUmp) { }
            if (!S.tpmsHooked && S.subOn && framework._appInstances && framework._appInstances.warnguide)
            {
                /* v1.4 / P5: warnguide laadt lazy (bij eerste msg/ctxt) -> hook pas als de instantie er is */
                tpmsHook();
            }
        }
        catch (e) { }
    }

    function startGuard()
    {
        try
        {
            if (!S.guardTimer)
            {
                S.guardTimer = setInterval(guardTick, GUARD_MS);
            }
        }
        catch (e)
        {
            fail("startGuard", e);
        }
    }

    /* ------------------------------------------------------------------ laden (M1/M3) ------------------------------------------------------------------ */

    function isB2Ctor(f)
    {
        return typeof f === "function" && f !== S.origCtor && f !== S.wrapper && f.prototype && typeof f.prototype._b2Start === "function";
    }

    function unhookReg()
    {
        try
        {
            if (S.regHooked && S.origReg)
            {
                framework.registerCtrlLoaded = S.origReg;
            }
        }
        catch (e) { fail("registerCtrlLoaded terugzetten", e); }
        S.regHooked = false;
        S.expectReg = false;
    }

    // Wrapper op framework.registerCtrlLoaded: slikt alleen de ene aanroep "MainMenuCtrl" van het B2-bestand (ook als die te laat
    // komt). Al het andere gaat ongewijzigd door. Wordt verwijderd zodra die aanroep gezien is of het bestand aantoonbaar faalt.
    function hookReg()
    {
        if (S.regHooked)
        {
            S.expectReg = true;
            return;
        }
        S.origReg = framework.registerCtrlLoaded;
        S.expectReg = true;
        S.regHooked = true;
        framework.registerCtrlLoaded = function (controlName)
        {
            if (controlName === "MainMenuCtrl" && S.expectReg)
            {
                var now = window.MainMenuCtrl;
                try
                {
                    if (isB2Ctor(now))
                    {
                        S.b2Ctor = now;
                    }
                    window.MainMenuCtrl = expectedCtor();      // nooit op de kale B2-constructor laten staan
                    note("registerCtrlLoaded(MainMenuCtrl) van B2-bestand geslikt" + (S.loading ? "" : " (te laat binnen; geen wijziging)"));
                }
                catch (e) { fail("registratie B2", e); }
                unhookReg();
                if (S.onReg)
                {
                    var cb = S.onReg;
                    S.onReg = null;
                    setTimeout(cb, 0);
                }
                return;
            }
            return S.origReg.apply(framework, arguments);
        };
    }

    function loadB2Ctor(done)
    {
        if (S.b2Ctor)
        {
            done(true);
            return;
        }
        if (S.loading)
        {
            return;
        }
        var finished = false;
        var timer = null;
        var script = null;

        function finish(ok, why)
        {
            if (finished)
            {
                return;
            }
            finished = true;
            S.loading = false;
            S.onReg = null;
            try { clearTimeout(timer); } catch (e0) { }
            if (ok && !S.b2Ctor)
            {
                ok = false;
                why = "B2-constructor niet herkend";
            }
            try
            {
                if (window.MainMenuCtrl !== expectedCtor())
                {
                    window.MainMenuCtrl = expectedCtor();
                }
            }
            catch (e1) { }
            if (!ok)
            {
                fail("laden " + PATHS.mmJs, why);
            }
            try { done(ok); } catch (e4) { fail("done", e4); }
        }

        try
        {
            S.loading = true;
            hookReg();
            S.onReg = function () { finish(true, ""); };
            script = document.createElement("script");
            script.type = "text/javascript";
            script.src = PATHS.mmJs;
            // versnellers; het resultaat hangt er niet van af (M3)
            script.onerror = function ()
            {
                unhookReg();                                  // bestand komt niet: geen late aanroep meer te verwachten
                finish(false, "bestand niet gevonden/leesbaar");
            };
            script.onload = function ()
            {
                // de registratie gebeurt synchroon tijdens het uitvoeren, voor onload; zonder registratie = fout in het bestand
                if (!S.b2Ctor)
                {
                    unhookReg();                              // script is al uitgevoerd: er komt geen registratie meer
                    finish(false, "bestand geladen maar niet geregistreerd (fout in het script?)");
                }
            };
            timer = setTimeout(function ()
            {
                try { if (script && script.parentNode) { script.parentNode.removeChild(script); } } catch (e5) { }
                finish(false, "timeout " + LOAD_TIMEOUT_MS + " ms");
            }, LOAD_TIMEOUT_MS);
            document.querySelector("head").appendChild(script);
        }
        catch (e)
        {
            finish(false, msgOf(e));
        }
    }

    /* ------------------------------------------------------------------ bewaakte constructor (H2) ------------------------------------------------------------------ */

    function onB2Error(where, e)
    {
        S.b2Errors++;
        fail("B2 " + where, e);
        dropBodyClass();
        if (S.on)
        {
            revert(true);     // volgende Home = origineel; CSS pas weg als deze B2-instantie opgeruimd is
            note("B2 uit na fout in " + where);
        }
    }

    function guardMethods(o)
    {
        for (var i = 0; i < GUARD_METHODS.length; i++)
        {
            (function (name)
            {
                var fn = o[name];
                if (typeof fn !== "function")
                {
                    return;
                }
                o[name] = function ()
                {
                    var r;
                    try
                    {
                        r = fn.apply(o, arguments);
                    }
                    catch (e)
                    {
                        onB2Error(name, e);
                        r = (name === "getContextCapture") ? {} : ((name === "handleControllerEvent") ? "ignored" : undefined);
                    }
                    if (name === "cleanUp")
                    {
                        S.liveB2 = Math.max(0, S.liveB2 - 1);
                        if (!S.on && S.liveB2 === 0 && S.cssOn)
                        {
                            cssB2Off();
                        }
                    }
                    else if (name === "startTransitionFrom")
                    {
                        dropBodyClass();
                    }
                    return r;
                };
            })(GUARD_METHODS[i]);
        }
    }

    function guardedCtor(uiaId, parentDiv, controlId, properties)
    {
        if (!S.on || !S.b2Ctor)
        {
            if (S.cssOn)
            {
                cssB2Off();
            }
            return new S.origCtor(uiaId, parentDiv, controlId, properties);
        }
        var before = 0;
        var bodyAdds = [];
        var body = document.body;
        var hadOwnAdd = false;
        try { before = parentDiv ? parentDiv.childNodes.length : 0; } catch (e0) { }
        cssB2On();          // M2: pas nu, als het OEM-home niet meer in beeld hoeft te blijven
        try
        {
            // body-luisteraars van een half gebouwde instantie kunnen worden opgeruimd
            hadOwnAdd = body.hasOwnProperty("addEventListener");
            var protoAdd = body.addEventListener;
            body.addEventListener = function (t, f, c)
            {
                bodyAdds.push([t, f, c]);
                return protoAdd.call(body, t, f, c);
            };
            var o = new S.b2Ctor(uiaId, parentDiv, controlId, properties);
            if (!hadOwnAdd) { try { delete body.addEventListener; } catch (eD) { } }
            guardMethods(o);
            S.liveB2++;
            return o;
        }
        catch (e)
        {
            if (!hadOwnAdd) { try { delete body.addEventListener; } catch (eD2) { } }
            S.b2Errors++;
            fail("B2-constructor", e);
            try
            {
                while (parentDiv && parentDiv.childNodes.length > before)
                {
                    parentDiv.removeChild(parentDiv.lastChild);
                }
            }
            catch (e2) { }
            for (var i = 0; i < bodyAdds.length; i++)
            {
                try { body.removeEventListener(bodyAdds[i][0], bodyAdds[i][1], bodyAdds[i][2]); } catch (e3) { }
            }
            revert(false);       // constructor, CSS, handlers, body-klasse terug
            note("B2-constructor faalde -> origineel home gebouwd");
            return new S.origCtor(uiaId, parentDiv, controlId, properties);
        }
    }

    function makeGuarded()
    {
        if (!S.wrapper)
        {
            var w = function (uiaId, parentDiv, controlId, properties)
            {
                return guardedCtor(uiaId, parentDiv, controlId, properties);
            };
            w.prototype = S.b2Ctor.prototype;     // MainMenuCtrl.prototype.* blijft naar B2 wijzen
            w.oemplusGuarded = true;
            S.wrapper = w;
        }
        return S.wrapper;
    }

    /* ------------------------------------------------------------------ punt 8: Terminal-item in Applicaties (runtime-patch, RAM-only) ----
     * Live-bewezen door een andere agent via bind-mount + GUI-herlaad (zie mzd-toolkit: toolkit-v74/terminal/):
     * item 'oemplusterminal' in _masterApplicationDataList + _applicationsCtxtWiseAppNames["Applications"] en een
     * _menuItemSelectCallback die ws://127.0.0.1:9997/ opent en NIETS naar MMUI stuurt. Wij mogen systemApp.js
     * NIET herladen -> we patchen de AL GELADEN systemApp-instantie bij "B2 aan" (idempotent, ook als een gepatchte
     * systemApp.js al gemount is) en rollen netjes terug bij "B2 uit". Fail-safe: elke fout -> niets doen.
     * Het selectCallback zit als .bind(this) in de List2Ctrl-properties (systemApp.js r.141) en wordt aangeroepen
     * via this.properties.selectCallback (List2Ctrl.js r.5567) -> we wrappen de INSTANTIE-functie
     * _menuItemSelectCallback NIET (de bound kopie in properties blijft dan origineel); in plaats daarvan wrappen we
     * de properties.selectCallback van de Applications-List2Ctrl (en VehicleStatusMonitor kan het item niet tonen).
     * Als die al een oemplus-wrapper heeft, niet nogmaals. */
    var TERM_APP = "oemplusterminal";
    var TERM_WS = "ws://127.0.0.1:9997/";

    function termItemPresent(sys)
    {
        try
        {
            var items = sys._masterApplicationDataList && sys._masterApplicationDataList.items;
            if (!items)
            {
                return false;
            }
            for (var i = 0; i < items.length; i++)
            {
                if (items[i] && items[i].appData && items[i].appData.appName === TERM_APP)
                {
                    return true;
                }
            }
        }
        catch (e) { }
        return false;
    }

    function termOpen()
    {
        try
        {
            var ws = new WebSocket(TERM_WS);
            setTimeout(function () { try { ws.close(); } catch (eC) { } }, 3000);
            note("Terminal: WebSocket geopend " + TERM_WS);
        }
        catch (e)
        {
            fail("Terminal ws", e);
        }
    }

    // wrap de selectCallback in de List2Ctrl-properties van een context-template (Applications)
    function termWrapListCallback(tmpl)
    {
        try
        {
            var l2 = tmpl && tmpl.list2Ctrl;
            var props = l2 && l2.properties;
            if (!props || typeof props.selectCallback !== "function" || props.selectCallback.oemplusTermWrapper)
            {
                return false;
            }
            var orig = props.selectCallback;
            var w = function (listCtrlObj, appData, params)
            {
                try
                {
                    if (appData && appData.appName === TERM_APP)
                    {
                        termOpen();     // NIETS naar MMUI
                        return true;
                    }
                }
                catch (eT) { fail("Terminal select", eT); }
                return orig.call(this, listCtrlObj, appData, params);
            };
            w.oemplusTermWrapper = true;
            w.oemplusTermOrig = orig;
            props.selectCallback = w;
            return true;
        }
        catch (e) { fail("termWrapListCallback", e); }
        return false;
    }

    function termUnwrapListCallback(tmpl)
    {
        try
        {
            var l2 = tmpl && tmpl.list2Ctrl;
            var props = l2 && l2.properties;
            if (props && typeof props.selectCallback === "function" && props.selectCallback.oemplusTermWrapper)
            {
                // de originele zit in de closure; bewaar hem bij het wrappen
                props.selectCallback = props.selectCallback.oemplusTermOrig || props.selectCallback;
            }
        }
        catch (e) { }
    }

    function termHook()
    {
        try
        {
            if (S.termHooked)
            {
                return true;
            }
            var sys = framework.getAppInstance("system");
            if (!sys || !sys._masterApplicationDataList || !sys._applicationsCtxtWiseAppNames)
            {
                note("Terminal: systemApp niet gevonden -> overslaan");
                return false;
            }
            // 1) item in _masterApplicationDataList (idempotent)
            if (!termItemPresent(sys))
            {
                S.termItem = { appData : { appName : TERM_APP, isVisible : true, audioSourceId : "None", mmuiEvent : "OemplusTerminal" },
                               text1 : "Terminal", disabled : false, itemStyle : "style01", hasCaret : false };
                sys._masterApplicationDataList.items.push(S.termItem);
                sys._masterApplicationDataList.itemCount = sys._masterApplicationDataList.items.length;
            }
            else
            {
                S.termItem = null;   // al aanwezig (bv. gepatchte systemApp.js gemount) -> niet nogmaals toevoegen
            }
            // 2) appName in beide "Applications"-varianten van _applicationsCtxtWiseAppNames (idempotent)
            var cwn = sys._applicationsCtxtWiseAppNames;
            for (var ctxt in cwn)
            {
                if (cwn.hasOwnProperty(ctxt) && ctxt === "Applications" && Object.prototype.toString.call(cwn[ctxt]) === "[object Array]")
                {
                    if (cwn[ctxt].indexOf(TERM_APP) === -1)
                    {
                        cwn[ctxt].push(TERM_APP);
                        S.termNames.push(TERM_APP);
                        S.termCtxts.push(ctxt);
                    }
                }
            }
            // 3) selectCallback wrappen op de HUIDIGE Applications-template (als die open staat) + op de
            //    contextTable-definitie (zodat een volgende open het ook heeft): beide zijn .bind-kopieen,
            //    dus we wrappen de properties van de levende list2Ctrl  en  de contextTable-entry.
            var wrapped = 0;
            try
            {
                var t = sys._currentContextTemplate;
                if (t && framework.getCurrCtxtId() === "Applications")
                {
                    if (termWrapListCallback(t))
                    {
                        wrapped++;
                    }
                }
            }
            catch (eC) { }
            try
            {
                var entry = sys._contextTable && sys._contextTable["Applications"];
                var props = entry && entry.controlProperties && entry.controlProperties.List2Ctrl;
                if (props && typeof props.selectCallback === "function" && !props.selectCallback.oemplusTermWrapper)
                {
                    var orig = props.selectCallback;
                    var w = function (listCtrlObj, appData, params)
                    {
                        try
                        {
                            if (appData && appData.appName === TERM_APP)
                            {
                                termOpen();
                                return true;
                            }
                        }
                        catch (eT) { fail("Terminal select (ctxtTable)", eT); }
                        return orig.call(this, listCtrlObj, appData, params);
                    };
                    w.oemplusTermWrapper = true;
                    w.oemplusTermOrig = orig;
                    props.selectCallback = w;
                    S.termOrigCb = orig;
                    wrapped++;
                }
            }
            catch (eT2) { }
            // ook de levende list2Ctrl wrappen met orig-bewaring
            try
            {
                var t2 = sys._currentContextTemplate;
                if (t2 && t2.list2Ctrl && t2.list2Ctrl.properties &&
                    typeof t2.list2Ctrl.properties.selectCallback === "function" &&
                    !t2.list2Ctrl.properties.selectCallback.oemplusTermWrapper)
                {
                    var o2 = t2.list2Ctrl.properties.selectCallback;
                    var w2 = function (listCtrlObj, appData, params)
                    {
                        try
                        {
                            if (appData && appData.appName === TERM_APP)
                            {
                                termOpen();
                                return true;
                            }
                        }
                        catch (eT3) { fail("Terminal select (live)", eT3); }
                        return o2.call(this, listCtrlObj, appData, params);
                    };
                    w2.oemplusTermWrapper = true;
                    w2.oemplusTermOrig = o2;
                    t2.list2Ctrl.properties.selectCallback = w2;
                    wrapped++;
                }
            }
            catch (eT4) { }
            S.termHooked = true;
            note("Terminal-item gepatcht (item " + (S.termItem ? "toegevoegd" : "al aanwezig") + ", appNames " + S.termNames.length + ", callbacks " + wrapped + ")");
            return true;
        }
        catch (e)
        {
            fail("termHook", e);
            return false;
        }
    }

    function termUnhook()
    {
        try
        {
            var sys = framework.getAppInstance("system");
            if (sys)
            {
                // item eraf (alleen als WIJ hem toevoegden)
                if (S.termItem && sys._masterApplicationDataList && sys._masterApplicationDataList.items)
                {
                    var items = sys._masterApplicationDataList.items;
                    for (var i = items.length - 1; i >= 0; i--)
                    {
                        if (items[i] === S.termItem || (items[i] && items[i].appData && items[i].appData.appName === TERM_APP && S.termItem))
                        {
                            items.splice(i, 1);
                        }
                    }
                    sys._masterApplicationDataList.itemCount = items.length;
                }
                // appNames eraf
                var cwn = sys._applicationsCtxtWiseAppNames;
                if (cwn)
                {
                    for (var c = 0; c < S.termCtxts.length; c++)
                    {
                        var arr = cwn[S.termCtxts[c]];
                        if (Object.prototype.toString.call(arr) === "[object Array]")
                        {
                            for (var k = arr.length - 1; k >= 0; k--)
                            {
                                if (arr[k] === TERM_APP)
                                {
                                    arr.splice(k, 1);
                                }
                            }
                        }
                    }
                }
                // callbacks unwrappen (contextTable + levende template)
                try
                {
                    var entry = sys._contextTable && sys._contextTable["Applications"];
                    var props = entry && entry.controlProperties && entry.controlProperties.List2Ctrl;
                    if (props && typeof props.selectCallback === "function" && props.selectCallback.oemplusTermWrapper)
                    {
                        props.selectCallback = props.selectCallback.oemplusTermOrig || props.selectCallback;
                    }
                }
                catch (e1) { }
                termUnwrapListCallback(sys._currentContextTemplate);
            }
        }
        catch (e) { fail("termUnhook", e); }
        S.termHooked = false;
        S.termOrigCb = null;
        S.termItem = null;
        S.termNames = [];
        S.termCtxts = [];
    }

    /* ------------------------------------------------------------------ P5-eco: TPMS (indirect, read-only uit warnguide) ----
     * Bron: docs/designs/TPMS-ONDERZOEK-2026-11-27.md (commit 441cbdef). Deze Mazda 3 BM heeft indirect
     * TPMS: geen drukwaarden/per-wiel, alleen warnguide-meldingen via MMUI -> GUI. We lezen ALLEEN:
     *   framework._appInstances.warnguide._cachedVWMValues (array met warning_no's) EN ._warningCount
     *   (samen lezen: _cachedVWMValues wordt alleen bijgewerkt als Warning_count truthy is) en hangen
     *   een read-only wrapper op warnguideApp.prototype._WarningStatusMsgHandler (origineel altijd
     *   aangeroepen). warnguide is protected (klasse OemplusB2 staat er nooit), maar de APP-INSTANTIE
     *   leeft wel (geladen bij boot) -> lezen mag. Mapping: 21/22/86 = "Bandendruk laag" (amber, pulserend),
     *   41/42 = "TPMS-storing" (amber, niet pulserend), anders "Banden OK" (rood-accent). Geen
     *   warnguide-app of nooit data -> verborgen (ONTWERP-B B6, gedocumenteerd). Alles try/catch +
     *   idempotent; bij "B2 uit" netjes terug. */
    var TPMS_LOW = { 21 : true, 22 : true, 86 : true };   // Check_Tyre_Pressure / Low_Tire_Air_Pressure
    var TPMS_FAULT = { 41 : true, 42 : true };            // TPMS_Inspection_Required

    function tpmsReadState()
    {
        // read-only; geeft "none" als er nooit data was (warnguide-app/laad-bericht afwezig)
        try
        {
            var wg = framework._appInstances && framework._appInstances.warnguide;
            if (!wg)
            {
                return "none";
            }
            var cnt = wg._warningCount;
            var vals = wg._cachedVWMValues;
            if (typeof cnt !== "number" || !vals)
            {
                return "none";   // nooit een WarningStatus-bericht gehad
            }
            if (cnt > 0 && Object.prototype.toString.call(vals) === "[object Array]")
            {
                for (var i = 0; i < vals.length; i++)
                {
                    var v = vals[i];
                    if (TPMS_LOW[v])
                    {
                        return "low";
                    }
                    if (TPMS_FAULT[v])
                    {
                        return "fault";
                    }
                }
            }
            return "ok";
        }
        catch (e)
        {
            fail("tpmsReadState", e);
            return "none";
        }
    }

    function tpmsApply()
    {
        // zet de klasse op beide TPMS-divs volgens S.tpmsState (alleen als B2 aan + eco-scherm actief)
        try
        {
            var st = S.tpmsState;
            var hide = (st === "none");
            for (var i = 0; i < S.tpmsDivs.length; i++)
            {
                var d = S.tpmsDivs[i];
                if (!d || !d.parentNode)
                {
                    continue;
                }
                var side = (i === 0) ? "L" : "R";
                var cls = "B2EcoTpms" + side;
                if (hide)
                {
                    cls += " B2EcoTpmsHidden";
                }
                else if (st === "ok")
                {
                    cls += " B2EcoTpms" + side + "_Ok";
                }
                else if (st === "low")
                {
                    cls += " B2EcoTpms" + side + (S.tpmsPulseOn ? "_LowPulse" : "_Low");
                }
                else if (st === "fault")
                {
                    cls += " B2EcoTpms" + side + "_Fault";
                }
                d.className = cls;
            }
        }
        catch (e) { fail("tpmsApply", e); }
    }

    function tpmsSet(state)
    {
        try
        {
            if (state !== "none")
            {
                S.tpmsSeen = true;
            }
            S.tpmsState = state;
            tpmsApply();
            // puls alleen bij "low"
            try
            {
                if (S.tpmsPulseTimer)
                {
                    clearInterval(S.tpmsPulseTimer);
                    S.tpmsPulseTimer = null;
                }
            }
            catch (e0) { }
            if (state === "low" && S.subOn)
            {
                S.tpmsPulseTimer = setInterval(function ()
                {
                    try
                    {
                        S.tpmsPulseOn = !S.tpmsPulseOn;
                        tpmsApply();
                    }
                    catch (e) { }
                }, 700);
            }
        }
        catch (e) { fail("tpmsSet", e); }
    }

    function tpmsEnsureDivs()
    {
        // maak de 2 TPMS-divs in de HUIDIGE ecoStatusCtrl (als die er is); idempotent per instantie
        try
        {
            if (!S.subOn || !document.body.classList.contains(SUB_CLASS))
            {
                return;
            }
            var eco = framework.getAppInstance && framework.getAppInstance("ecoenergy");
            var t = eco && eco._currentContextTemplate;
            var c = t && t.ecoStatusCtrl;
            if (!c || !c.controlDiv)
            {
                return;
            }
            if (c._oemplusTpmsDivs)
            {
                S.tpmsDivs = c._oemplusTpmsDivs;
                tpmsApply();
                return;
            }
            var dL = document.createElement("div");
            dL.className = "B2EcoTpmsL B2EcoTpmsHidden";
            var dR = document.createElement("div");
            dR.className = "B2EcoTpmsR B2EcoTpmsHidden";
            c.controlDiv.appendChild(dL);
            c.controlDiv.appendChild(dR);
            c._oemplusTpmsDivs = [dL, dR];
            S.tpmsDivs = c._oemplusTpmsDivs;
            tpmsApply();
        }
        catch (e) { fail("tpmsEnsureDivs", e); }
    }

    function tpmsHook()
    {
        // idempotent; faalt stil (fail-safe = OEM, TPMS blijft verborgen/OK-default)
        try
        {
            if (S.tpmsHooked)
            {
                return true;
            }
            // 1) read-only wrapper op de GEBONDEN handler in warnguide._messageTable["WarningStatus"]
            //    (net als systemApp: de tabel entries zijn .bind(this) in de constructor, dus een
            //    prototype-wijziging werkt niet; we wrappen de instantie-entry, origineel altijd eerst)
            var wg = null;
            try { wg = framework._appInstances && framework._appInstances.warnguide; } catch (eG) { }
            if (wg && wg._messageTable && typeof wg._messageTable["WarningStatus"] === "function" &&
                !wg._messageTable["WarningStatus"].oemplusTpmsWrapper)
            {
                var orig = wg._messageTable["WarningStatus"];
                var w = function (msg)
                {
                    var r = orig.apply(this, arguments);   // origineel ALTIJD eerst
                    try { tpmsSet(tpmsReadState()); } catch (eW) { }
                    return r;
                };
                w.oemplusTpmsWrapper = true;
                wg._messageTable["WarningStatus"] = w;
                S.tpmsOrigHandler = orig;
                S.tpmsOrigTable = wg._messageTable;
            }
            else if (window.warnguideApp && warnguideApp.prototype &&
                     typeof warnguideApp.prototype._WarningStatusMsgHandler === "function" &&
                     !warnguideApp.prototype._WarningStatusMsgHandler.oemplusTpmsWrapper)
            {
                // fallback: prototype (als de app geladen is maar de tabel niet bound)
                var orig2 = warnguideApp.prototype._WarningStatusMsgHandler;
                var w2 = function (msg)
                {
                    var r = orig2.apply(this, arguments);
                    try { tpmsSet(tpmsReadState()); } catch (eW2) { }
                    return r;
                };
                w2.oemplusTpmsWrapper = true;
                warnguideApp.prototype._WarningStatusMsgHandler = w2;
                S.tpmsOrigHandler = orig2;
            }
            // 2) initial state (cache) + divs in de huidige ecoStatusCtrl
            var st = tpmsReadState();
            tpmsSet(st);
            tpmsEnsureDivs();
            S.tpmsHooked = true;
            note("P5 TPMS-hook actief (state=" + S.tpmsState + (S.tpmsSeen ? "" : ", nooit data") + ")");
            return true;
        }
        catch (e)
        {
            fail("tpmsHook", e);
            return false;
        }
    }

    function tpmsUnhook()
    {
        try
        {
            // wrapper van de prototype af (alleen als de onze er nog op staat)
            var proto = null;
            try
            {
                var wg = framework._appInstances && framework._appInstances.warnguide;
                if (wg && wg.constructor && wg.constructor.prototype)
                {
                    proto = wg.constructor.prototype;
                }
            }
            catch (eP) { }
            if (!proto && window.warnguideApp && warnguideApp.prototype)
            {
                proto = warnguideApp.prototype;
            }
            if (S.tpmsOrigTable && S.tpmsOrigTable["WarningStatus"] &&
                S.tpmsOrigTable["WarningStatus"].oemplusTpmsWrapper && S.tpmsOrigHandler)
            {
                S.tpmsOrigTable["WarningStatus"] = S.tpmsOrigHandler;
            }
            if (proto && proto._WarningStatusMsgHandler && proto._WarningStatusMsgHandler.oemplusTpmsWrapper &&
                S.tpmsOrigHandler)
            {
                proto._WarningStatusMsgHandler = S.tpmsOrigHandler;
            }
            if (S.tpmsPulseTimer)
            {
                try { clearInterval(S.tpmsPulseTimer); } catch (eT) { }
                S.tpmsPulseTimer = null;
            }
            // divs weg (alle ecoStatusCtrl-instanties die we kennen)
            for (var i = 0; i < S.tpmsDivs.length; i++)
            {
                var d = S.tpmsDivs[i];
                try { if (d && d.parentNode) { d.parentNode.removeChild(d); } } catch (eD) { }
            }
            S.tpmsDivs = [];
            try
            {
                var eco = framework.getAppInstance && framework.getAppInstance("ecoenergy");
                var t = eco && eco._currentContextTemplate;
                var c = t && t.ecoStatusCtrl;
                if (c && c._oemplusTpmsDivs)
                {
                    c._oemplusTpmsDivs = null;
                }
            }
            catch (eC) { }
        }
        catch (e) { fail("tpmsUnhook", e); }
        S.tpmsHooked = false;
        S.tpmsOrigHandler = null;
        S.tpmsOrigTable = null;
        S.tpmsState = "none";
        S.tpmsSeen = false;
        S.tpmsPulseOn = false;
    }

    /* ------------------------------------------------------------------ aan / uit ------------------------------------------------------------------ */

    function apply()
    {
        try
        {
            var hooks = hookSystem();
            var sbn = hookSbn();          /* v1.2: nav-straatnaam-SBN's filteren */
            S.on = true;
            endNavSbnNow();               /* v1.2: evt. nu getoonde straatnaam-banner direct weg */
            window.MainMenuCtrl = makeGuarded();
            startGuard();
            hookCallHandle();             /* v1.4 / P0: synchrone contextwissel-hook voor de submenu-bewaker */
            hookTransition();             /* v1.4 / P0 (F1/V1): tweede synchrone hook, voor template-constructie */
            if (!isHome())
            {
                cssB2On();
            }
            /* v1.4 / P0: submenu-CSS + body.OemplusB2 aan (bewaker zet de klasse per context, protected uitgezonderd) */
            S.subOn = true;
            subCssOn();
            setSubClass();
            termHook();               /* v1.4 punt 8: Terminal-item in Applicaties (runtime-patch, RAM-only) */
            ritHook();                /* v1.5: item "Rit & rijstijl" direct na Brandstofverbruik (runtime-patch) */
            homeRitHook();            /* v1.5 punt 7: contextvak-regel op B2-home ("Rijstijl 8,6" / "Rit 12 km") */
            tpmsHook();               /* v1.4 / P5-eco: TPMS (indirect) read-only uit warnguide + 2 bandenbubbels */
            note("B2 aan (hooks " + hooks + "/4, sbn-hooks " + sbn + "/" + SBN_APIS.length + (S.cssOn ? "" : ", CSS bij eerste B2-home") +
                 ", submenu-CSS " + PATHS.subCss.length + " posities, TPMS " + S.tpmsState + ")");
            return true;
        }
        catch (e)
        {
            fail("apply", e);
            revert(false);
            return false;
        }
    }

    // keepCssForLive: CSS laten staan zolang er een B2-instantie leeft (wordt bij diens cleanUp weggehaald)
    function revert(keepCssForLive)
    {
        try
        {
            S.on = false;
            unhookSystem();
            unhookSbn();              /* v1.2 */
            /* v1.4 / P0: submenu's uit (klasse weg + B2Sub-links weg),-onafhankelijk van de home-CSS */
            S.subOn = false;
            try { document.body.classList.remove(SUB_CLASS); } catch (eSub) { }
            S.transPending = null;
            S.pendingCtxt = null;
            subCssOffLinks();
            ritUnhook();              /* v1.5: Rit-item + paneel + wrappers netjes terug (LIFO: v----r termUnhook) */
            termUnhook();             /* v1.4 punt 8: Terminal-item + wrapper netjes terug */
            homeRitUnhook();          /* v1.5 punt 7: home-contextregel weg */
            tpmsUnhook();             /* v1.4 / P5-eco: TPMS-wrapper + divs netjes terug */
            unhookCallHandle();
            unhookTransition();
            if (!(keepCssForLive && S.liveB2 > 0))
            {
                cssB2Off();
            }
            if (expectedCtor())
            {
                window.MainMenuCtrl = expectedCtor();
            }
            dropBodyClass();
            note("B2 uit");
        }
        catch (e)
        {
            fail("revert", e);
        }
    }

    function b2On(cb)
    {
        try
        {
            if (S.on)
            {
                cb(true);
                return;
            }
            if (!S.origCtor)
            {
                S.origCtor = window.MainMenuCtrl;
            }
            if (typeof S.origCtor !== "function" || S.origCtor.oemplusGuarded || isB2Ctor(S.origCtor))
            {
                fail("b2On", "originele MainMenuCtrl ontbreekt/onherkenbaar");
                S.origCtor = null;
                cb(false);
                return;
            }
            startGuard();
            S.lastErr = "";
            loadB2Ctor(function (ok)
            {
                cb(ok ? apply() : false);
            });
        }
        catch (e)
        {
            fail("b2On", e);
            cb(false);
        }
    }

    function b2Off()
    {
        revert(false);
    }

    function status()
    {
        var fw = "?";
        try { fw = framework._frameworkState; } catch (e) { }
        return {
            version : VERSION,
            on : S.on,
            ctor : (S.on && S.wrapper && window.MainMenuCtrl === S.wrapper) ? "B2" : "origineel",
            b2Loaded : !!S.b2Ctor,
            hooks : hookCount(),
            sbnHooks : sbnHookCount(),
            sbnDropped : S.sbnDropped,
            cssOn : S.cssOn,
            subOn : S.subOn,             /* v1.4 / P0 */
            subClass : document.body.classList.contains(SUB_CLASS),   /* v1.4 / P0 */
            protectedNow : (function () { var i = currIds(); return isProtected(i.uia, i.ctxt); })(),  /* v1.4 / P0 */
            subLinks : S.subLinks.length, /* v1.4 / P0: aantal B2Sub-<link>s in de DOM */
            subCtxt : (function () { var i = currIds(); return (i.uia || "?") + "/" + (i.ctxt || "?"); })(),  /* v1.4 / P0 (F4/V3) */
            lastSub : S.lastSub,         /* v1.4 / P0 (F4/V3): laatste bewaker-actie */
            ctxtHook : S.ctxtHooked,     /* v1.4 / P0 (F4/V3): wrapper op _callHandleContext staat */
            transHook : S.transHooked,   /* v1.4 / P0 (F4/V3): wrapper op _transitionChange staat */
            ritHooked : S.ritHooked,     /* v1.5: item "Rit & rijstijl" staat in Applicaties */
            ritPanel : S.ritPanel ? { open : true, page : S.ritPanel.model.page, drive : S.ritPanel.model.drive } : null,  /* v1.5 */
            live : (window.OemplusLive ? window.OemplusLive.status() : null),  /* v1.5: transport/stats van OemplusLive */
            tpmsHook : S.tpmsHooked,     /* v1.4 / P5-eco */
            tpmsState : S.tpmsState,     /* v1.4 / P5-eco: none | ok | low | fault */
            tpmsSeen : S.tpmsSeen,       /* v1.4 / P5-eco: ooit warnguide-data gehad */
            liveB2 : S.liveB2,
            b2Errors : S.b2Errors,
            regHooked : S.regHooked,
            guard : !!S.guardTimer,
            fwState : fw,
            lastErr : S.lastErr,
            events : S.events.slice(0)
        };
    }

    /* ------------------------------------------------------------------ paneel ------------------------------------------------------------------ */

    var ITEMS = [
        { id : "on",   text : "B2 aan (home + submenu's)" },
        { id : "off",  text : "B2 uit (tot herstart)" },
        { id : "info", text : "Info" },
        { id : "eco",  text : "Verder naar Eco-scherm" }
    ];

    var PANEL_OPEN_CLASS = "B2EcoPanelOpen";   /* v1.4-r2: zie Panel._build / B2Sub-50-eco.css */

    function Panel(tmpl)
    {
        this.tmpl = tmpl;
        this.focus = 0;
        this.visible = true;
        this.rows = [];
        this.downIdx = -1;
        this.showFocus = false;
        this._build();
    }

    Panel.prototype._build = function ()
    {
        var self = this;
        var d = document.createElement("div");
        d.className = "OemplusInjPanel";
        var t = document.createElement("div");
        t.className = "OemplusInjTitle";
        t.innerHTML = "OEM+ &middot; B2 (proef, v1.5)";
        d.appendChild(t);
        this.stateEl = document.createElement("div");
        this.stateEl.className = "OemplusInjState";
        d.appendChild(this.stateEl);
        for (var i = 0; i < ITEMS.length; i++)
        {
            var r = document.createElement("div");
            r.className = "OemplusInjRow";
            r.style.top = (64 + i * 54) + "px";
            r.innerHTML = ITEMS[i].text;
            r.setAttribute("data-idx", String(i));
            d.appendChild(r);
            this.rows.push(r);
        }
        this.infoEl = document.createElement("div");
        this.infoEl.className = "OemplusInjInfo";
        d.appendChild(this.infoEl);

        this._down = function (evt) { self._onDown(evt); };
        this._up = function (evt) { self._onUp(evt); };
        d.addEventListener("mousedown", this._down, false);
        d.addEventListener("mouseup", this._up, false);
        this.div = d;
        this.tmpl.divElt.appendChild(d);
        /* v1.4-r2 (BORD-BOUW defect 2): marker op de template-div zolang het paneel open staat, zodat
         * B2Sub-50-eco.css de B2-eco decoraties (fixed KPI-kaart, 800x416 bubbel-lagen) onder/naast het
         * menu verbergt. Alleen een extra klasse; OEM-klassen en hitboxes blijven ongemoeid. */
        try { this.tmpl.divElt.classList.add(PANEL_OPEN_CLASS); } catch (eC) { }
        this.refresh();
    };

    Panel.prototype._rowIndex = function (evt)
    {
        var el = evt.target;
        while (el && el !== this.div)
        {
            if (el.getAttribute && el.getAttribute("data-idx") !== null && el.getAttribute("data-idx") !== "")
            {
                return parseInt(el.getAttribute("data-idx"), 10);
            }
            el = el.parentNode;
        }
        return -1;
    };

    Panel.prototype._onDown = function (evt)
    {
        try
        {
            this.downIdx = this._rowIndex(evt);
            if (this.downIdx >= 0)
            {
                this.focus = this.downIdx;
                this.showFocus = true;
                this.refresh();
            }
        }
        catch (e) { fail("panel down", e); }
    };

    Panel.prototype._onUp = function (evt)
    {
        try
        {
            var idx = this._rowIndex(evt);
            if (idx >= 0 && idx === this.downIdx)
            {
                this.select(idx);
            }
            this.downIdx = -1;
        }
        catch (e) { fail("panel up", e); }
    };

    Panel.prototype.refresh = function ()
    {
        try
        {
            var st = status();
            this.stateEl.innerHTML = "Scherm: <b>" + (st.on ? "B2 (actief)" : "origineel") + "</b>" +
                (st.lastErr ? " &middot; <span class=\"OemplusInjErr\">fout</span>" : "");
            for (var i = 0; i < this.rows.length; i++)
            {
                var cls = "OemplusInjRow";
                if (i === this.focus && this.showFocus)
                {
                    cls += " OemplusInjFocus";
                }
                if ((ITEMS[i].id === "on" && st.on) || (ITEMS[i].id === "off" && !st.on))
                {
                    cls += " OemplusInjDim";
                }
                this.rows[i].className = cls;
            }
        }
        catch (e) { fail("panel refresh", e); }
    };

    Panel.prototype.setInfo = function (html)
    {
        try { this.infoEl.innerHTML = html || ""; } catch (e) { }
    };

    Panel.prototype.select = function (idx)
    {
        var self = this;
        try
        {
            var id = ITEMS[idx].id;
            if (id === "on")
            {
                this.setInfo("B2 laden&hellip;");
                b2On(function (ok)
                {
                    self.setInfo(ok ? "B2 staat aan. Druk op <b>Home</b>." : "B2 NIET aangezet: " + S.lastErr + "<br>Home blijft origineel.");
                    self.refresh();
                });
            }
            else if (id === "off")
            {
                b2Off();
                this.setInfo("Origineel home-scherm terug (tot herstart).");
            }
            else if (id === "info")
            {
                var st = status();
                this.setInfo(st.version + " &middot; home: " + st.ctor + " &middot; B2-bestand: " + (st.b2Loaded ? "ja" : "nee") +
                    " &middot; hooks: " + st.hooks + "/4 &middot; SBN: " + st.sbnHooks + "/" + SBN_APIS.length +
                    " (nav onderdrukt: " + st.sbnDropped + ") &middot; CSS: " + (st.cssOn ? "aan" : "uit") +
                    " &middot; fouten: " + st.b2Errors + "<br>" +
                    "submenu's: " + (st.subOn ? "aan" : "uit") + " &middot; OemplusB2: " + (st.subClass ? "ja" : "nee") +
                    " &middot; scherm: " + st.subCtxt + " &middot; protected: " + (st.protectedNow ? "ja" : "nee") +
                    " &middot; links: " + st.subLinks + "/" + PATHS.subCss.length +
                    " &middot; hooks ctxt/transition: " + (st.ctxtHook ? "ja" : "NEE") + "/" + (st.transHook ? "ja" : "NEE") +
                    (st.lastSub ? " &middot; " + st.lastSub : "") + "<br>" +
                    (st.lastErr ? "fout: " + st.lastErr + "<br>" : "") +
                    "RAM-only; herstart CMU = fabriek.");
            }
            else if (id === "eco")
            {
                this.hide();
                return;
            }
            this.refresh();
        }
        catch (e)
        {
            fail("panel select", e);
        }
    };

    Panel.prototype.hide = function ()
    {
        try
        {
            this.visible = false;
            this.div.style.display = "none";
            try { this.tmpl.divElt.classList.remove(PANEL_OPEN_CLASS); } catch (eC) { }
            // het originele scherm krijgt de focus terug zoals bij binnenkomst
            if (this.tmpl && this.tmpl.oemplusOrigHandle)
            {
                this.tmpl.oemplusOrigHandle.call(this.tmpl, "acceptFocusInit");
            }
        }
        catch (e) { fail("panel hide", e); }
    };

    // true = event door het paneel afgehandeld
    Panel.prototype.handle = function (eventId)
    {
        if (!this.visible)
        {
            return false;
        }
        switch (eventId)
        {
            case "cw":
            case "down":
                this.focus = (this.focus + 1) % ITEMS.length;
                this.showFocus = true;
                this.refresh();
                return true;
            case "ccw":
            case "up":
                this.focus = (this.focus + ITEMS.length - 1) % ITEMS.length;
                this.showFocus = true;
                this.refresh();
                return true;
            case "select":
                this.showFocus = true;
                this.select(this.focus);
                return true;
            case "acceptFocusInit":
            case "acceptFocusFromLeft":
            case "acceptFocusFromTop":
            case "acceptFocusFromRight":
            case "acceptFocusFromBottom":
                this.showFocus = true;
                this.refresh();
                return true;
            case "selectStart":
            case "selectHold":
            case "upStart":
            case "downStart":
            case "left":
            case "right":
            case "leftStart":
            case "rightStart":
                return true;
            default:
                return false;   // controllerActive/touchActive/lostFocus/... gaan ook naar het originele scherm
        }
    };

    /* ------------------------------------------------------------------ v1.5: paneel "Rit & rijstijl" (BOUWPLAN-RIT) ----
     * Item "Rit & rijstijl" direct ONDER Brandstofverbruik (ecoenergy) in Applicaties; Enter opent een eigen
     * DOM-paneel over de Applications-template (geen MMUI-verkeer, zelfde mechaniek als termHook). Navigeren =
     * draaien + kantelen L/R (B2DriveView.nav), ook rijdend (besluit de gebruiker: GEEN rustscherm-lock; max 1x/s verversen, geen animaties).
     * Terug-knop = OEM (MMUI verlaat Applicaties -> cleanUp ruimt op); lang indrukken = paneel dicht.
     * Startpagina: Vorige rit als de huidige rit < 0,5 km (B2DriveView.startPage). */
    var RIT_APP = "oemplusrit";

    function ritItemPresent(sys)
    {
        try
        {
            var items = sys._masterApplicationDataList && sys._masterApplicationDataList.items;
            if (!items) { return false; }
            for (var i = 0; i < items.length; i++)
            {
                if (items[i] && items[i].appData && items[i].appData.appName === RIT_APP) { return true; }
            }
        }
        catch (e) { }
        return false;
    }

    // invoegpositie: direct na het item met appName "ecoenergy" (Brandstofverbruik); anders achteraan
    function ritInsertIndex(items)
    {
        for (var i = 0; i < items.length; i++)
        {
            if (items[i] && items[i].appData && items[i].appData.appName === "ecoenergy") { return i + 1; }
        }
        return items.length;
    }

    function ritWrapListCallback(tmpl)
    {
        try
        {
            var l2 = tmpl && tmpl.list2Ctrl;
            var props = l2 && l2.properties;
            if (!props || typeof props.selectCallback !== "function" || props.selectCallback.oemplusRitWrapper)
            {
                return false;
            }
            var orig = props.selectCallback;
            var w = function (listCtrlObj, appData, params)
            {
                try
                {
                    if (appData && appData.appName === RIT_APP)
                    {
                        ritPanelOpen(listCtrlObj);   // NIETS naar MMUI
                        return true;
                    }
                }
                catch (eR) { fail("Rit select", eR); }
                return orig.call(this, listCtrlObj, appData, params);
            };
            w.oemplusRitWrapper = true;
            w.oemplusRitOrig = orig;
            props.selectCallback = w;
            return true;
        }
        catch (e) { fail("ritWrapListCallback", e); }
        return false;
    }

    function ritUnwrapListCallback(tmpl)
    {
        try
        {
            var l2 = tmpl && tmpl.list2Ctrl;
            var props = l2 && l2.properties;
            if (props && typeof props.selectCallback === "function" && props.selectCallback.oemplusRitWrapper)
            {
                props.selectCallback = props.selectCallback.oemplusRitOrig || props.selectCallback;
            }
        }
        catch (e) { }
    }

    function ritHook()
    {
        try
        {
            if (S.ritHooked) { return true; }
            var sys = framework.getAppInstance("system");
            if (!sys || !sys._masterApplicationDataList || !sys._applicationsCtxtWiseAppNames)
            {
                note("Rit: systemApp niet gevonden -> overslaan");
                return false;
            }
            var items = sys._masterApplicationDataList.items;
            if (!ritItemPresent(sys))
            {
                S.ritItem = { appData : { appName : RIT_APP, isVisible : true, audioSourceId : "None", mmuiEvent : "OemplusRit" },
                               text1 : "Rit & rijstijl", disabled : false, itemStyle : "style01", hasCaret : false };
                items.splice(ritInsertIndex(items), 0, S.ritItem);
                sys._masterApplicationDataList.itemCount = items.length;
            }
            else { S.ritItem = null; }
            var cwn = sys._applicationsCtxtWiseAppNames;
            for (var ctxt in cwn)
            {
                if (cwn.hasOwnProperty(ctxt) && ctxt === "Applications" && Object.prototype.toString.call(cwn[ctxt]) === "[object Array]")
                {
                    if (cwn[ctxt].indexOf(RIT_APP) === -1)
                    {
                        // invoegen direct na ecoenergy in de appNames-lijst (zelfde plek als het item)
                        var ai = cwn[ctxt].indexOf("ecoenergy");
                        if (ai >= 0) { cwn[ctxt].splice(ai + 1, 0, RIT_APP); } else { cwn[ctxt].push(RIT_APP); }
                        S.ritNames.push(RIT_APP);
                        S.ritCtxts.push(ctxt);
                    }
                }
            }
            var wrapped = 0;
            try
            {
                var t = sys._currentContextTemplate;
                if (t && framework.getCurrCtxtId() === "Applications") { if (ritWrapListCallback(t)) { wrapped++; } }
            }
            catch (eC) { }
            try
            {
                var entry = sys._contextTable && sys._contextTable["Applications"];
                var props = entry && entry.controlProperties && entry.controlProperties.List2Ctrl;
                if (props && typeof props.selectCallback === "function" && !props.selectCallback.oemplusRitWrapper)
                {
                    var orig = props.selectCallback;
                    var w = function (listCtrlObj, appData, params)
                    {
                        try
                        {
                            if (appData && appData.appName === RIT_APP) { ritPanelOpen(listCtrlObj); return true; }
                        }
                        catch (eT) { fail("Rit select (ctxtTable)", eT); }
                        return orig.call(this, listCtrlObj, appData, params);
                    };
                    w.oemplusRitWrapper = true;
                    w.oemplusRitOrig = orig;
                    props.selectCallback = w;
                    wrapped++;
                }
            }
            catch (eT2) { }
            S.ritHooked = true;
            note("Rit & rijstijl-item gepatcht (item " + (S.ritItem ? "toegevoegd na ecoenergy" : "al aanwezig") + ", appNames " + S.ritNames.length + ", callbacks " + wrapped + ")");
            return true;
        }
        catch (e)
        {
            fail("ritHook", e);
            return false;
        }
    }

    function ritUnhook()
    {
        try
        {
            ritPanelClose();
            var sys = framework.getAppInstance("system");
            if (sys)
            {
                if (S.ritItem && sys._masterApplicationDataList && sys._masterApplicationDataList.items)
                {
                    var items = sys._masterApplicationDataList.items;
                    for (var i = items.length - 1; i >= 0; i--)
                    {
                        if (items[i] === S.ritItem || (items[i] && items[i].appData && items[i].appData.appName === RIT_APP && S.ritItem))
                        {
                            items.splice(i, 1);
                        }
                    }
                    sys._masterApplicationDataList.itemCount = items.length;
                }
                var cwn = sys._applicationsCtxtWiseAppNames;
                if (cwn)
                {
                    for (var c = 0; c < S.ritCtxts.length; c++)
                    {
                        var arr = cwn[S.ritCtxts[c]];
                        if (Object.prototype.toString.call(arr) === "[object Array]")
                        {
                            for (var k = arr.length - 1; k >= 0; k--)
                            {
                                if (arr[k] === RIT_APP) { arr.splice(k, 1); }
                            }
                        }
                    }
                }
                try
                {
                    var entry = sys._contextTable && sys._contextTable["Applications"];
                    var props = entry && entry.controlProperties && entry.controlProperties.List2Ctrl;
                    if (props && typeof props.selectCallback === "function" && props.selectCallback.oemplusRitWrapper)
                    {
                        props.selectCallback = props.selectCallback.oemplusRitOrig || props.selectCallback;
                    }
                }
                catch (e1) { }
                ritUnwrapListCallback(sys._currentContextTemplate);
            }
        }
        catch (e) { fail("ritUnhook", e); }
        S.ritHooked = false;
        S.ritItem = null;
        S.ritNames = [];
        S.ritCtxts = [];
    }

    /* ---- RitPanel: eigen DOM-paneel in de Applications-template (model van Panel/attach) ---- */
    function ritLoadScripts(cb)
    {
        // lazy load B2DriveView.js + OemplusLive.js (eenmalig per sessie)
        try
        {
            if (window.B2DriveView && window.OemplusLive) { cb(true); return; }
            var n = 0, done = 0, ok = true;
            var onload = function (good) { done++; if (!good) { ok = false; } if (done === n) { cb(ok); } };
            var load = function (src) {
                n++;
                var s = document.createElement("script");
                s.src = src;
                s.onload = function () { onload(true); };
                s.onerror = function () { onload(false); };
                document.getElementsByTagName("head")[0].appendChild(s);
            };
            if (!window.B2DriveView) { load("common/oemplusb2/js/B2DriveView.js"); } else { n++; done++; }
            if (!window.OemplusLive) { load("apps/ecoenergy/oemplus/OemplusLive.js"); } else { n++; done++; }
            if (n === 0) { cb(true); }
        }
        catch (e) { fail("ritLoadScripts", e); cb(false); }
    }

    function RitPanel(tmpl)
    {
        this.tmpl = tmpl;
        this.page = 0;
        this.model = { page : 0, data : null, rxAgeS : null, drive : false, transport : null, retryS : 0 };
        this.userNav = false;      // gebruiker heeft zelf gebladerd -> startpagina niet meer overschrijven
        this.startSet = false;     // startpagina bepaald op de eerste data (Vorige rit tot rit >= 0,5 km)
        this.div = null;
        this.timer = null;
        this.origHandle = null;
        this.origClean = null;
        this.selectAt = 0;
        this.lastRenderKey = "";
        this.lastDataTs = 0;
        this.stillSince = 0;
        this._onData = null;
        this._down = null;
        this._up = null;
    }

    RitPanel.prototype.open = function ()
    {
        var self = this;
        try
        {
            var t = this.tmpl;
            if (!t || !t.divElt) { return; }
            var d = document.createElement("div");
            this.div = d;
            t.divElt.appendChild(d);
            ritLoadScripts(function (ok) {
                try
                {
                    if (!ok || !window.B2DriveView) { note("Rit: B2DriveView laden mislukt"); self.close(); return; }
                    window.B2DriveView.build(d);
                    // laatste bekende snapshot (bv. van de home-regel) meteen gebruiken voor de startpagina
                    try { var st0 = window.OemplusLive ? window.OemplusLive.status() : null; if (st0 && st0.last) { self.model.data = st0.last; self.model.rxAgeS = st0.rxAgeS; } } catch (eS0) { }
                    if (self.model.data) { self.model.page = window.B2DriveView.startPage(self.model.data); self.startSet = true; }
                    self.paint();
                    // events
                    self.origHandle = t.handleControllerEvent;
                    t.handleControllerEvent = function (ev) { return self.handle(ev); };
                    // review v1.5: orig lokaal vasthouden -- close() zet self.origClean op null, dus NIET self.origClean.apply
                    // erna (gaf TypeError midden in de OEM-cleanUp bij Terug/camera met paneel open).
                    var origClean = t.cleanUp;
                    self.origClean = origClean;
                    t.cleanUp = function () { try { self.close(true); } catch (eC) { } return origClean.apply(t, arguments); };
                    // touch (alleen stilstand; pageX/pageY -> paneel-coordinaten 60,64)
                    self._down = function (ev) { try { self._tx = ev.pageX - 60; self._ty = ev.pageY - 64; self._t0 = new Date().getTime(); } catch (e) { } };
                    self._up = function (ev) {
                        try
                        {
                            if (self.model.drive) { return; }
                            var r = window.B2DriveView.touch(self.model, self._tx, ev.pageX - 60, ev.pageY - 64);
                            if (r.consumed && r.page !== self.model.page) { self.model.page = r.page; self.userNav = true; self.paint(); }
                        }
                        catch (eT) { }
                    };
                    d.addEventListener("mousedown", self._down, false);
                    d.addEventListener("mouseup", self._up, false);
                    // live data
                    if (window.OemplusLive) {
                        self._onData = function (data, ageS) { self.onData(data, ageS); };
                        window.OemplusLive.subscribe(self._onData);
                    }
                    // app-naam in de statusbalk
                    try { self._sbName = framework.common.statusBar.getAppName ? framework.common.statusBar.getAppName() : null; } catch (eS) { self._sbName = null; }
                    try { framework.common.statusBar.setAppName("Rit & rijstijl"); } catch (eS2) { }
                    // 1x/s tik: drive bepalen + renderen als iets veranderde
                    self.timer = setInterval(function () { self.tick(); }, 1000);
                    note("Rit-paneel open (pagina " + self.model.page + ")");
                }
                catch (e2) { fail("RitPanel.open", e2); self.close(); }
            });
        }
        catch (e) { fail("RitPanel.open", e); this.close(); }
    };

    RitPanel.prototype.handle = function (ev)
    {
        try
        {
            if (!this.div || !window.B2DriveView) { return this.origHandle ? this.origHandle.apply(this.tmpl, arguments) : "consumed"; }
            var held = 0;
            if (ev === "select") { held = this.selectAt ? (new Date().getTime() - this.selectAt) : 0; }
            if (ev === "selectStart") { this.selectAt = new Date().getTime(); return "consumed"; }
            var r = window.B2DriveView.nav(this.model, ev, held);
            if (r.action === "close") { this.close(); return "consumed"; }
            if (r.action === "reconnect") { if (window.OemplusLive) { window.OemplusLive.reconnectNow(); } }
            if (r.consumed) {
                if (r.page !== this.model.page) { this.model.page = r.page; this.userNav = true; this.paint(); }
                return "consumed";
            }
        }
        catch (e) { fail("RitPanel.handle", e); }
        return this.origHandle ? this.origHandle.apply(this.tmpl, arguments) : "consumed";
    };

    RitPanel.prototype.onData = function (data, ageS)
    {
        try
        {
            if (data) { this.model.data = data; this.lastDataTs = data.ts || 0; }
            if (data && !this.startSet && !this.userNav && window.B2DriveView)
            {
                this.model.page = window.B2DriveView.startPage(data);
                this.startSet = true;
            }
            this.model.rxAgeS = ageS;
            var st = window.OemplusLive ? window.OemplusLive.status() : null;
            if (st) { this.model.transport = st.transport; this.model.retryS = st.retryS; }
            this.paint();
        }
        catch (e) { }
    };

    RitPanel.prototype.driveNow = function ()
    {
        // ONTWERP-RIT par.3.2: AtSpeed || (live && (moving || speed >= 5)); stilstand pas als BEIDE stil
        try
        {
            var atSpeed = false;
            try { atSpeed = !!(framework.common.getAtSpeedValue && framework.common.getAtSpeedValue()); } catch (eA) { }
            var d = this.model.data, nu = d && d.nu ? d.nu : null;
            var piMoving = !!(nu && (nu.rijdend === true || (typeof nu.kmh === "number" && nu.kmh >= 5)));
            if (atSpeed || piMoving) { this.stillSince = 0; return true; }
            // terug naar stilstand pas als speed < 3 gedurende >= 3 s (of geen live data)
            if (nu && typeof nu.kmh === "number" && nu.kmh < 3)
            {
                var n = new Date().getTime();
                if (!this.stillSince) { this.stillSince = n; }
                if (n - this.stillSince >= 3000) { return false; }
                return this.model.drive; // hysterese
            }
            if (!d) { return this.model.drive ? true : false; }
            return false;
        }
        catch (e) { return true; }   // bij twijfel: rijdend (veilig)
    };

    RitPanel.prototype.tick = function ()
    {
        // 1x/s: drive bepalen (alleen touch uit + gedempte titel) en hertekenen als iets veranderde (paint dedupliceert)
        try
        {
            if (!this.div) { return; }
            this.model.drive = this.driveNow();
            this.paint();
        }
        catch (e) { }
    };

    RitPanel.prototype.paint = function ()
    {
        try
        {
            if (!this.div || !window.B2DriveView) { return; }
            var st = window.OemplusLive ? window.OemplusLive.status() : null;
            if (st) { this.model.transport = st.transport; this.model.retryS = st.retryS; this.model.rxAgeS = st.rxAgeS; }
            // renderen alleen als iets veranderde (pagina, drive, conn, ts, age bij oud)
            var conn = window.B2DriveView.conn(this.model);
            var key = this.model.page + "|" + this.model.drive + "|" + conn + "|" + this.lastDataTs + "|" +
                (conn === "old" || conn === "none" ? Math.round(this.model.rxAgeS || 0) + "|" + this.model.retryS : "");
            if (key === this.lastRenderKey) { return; }
            this.lastRenderKey = key;
            window.B2DriveView.render(this.div, this.model);
        }
        catch (e) { fail("RitPanel.paint", e); }
    };

    RitPanel.prototype.close = function (fromCleanUp)
    {
        try
        {
            var hadHandle = !!this.origHandle;
            if (this.timer) { clearInterval(this.timer); this.timer = null; }
            if (this._onData && window.OemplusLive) { try { window.OemplusLive.unsubscribe(this._onData); } catch (eU) { } this._onData = null; }
            if (this.div)
            {
                try { this.div.removeEventListener("mousedown", this._down, false); } catch (e1) { }
                try { this.div.removeEventListener("mouseup", this._up, false); } catch (e2) { }
                try { if (this.div.parentNode) { this.div.parentNode.removeChild(this.div); } } catch (e3) { }
            }
            this.div = null;
            if (this.tmpl && this.origHandle) { try { this.tmpl.handleControllerEvent = this.origHandle; } catch (e4) { } this.origHandle = null; }
            if (this.tmpl && this.origClean) { try { this.tmpl.cleanUp = this.origClean; } catch (e5) { } this.origClean = null; }
            try { if (this._sbName !== null && this._sbName !== undefined && framework.common.statusBar.setAppName) { framework.common.statusBar.setAppName(this._sbName); } } catch (e6) { }
            // focus terug naar de OEM-lijst (alleen bij zelf sluiten; niet tijdens de OEM-cleanUp van het template)
            try { if (!fromCleanUp && hadHandle && this.tmpl && this.tmpl.list2Ctrl) { this.tmpl.handleControllerEvent("acceptFocusInit"); } } catch (e7) { }
            if (S.ritPanel === this) { S.ritPanel = null; }
            note("Rit-paneel dicht");
        }
        catch (e) { fail("RitPanel.close", e); }
    };

    function ritPanelOpen(listCtrlObj)
    {
        try
        {
            if (S.ritPanel) { return; }   // al open
            var sys = framework.getAppInstance("system");
            var t = sys && sys._currentContextTemplate;
            if (!t || framework.getCurrCtxtId() !== "Applications") { t = (listCtrlObj && listCtrlObj._tmpl) || t; }
            if (!t || !t.divElt) { note("Rit: geen Applications-template"); return; }
            S.ritPanel = new RitPanel(t);
            S.ritPanel.open();
        }
        catch (e) { fail("ritPanelOpen", e); }
    }

    function ritPanelClose()
    {
        try { if (S.ritPanel) { S.ritPanel.close(); } } catch (e) { }
        S.ritPanel = null;
    }

    /* ---- v1.5 punt 7: home-contextregel (App-vak). Abonneert op OemplusLive zolang B2 aan + home zichtbaar is;
     * de echte tekst zet MainMenuCtrl-oemplusb2.js (_b2UpdateRit) in het B2-contextvak. Bij protected/B2-uit:
     * abonnement weg (OemplusLive stopt bij 0 abonnees). */
    var homeRitOn = false, homeRitTimer = null, homeRitLiveSub = null, homeRitLoading = false;
    function homeRitHook()
    {
        try
        {
            if (homeRitOn || !S.subOn) { return; }
            homeRitOn = true;
            // 2 s tik: alleen als het B2-home zichtbaar is abonneren op OemplusLive (anders: geen netwerk/timers voor de regel)
            homeRitTimer = setInterval(homeRitTick, 2000);
            homeRitTick();
            note("home-rijstijl-regel aan (2 s tik; live alleen zolang home zichtbaar)");
        }
        catch (e) { fail("homeRitHook", e); }
    }
    function homeRitSub(on)
    {
        try
        {
            if (on)
            {
                if (homeRitLiveSub || homeRitLoading) { return; }
                homeRitLoading = true;
                ritLoadScripts(function (ok) {
                    homeRitLoading = false;
                    try
                    {
                        if (ok && window.OemplusLive && homeRitOn && !homeRitLiveSub && document.body.classList.contains("OemplusB2Home"))
                        {
                            homeRitLiveSub = function () { homeRitPaint(); };
                            window.OemplusLive.subscribe(homeRitLiveSub);
                        }
                    }
                    catch (eL) { }
                });
            }
            else if (homeRitLiveSub)
            {
                try { if (window.OemplusLive) { window.OemplusLive.unsubscribe(homeRitLiveSub); } } catch (eU) { }
                homeRitLiveSub = null;
            }
        }
        catch (e) { }
    }
    function homeRitPaint()
    {
        try
        {
            var sys = framework.getAppInstance("system");
            var t = sys && sys._currentContextTemplate;
            var mm = t && t.mainMenuControl;   // HomeScreen-template: this.mainMenuControl = instantiateControl(... MainMenuCtrl)
            if (mm && mm._b2UpdateRit) { mm._b2UpdateRit(); }
        }
        catch (e) { }
    }
    function homeRitTick()
    {
        try
        {
            if (!homeRitOn) { return; }
            var vis = document.body.classList.contains("OemplusB2Home");
            homeRitSub(vis);
            if (vis) { homeRitPaint(); }   // ook zonder frames: veroudering (oud -> regel weg) zichtbaar maken
        }
        catch (e) { }
    }
    function homeRitUnhook()
    {
        try
        {
            if (homeRitTimer) { clearInterval(homeRitTimer); homeRitTimer = null; }
            homeRitOn = false;
            homeRitSub(false);
            note("home-rijstijl-regel uit");
        }
        catch (e) { }
    }

    function attach(tmpl)
    {
        try
        {
            dropBodyClass();     // M4: eco-scherm is nooit home
            if (!tmpl || !tmpl.divElt || tmpl.oemplusInjPanel)
            {
                return;
            }
            var orig = tmpl.handleControllerEvent;
            tmpl.oemplusOrigHandle = orig;
            var p = new Panel(tmpl);
            tmpl.oemplusInjPanel = p;
            S.panel = p;
            tmpl.handleControllerEvent = function (eventId)
            {
                try
                {
                    if (p.handle(eventId))
                    {
                        return "consumed";
                    }
                }
                catch (e)
                {
                    fail("handleControllerEvent", e);
                }
                return orig.apply(tmpl, arguments);
            };
            var origClean = tmpl.cleanUp;
            tmpl.cleanUp = function ()
            {
                try
                {
                    p.div.removeEventListener("mousedown", p._down, false);
                    p.div.removeEventListener("mouseup", p._up, false);
                    if (S.panel === p)
                    {
                        S.panel = null;
                    }
                }
                catch (e) { }
                return origClean.apply(tmpl, arguments);
            };
            note("paneel op " + (tmpl.templateName || "?"));
        }
        catch (e)
        {
            fail("attach", e);
        }
    }

    window.OemplusInject = {
        version : VERSION,
        attach : attach,
        b2On : b2On,
        b2Off : b2Off,
        status : status,
        _liveLog : function (m) { note("live: " + m); }   /* OemplusLive.js logt hierheen */
    };

    // template dat al bestond voordat dit bestand binnen was
    try
    {
        var pend = window.OemplusInjectPending;
        window.OemplusInjectPending = null;
        if (pend && pend.divElt && pend.divElt.parentNode)
        {
            attach(pend);
        }
    }
    catch (e)
    {
        fail("pending attach", e);
    }
    note("geladen " + VERSION);
})();
