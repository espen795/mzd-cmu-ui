/*
 Copyright 2012 by Johnson Controls
 __________________________________________________________________________

 Filename: MainMenuCtrl.js
 __________________________________________________________________________

 Project: JCI-IHU
 Language: EN
 Author: agohsmbr
 Date: 4.10.2012
 __________________________________________________________________________

 Description: System Main Menu Control

 Revisions:
 v0.1 (10-April-2012) First Version
 v0.2 (23-May-2012) Cleanup and optimization - awoodhc
 v0.3 (03-Aug-2012) Re-write of MainMenuCtrl with new Studio Assets -awoodhc
 v0.4 (06-Aug-2012) Re-added multicontroller handling -awoodhc
 v0.5 (27-Aug-2012) Updated Control select callback. Removed dummy functions from Main Menu Ctrl -awoodhc
 v0.6 (06-Mar-2013) Updated to v3.80 UI specifications from Studio -apeter9
 OEMPLUS-B2 v1 (2026-11-25) Home-layout B2: verticale lijst + contextvak. Alle toevoegingen gemarkeerd
   met OEMPLUS-B2; elke nieuwe functie draait in try/catch zodat een fout het home-scherm nooit breekt.
 OEMPLUS-B2 v1.2 (2026-11-26, alleen in ui-oemplus-inject-v1.2): SBN-banner bovenin vrijhouden (klok/rijen
   beginnen lager), contextpanelen direct vullen uit de gecachete systemApp-state bij _b2Start.
 OEMPLUS-B2 v1.2-fixes (2026-11-26, na R-cmu review ecb254e1, V1-V3 + B5/B6/B7):
   B1 contextvak terug op y 188-474 (Focus-tops 67/1/-65/-131/-197, hit-zone 188-474);
   B2 SBN-banner fail-visible: verborgen startpositie alleen zolang body.B2SbnWatch (levende watcher) staat;
   B3 _b2SeedFromSystem seedt alleen panelen waarvoor geen bericht in de systemApp-cache staat;
   B5 Set "In orde" alleen bij echte data; B6 per-paneel try/catch; B7 CSS-opschoning (lege regel, 0s, no-op weg).
 __________________________________________________________________________

 */

log.addSrcFile("MainMenuCtrl.js", "system");

function MainMenuCtrl(uiaId, parentDiv, controlId, properties)
{
    this.uiaId = uiaId;
    this.divElt = null;
    this.controlId = controlId;

    this.properties = 
    {
        // (Object) Arbitrary passed back to the app.
        "appData" : null,

        // (Function) Called when the user selects a coin via touch or commander.
        "selectCallback" : null,

        // (Number) Milliseconds to hold the controller left or right before fast-tilt kicks in. Default 1500.
        "tiltHoldTime" : 1500,

        // (Number) Milliseconds between fast-tilt steps. Default 500.
        "tiltStepTime" : 500,
    };
    
    for (var i in properties)
    {
        this.properties[i] = properties[i];
    }
    
    this._coins = 
    [
        { key : "App", focusTranslateX : 30,  focusTranslateY : -53, hasFocus : false, nameId : "Applications" },
        { key : "Ent", focusTranslateX : -15,   focusTranslateY : -30, hasFocus : false, nameId : "Entertainment" },
        { key : "Com", focusTranslateX : -15,   focusTranslateY : -30, hasFocus : false, nameId : "Communication" },
        { key : "Nav", focusTranslateX : -15,   focusTranslateY : -30, hasFocus : false, nameId : "NavigationTitle" },
        { key : "Set", focusTranslateX : -58, focusTranslateY : -53, hasFocus : false, nameId : "Settings" }
    ];

    this._tiltHoldTimerId = null;
    this._fastTiltStepIntervalId = null;

    this._fullyHighlightedIndex = null; // (Number) The index that currently has the full focus highlight.
    this._lastControllerStartEvent = "";    // (String) Used to ensure the current tabs control instance doesn't process tilt-release events from a previous tabs control instance.
    this._allowInput = true;            // (Boolean) If true, allow mouse down and controller inputs.
    this._allowInputTimerId = null;     // (Handle) setTimeout ID used to unblock input after a short time.
    this._pendingInvokeSelectIndex = null;  // (Number) Index (or null) of the selected coin used to delay the callback until the focus animation completes

    /* OEMPLUS-B2 */
    this._b2 = { els : {}, data : {}, clockTimerId : null, sbTimerId : null, lastClock : "", lastDate : "", sbnSeen : false };

    this.createStructure();   
    parentDiv.appendChild(this.divElt);
    this._prvFocus = -1 ;
    this.init();
}

// This function creates the div classes of the Main Menu
MainMenuCtrl.prototype.createStructure = function()
{ 
    this.divElt = document.createElement('div');
    this.divElt.id = this.controlId;
    this.divElt.className = "MainMenuCtrl";
    
    var ellipse = document.createElement('div');
    ellipse.className = "MainMenuCtrlEllipse";
    this.divElt.appendChild(ellipse);

    for (var i = 0; i < this._coins.length; i++)
    {
        var key = this._coins[i].key;

        this._coins[i].div = document.createElement('div');
        this._coins[i].div.className = "MainMenuCtrl" + key + "Div";

        div = document.createElement('div');
        div.className = "MainMenuCtrl" + key + "Focus";
        this._coins[i].div.appendChild(div);

        var focusDiv = div; /* OEMPLUS-B2 */

        var div = document.createElement('div');
        div.className = "MainMenuCtrl" + key + "Normal";
        this._coins[i].div.appendChild(div);

        this._coins[i].highlight = document.createElement('div');
        this._coins[i].highlight.className = "MainMenuCtrl" + key + "Highlight";

        /* OEMPLUS-B2: rij-inhoud (icoon + label) en contextvak opbouwen */
        this._b2BuildRow(i, focusDiv, div, this._coins[i].highlight);

        this._coins[i].setHighlightEndBinder = this._setHighlightEnd.bind(this, i);
        this._coins[i].div.addEventListener('OTransitionEnd', this._coins[i].setHighlightEndBinder, false);
    }

    // Add coins and highlight in correct z-order

    this.divElt.appendChild(this._coins[1].highlight);
    this.divElt.appendChild(this._coins[2].highlight);
    this.divElt.appendChild(this._coins[3].highlight);

    this.divElt.appendChild(this._coins[1].div);
    this.divElt.appendChild(this._coins[2].div);
    this.divElt.appendChild(this._coins[3].div);

    this.divElt.appendChild(this._coins[4].highlight);
    this.divElt.appendChild(this._coins[4].div);

    this.divElt.appendChild(this._coins[0].highlight);
    this.divElt.appendChild(this._coins[0].div);

    // Create text area for icon names
    this._iconNameDiv = document.createElement('div');
    this._iconNameDiv.className = "MainMenuCtrlIconName";
    this.divElt.appendChild(this._iconNameDiv);

    /* OEMPLUS-B2: scheidingslijn + kop (klok, datum, haarlijn) */
    this._b2BuildHeader();
}

// This function will be used to set the default main menu icon (maybe not always com)
MainMenuCtrl.prototype.init = function()
{
    // Record the hit test area for each normal and focus coin (can only be done after the divs are added to the DOM)
    for (var i = 0; i < this._coins.length; i++)
    {
        this._computeHitAreas(this._coins[i]);

        // Draw hit test circles for visual testing.
        // this._drawCoinBorder(this._coins[i].normalHitArea, "blue");
        // this._drawCoinBorder(this._coins[i].focusHitArea, "yellow");
    }

    this._mouseDownCallback = this._mouseDown.bind(this);
    this._mouseUpCallback = this._mouseUp.bind(this);
    this._mouseMoveCallback = this._mouseMove.bind(this);
    document.body.addEventListener("mousedown", this._mouseDownCallback);

    // (Boolean) Flag used to avoid exploding coin animations when the transition occurs for something other than touch or controller input.
    this._hasInvokedSelectCallback = false;

    // Set initial focus flag on the navigation coin
    this._setFocus(2);

    /* OEMPLUS-B2: klok starten, eerder ontvangen data ophalen, statusbalk verbergen op home (v1.1) */
    this._b2Start();
}

// Debug helper function to draw a border around each hit area.
MainMenuCtrl.prototype._drawCoinBorder = function(hitArea, color)
{
    // Add a circle to the document to show the hit area.
    var r = Math.sqrt(hitArea.r2);
    var d = r * 2;
    var x = hitArea.x - r;
    var y = hitArea.y - r - 64;

    var style = 'position:absolute; left:' + x + 'px; top:' + y + 'px; border:1px solid ' + color + '; width:' + d + 'px; height:' + d + 'px; z-index:999; border-radius:999px';

    var div = document.createElement('div');
    div.style = style;
    this.divElt.appendChild(div);
}

MainMenuCtrl.prototype._computeHitAreas = function(coin)
{
    var div = coin.div;
    var w = coin.div.offsetWidth;
    var h = coin.div.offsetHeight;

    var radius = h / 2;
    coin.normalHitArea = {
        x : div.offsetLeft + w / 2,
        y : div.offsetTop + h / 2 + this._b2PageY(), // account for the status bar (OEMPLUS-B2 v1.1: echte paginapositie)
        r2 : radius * radius,
    };

    h = h * 1.2;
    w = w * 1.2;
    radius = h / 2;
    coin.focusHitArea = {
        x : div.offsetLeft + w / 2 + coin.focusTranslateX,
        y : div.offsetTop + h / 2 + this._b2PageY() + coin.focusTranslateY, // OEMPLUS-B2 v1.1
        r2 : radius * radius,
    };

    /* OEMPLUS-B2: rijen zijn rechthoeken (372x66) en verschuiven niet bij focus -> rechthoek-hit-test,
     * gelijk voor normaal en focus. Valt terug op de cirkels hierboven als de maat niet klopt. */
    try
    {
        var rw = div.offsetWidth;
        var rh = div.offsetHeight;
        if (rw > 0 && rh > 0)
        {
            var y0 = this._b2PageY();
            var rect = { x0 : div.offsetLeft, y0 : div.offsetTop + y0, x1 : div.offsetLeft + rw, y1 : div.offsetTop + y0 + rh };
            coin.normalHitArea = { rect : rect, x : rect.x0 + rw / 2, y : rect.y0 + rh / 2, r2 : 0 };
            coin.focusHitArea = coin.normalHitArea;
        }
    }
    catch (e)
    {
        this._b2Log("_computeHitAreas", e);
    }

    coin.currentHitArea = coin.normalHitArea;
}

MainMenuCtrl.prototype._mouseDown = function(evt)
{
    if (this._allowInput)
    {
        var index = this._hitTestEvent(evt);
        if (index !== -1)
        {
            if (this._getFocus() == -1)
            {
                framework.common.stealFocus();
            }
            // Install mousemove / mouseup handlers to implement touch-move behavior.
            document.body.addEventListener("mousemove", this._mouseMoveCallback);
            document.body.addEventListener("mouseup", this._mouseUpCallback);

            this._setFocus(index);
            this._setHighlight(index);
        }
    }
};

MainMenuCtrl.prototype._mouseUp = function(evt)
{
    document.body.removeEventListener("mousemove", this._mouseMoveCallback);
    document.body.removeEventListener("mouseup", this._mouseUpCallback);

    var index = this._hitTestEvent(evt, true);
    if (index === -1)
    {
        // Also test the normal hit area for the two side coins because these coins move when focussed.
        // This avoids the scenario where the user touches the coin, it gets focus and expands, but upon touch-release
        // the hit test doesn't return a hit and we don't change contexts.
        var f = this._getFocus();
        if (f === 0 || f === 4)
        {
            var hitArea = this._coins[f].normalHitArea;
            if (this._hitTestHelper(evt.x, evt.y, hitArea))
            {
                index = f;
            }
        }
    }

    if (index !== -1)
    {
        framework.common.beep("Short", "Touch");
        this._invokeSelectCallback(index);
    }
};

MainMenuCtrl.prototype._mouseMove = function(evt)
{
    var index = this._hitTestEvent(evt);
    if (index !== -1)
    {
        // User is touching a coin so move focus and highlight
        this._setFocus(index);
        this._setHighlight(index);
    }
};

// Perform a hit test of the given mouse event and return the index of the coin hit, or -1 if no hit.
MainMenuCtrl.prototype._hitTestEvent = function(evt)
{
    var hitIndex = -1;
    var order = [0, 4, 1, 2, 3]; // We test the outside coins first because they overlap the three middle coins.
    for (var i = 0; i < order.length; ++i)
    {
        var hitArea = this._coins[ order[i] ].currentHitArea;

        if (this._hitTestHelper(evt.pageX, evt.pageY, hitArea))
        {
            hitIndex = order[i];
            break;
        }
    }

    /* OEMPLUS-B2: tik op het contextvak rechts = het item dat focus heeft */
    if (hitIndex === -1)
    {
        try
        {
            var f = this._getFocus();
            var x = evt.pageX;
            var y = evt.pageY - this._b2PageY();   // y binnen MainMenuCtrl (v1.1: = pagina-y, control staat op 0)
            if (f !== -1 && x >= 410 && x <= 790 && y >= 188 && y <= 474)   /* v1.2-fix B1: exact het zichtbare vak y 188-474 (v1.2 had 178-478; v1.1: 132-432) */
            {
                hitIndex = f;
            }
        }
        catch (e)
        {
            this._b2Log("_hitTestEvent", e);
        }
    }
    return hitIndex;
};

MainMenuCtrl.prototype._hitTestHelper = function(x, y, hitArea)
{
    /* OEMPLUS-B2 */
    if (hitArea && hitArea.rect)
    {
        return (x >= hitArea.rect.x0 && x < hitArea.rect.x1 && y >= hitArea.rect.y0 && y < hitArea.rect.y1);
    }
    var dx = x - hitArea.x;
    var dy = y - hitArea.y;
    var distance = dx * dx + dy * dy;
    return (distance < hitArea.r2);
};

// Sets the hightlight to the coin with the given index and removes it from all other coins.
// Call this with an invalid index such as -1 to clear the visible highlight effects from the screen.
MainMenuCtrl.prototype._setHighlight = function(index)
{
    if (this._fullyHighlightedIndex !== index)
    {
        this._fullyHighlightedIndex = null;

        if (index === -1)
        {
            this._prvFocus = this._getFocus();
        }
        else
        {
            this._prvFocus = -1;
        }

        var name = "";
        for (var i = 0; i < this._coins.length; i++)
        {
            if (i === index)
            {
                this._coins[i].div.classList.add("MainMenuCtrlCoinFocus");
                this._coins[i].highlight.classList.add("Visible");
                this._coins[i].currentHitArea = this._coins[i].focusHitArea;
                name = framework.localize.getLocStr(this.uiaId, this._coins[i].nameId);
            }
            else if (this._coins[i].highlight.style.opacity !== "0")
            {
                this._coins[i].div.classList.remove("MainMenuCtrlCoinFocus");
                this._coins[i].highlight.classList.remove("Visible");
                this._coins[i].currentHitArea = this._coins[i].normalHitArea;
            }
        }

        if ( name != "")
        {
            // TODO: workaround for remoteUI text. Do not override with blank text
            this._iconNameDiv.innerHTML = name;
        }

        /* OEMPLUS-B2: contextvak dat nu zichtbaar wordt bijwerken */
        this._b2Refresh(index);
    }
};

MainMenuCtrl.prototype.setText = function(text)
{
    this._iconNameDiv.innerHTML = text;
};

// TODO: Workaround: Add better logic involving common. Focus should not be gained by app iteself mutually. Can be given by common (handleControllerEvents) or stolen (stealFocus).
// This restores the focus on the previous icon, if carPlay had focus before and was removed.
MainMenuCtrl.prototype.getRemoteUiButtonStatus = function(enabled)
{
    if(!enabled && this._iconNameDiv.innerHTML != name && this._prvFocus != -1)
    {
        this._setHighlight(this._prvFocus) ;
    }
};

// Called when the focus animation on a coin ends.
MainMenuCtrl.prototype._setHighlightEnd = function(index, evt)
{
    if (evt.currentTarget.classList.contains("MainMenuCtrlCoinFocus"))
    {
        this._fullyHighlightedIndex = index;
        if (this._pendingInvokeSelectIndex !== null)
        {
            log.debug("_setHighlightEnd: invoking pending select callback on index " + this._pendingInvokeSelectIndex);
            var tmp = this._pendingInvokeSelectIndex;
            this._pendingInvokeSelectIndex = null;
            this._invokeSelectCallback(tmp);
        }
    }
};

// Return the index of the coin that currently has focus.
MainMenuCtrl.prototype._getFocus = function()
{
    for (var i = 0; i < this._coins.length; i++)
    {
        if (this._coins[i].hasFocus)
        {
            return i;
        }
    }
    return -1;
};

// Set focus to the coin with the given index.
MainMenuCtrl.prototype._setFocus = function(index)
{
    for (var i = 0; i < this._coins.length; i++)
    {
        this._coins[i].hasFocus = (i === index);
    }
};

// Invoke the select callback to the application.
MainMenuCtrl.prototype._invokeSelectCallback = function(index)
{
    if (0 <= index && index < 5)
    {
        // Temporarily block input to allow time for a context change transition.
        // ** DO NOT **  block input indefinitely in case MMUI does not send a context change.
        if (this._allowInput)
        {
            this._allowInput = false;
            this._allowInputTimerId = setTimeout(function(){
                this._allowInput = true;
                this._allowInputTimerId = null;
            }.bind(this), 1000);
        }

        if (index === this._fullyHighlightedIndex)
        {
            this._hasInvokedSelectCallback = true;
            if (this.properties.selectCallback)
            {
                var icon = this._coins[index].key.toLowerCase();
                this.properties.selectCallback(this, this.properties.appData, { "icon" : icon });
            }
        }
        else
        {
            log.info("_invokeSelectCallback: Select callback delayed because coin is not fully highlighted yet.");
            this._pendingInvokeSelectIndex = index;
        }
    }
};

// A support function to move the focus left or right from the current focus position. Pass -1 to move left, pass +1 to move right.
MainMenuCtrl.prototype._offsetFocus = function(direction)
{
    var index = this._getFocus();
    index += direction;

    if (index < 0)
    {
        index = 0;
    }
    if (index > 4)
    {
        index = 4;
    }

    if (index !== this._getFocus())
    {
        this._setFocus(index);
        this._setHighlight(index);
    }
};

// Start a timer while the user holds tilt.
MainMenuCtrl.prototype._startTiltHoldTimer = function()
{
    this._cancelFastTilt();

    // Only start the fast tilt hold timer if fast-tilting would have any effect from the current focus position.
    if ((this._fastTiltDirection === -1 && this._getFocus() > 0) ||
        (this._fastTiltDirection === 1 && this._getFocus() < 4))
    {
        this._tiltHoldTimerId = setTimeout(this._startFastTiltInterval.bind(this), this.properties.tiltHoldTime);
    }
};

// Invoked when the user holds tilt long enough to start fast tilting.
MainMenuCtrl.prototype._startFastTiltInterval = function()
{
    framework.common.beep("Long", "Multicontroller");
    this._tiltHoldTimerId = null;
    this._fastTiltStep();
    this._fastTiltStepIntervalId = setInterval(this._fastTiltStep.bind(this), this.properties.tiltStepTime);
};

// Cancels all fast-tilt or tilt-hold timers.
MainMenuCtrl.prototype._cancelFastTilt = function()
{
    clearTimeout(this._tiltHoldTimerId);
    clearInterval(this._fastTiltStepIntervalId);

    this._tiltHoldTimerId = null;
    this._fastTiltStepIntervalId = null;
};

// Periodic interval invoked during fast tilting.
MainMenuCtrl.prototype._fastTiltStep = function()
{
    this._offsetFocus(this._fastTiltDirection);
};

// Handle multicontroller events.
MainMenuCtrl.prototype.handleControllerEvent = function(eventId)
{
    var response = "consumed";
    switch(eventId)
    {
        case "lostFocus":
            this._setHighlight(-1);
            response = "consumed";
            break;

        case "acceptFocusInit": // intentional fall through
        case "acceptFocusFromTop":
            if (this._prvFocus != -1)
            {
                this._setHighlight(this._prvFocus) ;
            }
            else if (this._getFocus() != -1)
            {
                this._setHighlight(this._getFocus()) ;
            }
            else
            {
                // set default focus - communication // remove hardcoding later
                this._setHighlight(2) ;
            }
            break;

        case "ccw":
            if (this._allowInput)
            {
                this._offsetFocus(-1);
            }
            break;

        case "cw":
            if (this._allowInput)
            {
                this._offsetFocus(1);
            }
            break;

        case "leftStart":
            if (this._allowInput)
            {
                this._lastControllerStartEvent = eventId;
                this._fastTiltDirection = -1;
                this._offsetFocus(this._fastTiltDirection);
                this._startTiltHoldTimer();
            }
            break;

        case "left":
            if (this._allowInput && this._lastControllerStartEvent === "leftStart")
            {
                this._cancelFastTilt();
            }
            this._lastControllerStartEvent = "";
            break;

        case "rightStart":
            if (this._allowInput)
            {
                this._lastControllerStartEvent = eventId;
                this._fastTiltDirection = 1;
                this._offsetFocus(this._fastTiltDirection);
                this._startTiltHoldTimer();
            }
            break;

        case "right":
            if (this._allowInput && this._lastControllerStartEvent === "rightStart")
            {
                this._cancelFastTilt();
            }
            this._lastControllerStartEvent = "";
            break;

        case "selectStart":
            if (this._allowInput)
            {
                this._lastControllerStartEvent = eventId;
                this._setHighlight(this._getFocus());
            }
            break;

        case "select":
            if (this._allowInput && this._lastControllerStartEvent === "selectStart")
            {
                this._invokeSelectCallback(this._getFocus());
            }
            this._lastControllerStartEvent = "";
            break;
        case "upStart":
            if (this._allowInput)
            {
                this._lastControllerStartEvent = "";
                response = "giveFocusUp";
            }
            break;

        case "up":
            // do nothing
            break;
        default:
            // do nothing
            // throws many warnings. Made debug for now. // change once have consistent multicontroller event handeling acrross common
            log.debug("MainMenuCtrl.handleControllerEvent - event " + eventId + " is not handled. Sending response ignored");
            response = "ignored";
            break;
    }

    return response;
};

MainMenuCtrl.prototype.startTransitionFrom = function()
{
    /* OEMPLUS-B2: statusbalk weer tonen zodra home wegschuift */
    this._b2SetHomeClass(false);

    if (this._hasInvokedSelectCallback)
    {
        var index = this._getFocus();
        switch (index)
        {
            case 0: // fallthrough
            case 4:
                this._coins[index].div.classList.add("MainMenuCtrlCoinAExplode");
                this._coins[index].highlight.classList.add("MainMenuCtrlHighlightExplode");
                break;

            case 1: // fallthrough
            case 2: // fallthrough
            case 3:
                this._coins[index].div.classList.add("MainMenuCtrlCoinBExplode");
                this._coins[index].highlight.classList.add("MainMenuCtrlHighlightExplode");
                break;

            default:
                break;
        }
    }
};

MainMenuCtrl.prototype.endTransitionTo = function()
{
    this._iconNameDiv.classList.add("Visible");
    /* OEMPLUS-B2 */
    this._b2SetHomeClass(true);
};

MainMenuCtrl.prototype.getContextCapture = function()
{
    var capture = {};
    capture.focusedIcon = this._getFocus();
    log.debug("MainMenuCtrl.prototype.getContextCapture " + capture.focusedIcon);
    return capture;
};

MainMenuCtrl.prototype.restoreContext = function(capture)
{
    if (capture && typeof capture.focusedIcon === "number")
    {
        this._setFocus(capture.focusedIcon);
        log.debug("MainMenuCtrl.prototype.restoreContext " + capture.focusedIcon);
    }
};

MainMenuCtrl.prototype.finishPartialActivity = function()
{
    this._cancelFastTilt();

    /* OEMPLUS-B2 */
    this._b2Stop();

    // Null out the selectCallback to prevent any inadvertant callbacks while/after this template is destroyed.
    this.properties.selectCallback = null;
};

MainMenuCtrl.prototype.cleanUp = function()
{
    // delete obj reference
    delete this.properties;

    document.body.removeEventListener("mousemove", this._mouseMoveCallback);
    document.body.removeEventListener("mousedown", this._mouseDownCallback);
    document.body.removeEventListener("mouseup", this._mouseUpCallback);

    for (var i = 0; i < this._coins.length; i++)
    {
        this._coins[i].div.removeEventListener('OTransitionEnd', this._coins[i].setHighlightEndBinder);
    }

    if (this._allowInputTimerId)
    {
        clearTimeout(this._allowInputTimerId);
        this._allowInputTimerId = null;
    }

    this._cancelFastTilt();

    /* OEMPLUS-B2 */
    this._b2Stop();
};

/* ======================================================================================
 * OEMPLUS-B2 v1 -- contextvak-logica. ES5 only (Presto 2.12), alles in try/catch.
 * Data in v1 (alleen wat systemApp al ontvangt, doorgegeven via systemApp._oemplusB2Note):
 *   StatusUpdateMissedCallCount  payload.missedCallCount
 *   StatusUpdateNotifications    payload.messageCounts.countSMS / countEmail
 *   StatusUpdateAudioSource      payload.statusAudio.audioSource / audioActive
 *   StatusUpdateSchedMaint       payload.due (boolean)
 * Statusbalk-status (bereik/batterij/BT) wordt alleen GELEZEN uit framework.common.statusBar.
 * ====================================================================================== */

MainMenuCtrl.prototype._B2_ROWS = {
    "App" : { hd : "APPLICATIES",  desc : "Voertuig, apps<br>en meldingen",   label : "Applicaties" },
    "Ent" : { hd : "AUDIO",        desc : "Radio, USB en<br>Bluetooth-audio",  label : "Entertainment" },
    "Com" : { hd : "TELEFOON",     desc : "Bellen, berichten<br>en contacten", label : "Communicatie" },
    "Nav" : { hd : "NAVIGATIE",    desc : "Bestemming,<br>route en kaart",     label : "Navigatie" },
    "Set" : { hd : "INSTELLINGEN", desc : "Display, geluid<br>en systeem",     label : "Instellingen" }
};

// audioSource -> [stringId in systemApp-dictionary, terugval]
MainMenuCtrl.prototype._B2_SOURCES = {
    "FMRadio" : ["FmRadio", "FM-radio"],
    "AMRadio" : ["AmRadio", "AM-radio"],
    "DAB" : ["DabRadio", "DAB-radio"],
    "BTAudio" : ["Bluetooth", "Bluetooth-audio"],
    "USB_A" : ["UsbAudioA", "USB 1"],
    "USB_B" : ["UsbAudioB", "USB 2"],
    "USBAudio" : ["", "USB"],
    "AuxIn" : ["AuxIn", "AUX"],
    "CD" : ["CdPlayer", "CD"],
    "DVD" : ["DVDItem", "DVD"],
    "TV" : ["TVItem", "TV"],
    "Pandora" : ["Pandora", "Pandora"],
    "Stitcher" : ["StitcherItem", "Stitcher"],
    "AhaRadio" : ["AhaRadio", "Aha Radio"],
    "SatRadio" : ["SdarsRadio", "Satellietradio"],
    "XmAudio" : ["XMAudio", "XM"],
    "CarPlay" : ["", "Apple CarPlay"],
    "CarPlayWifi" : ["", "Apple CarPlay"],
    "AndroidAuto" : ["", "Android Auto"],
    "TrafficInfo" : ["TrafficAlertsItem", "Verkeersinformatie"]
};

MainMenuCtrl.prototype._B2_DAYS = ["zondag", "maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag"];
MainMenuCtrl.prototype._B2_MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"];

MainMenuCtrl.prototype._b2Log = function(where, e)
{
    try
    {
        log.warn("OEMPLUS-B2 " + where + ": " + (e && e.message ? e.message : e));
    }
    catch (e2)
    {
    }
};

MainMenuCtrl.prototype._b2El = function(parent, cls, html)
{
    var el = document.createElement('div');
    el.className = cls;
    if (html)
    {
        el.innerHTML = html;
    }
    if (parent)
    {
        parent.appendChild(el);
    }
    return el;
};

MainMenuCtrl.prototype._b2Text = function(el, text)
{
    if (el)
    {
        text = (text === null || text === undefined) ? "" : String(text);
        if (el.textContent !== text)
        {
            el.textContent = text;
        }
    }
};

MainMenuCtrl.prototype._b2Loc = function(stringId, fallback)
{
    try
    {
        if (stringId)
        {
            var s = framework.localize.getLocStr(this.uiaId, stringId);
            if (s && s !== stringId && s.indexOf(":" + stringId) === -1)
            {
                return s;
            }
        }
    }
    catch (e)
    {
    }
    return fallback;
};

// Bouwt per item: icoon + label in Normal en Highlight, en het contextvak in Focus.
MainMenuCtrl.prototype._b2BuildRow = function(i, focusDiv, normalDiv, highlightDiv)
{
    try
    {
        var key = this._coins[i].key;
        var row = this._B2_ROWS[key];
        var label = this._b2Loc(this._coins[i].nameId, row.label);
        var els = {};

        this._b2El(normalDiv, "MainMenuCtrlB2RowIcon");
        this._b2Text(this._b2El(normalDiv, "MainMenuCtrlB2RowLabel"), label);
        this._b2El(highlightDiv, "MainMenuCtrlB2RowIcon");
        this._b2Text(this._b2El(highlightDiv, "MainMenuCtrlB2RowLabel"), label);

        // kop van het vak
        var hd = this._b2El(focusDiv, "B2Hd");
        els.hdIcon = this._b2El(hd, "B2HdIcon");
        els.hdIcon.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/Hd" + key + ".png)";
        els.hdText = this._b2El(hd, "B2HdText");
        this._b2Text(els.hdText, row.hd);

        // statisch deel (App, Nav en terugval): groot icoon + omschrijving
        var st = this._b2El(focusDiv, "B2Static");
        var big = this._b2El(st, "B2Big");
        big.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/Big" + key + ".png)";
        this._b2El(st, "B2Desc", row.desc);
        this._b2El(st, "B2Rule");
        this._b2Text(this._b2El(st, "B2Note"), "Druk of tik om te openen");

        // dynamisch deel (v1: Ent, Com, Set; v1.5: ook App met de rijstijl-regel uit de live-data)
        if (key === "Ent" || key === "Com" || key === "Set" || key === "App")
        {
            var dy = this._b2El(focusDiv, "B2Dyn");
            els.hero = this._b2El(dy, "B2Hero");
            var sub = this._b2El(dy, "B2Sub");
            els.subIcon = this._b2El(sub, "B2SubIcon");
            els.subText = this._b2El(sub, "B2SubText");
            this._b2El(dy, "B2Rule");

            if (key === "Com")
            {
                // bereik + batterij gespiegeld uit de statusbalk (zelfde PNG's), i.p.v. de B2Sub-regel
                sub.style.display = "none";
                var sb = this._b2El(dy, "B2SbIcons");
                els.sbSig = this._b2El(sb, "B2SbSig");
                els.sbBatt = this._b2El(sb, "B2SbBatt");
                els.num1 = this._b2El(dy, "B2Num B2C1");
                this._b2Text(this._b2El(dy, "B2NumLbl B2C1L"), "GEMIST");
                this._b2Text(this._b2El(dy, "B2NumSub B2C1L"), "oproepen");
                els.num2 = this._b2El(dy, "B2Num B2C2");
                this._b2Text(this._b2El(dy, "B2NumLbl B2C2L"), "BERICHTEN");
                this._b2Text(this._b2El(dy, "B2NumSub B2C2L"), "ongelezen");
                // Com toont altijd het dynamische vak (tellers met een streepje als er nog niets binnen is)
                focusDiv.classList.add("B2HasData");
                this._b2Text(els.hero, "Telefoon");
                this._b2Text(els.num1, "\u2013");
                this._b2Text(els.num2, "\u2013");
            }
            else if (key === "App")
            {
                /* v1.5 punt 7 (de gebruiker 2026-11-27): contextvak bij Applicaties toont de rijstijl-regel:
                 * "Rijstijl 8,6 \u25b2" (vorige rit) of "Rit 12 km \u00b7 9/11 soepel" (lopend); verborgen zonder data.
                 * Leeg bij eerste start (nog geen live frame) -> B2HasData pas bij echte data (zie _b2UpdateRit). */
                this._b2Text(this._b2El(dy, "B2NumLbl B2C1"), "RIJSTIJL");
                els.ritLine = this._b2El(dy, "B2RitLine");
                this._b2Text(els.ritLine, "\u2013");
            }
            else
            {
                // onderblok: klein label + omschrijving van wat drukken opent
                this._b2Text(this._b2El(dy, "B2NumLbl B2C1"), "OPENT");
                els.note = this._b2El(dy, "B2Open");
                this._b2Text(els.note, label + (key === "Ent" ? " \u00b7 radio, USB, Bluetooth" : " \u00b7 display, geluid, systeem"));
            }
        }
        els.box = focusDiv;
        els.hdDefault = row.hd;
        els.hdIconDefault = els.hdIcon.style.backgroundImage;
        this._b2.els[key] = els;
    }
    catch (e)
    {
        this._b2Log("_b2BuildRow", e);
    }
};

// Pagina-y van de bovenkant van MainMenuCtrl: TemplateWithStatus staat op 64, MainMenuCtrl daarbinnen op
// divElt.offsetTop (v1.1: -64 -> 0). Terugval 64 + 0 = de stock-aanname "onder de statusbalk".
MainMenuCtrl.prototype._b2PageY = function()
{
    var y = 64;
    try
    {
        if (this.divElt && typeof this.divElt.offsetTop === "number")
        {
            y = 64 + this.divElt.offsetTop;
        }
    }
    catch (e)
    {
    }
    return y;
};

// OEMPLUS-B2 v1.1: statusbalk-containers die in de kop gespiegeld worden (links -> rechts) en de prioriteit
// waarmee ze plek krijgen (max 4 tegelijk; ontbrekend/verborgen in de statusbalk = icoon weg).
MainMenuCtrl.prototype._B2_STAT_ORDER = ["Traffic", "Roaming", "Message", "WifiSignal", "Bluetooth", "Batt"];
MainMenuCtrl.prototype._B2_STAT_PRIO = ["Batt", "Bluetooth", "Message", "Roaming", "WifiSignal", "Traffic"];
MainMenuCtrl.prototype._B2_STAT_MAX = 4;

MainMenuCtrl.prototype._b2BuildHeader = function()
{
    try
    {
        this._b2El(this.divElt, "MainMenuCtrlB2Divider");
        this._b2.els.clock = this._b2El(this.divElt, "MainMenuCtrlB2Clock");
        this._b2.els.date = this._b2El(this.divElt, "MainMenuCtrlB2Date");
        this._b2El(this.divElt, "MainMenuCtrlB2TopRule");
        var stat = this._b2El(this.divElt, "MainMenuCtrlB2Stat");
        this._b2.els.stat = {};
        for (var i = 0; i < this._B2_STAT_ORDER.length; i++)
        {
            var name = this._B2_STAT_ORDER[i];
            var ic = this._b2El(stat, "B2StatIcon");
            ic.id = "OemplusB2Stat_" + name;
            this._b2.els.stat[name] = ic;
        }
    }
    catch (e)
    {
        this._b2Log("_b2BuildHeader", e);
    }
};

MainMenuCtrl.prototype._b2Start = function()
{
    try
    {
        this._b2UpdateClock();
        this._b2.clockTimerId = setInterval(this._b2UpdateClock.bind(this), 5000);
        // statusbalk-iconen (bereik/batterij) spiegelen; goedkoop, alleen schrijven bij verandering
        this._b2.sbTimerId = setInterval(this._b2UpdateSbIcons.bind(this), 3000);

        // eerder ontvangen v1-berichten (systemApp bewaart de laatste payload per bericht)
        var sys = framework.getAppInstance("system");
        var cache = sys ? sys._oemplusB2Data : null;
        if (cache)
        {
            var self = this;
            var replay = function (name)
            {
                try { self.oemplusB2Update(name, cache[name]); } catch (eR) { self._b2Log("replay " + name, eR); }
            };
            for (var name in cache)
            {
                if (cache.hasOwnProperty(name))
                {
                    replay(name);
                }
            }
        }
        /* OEMPLUS-B2 v1.2: MMUI stuurt de statusberichten pas opnieuw bij de volgende wijziging, dus bij 'B2 aan'
         * direct de GECACHETE state van systemApp lezen (alleen lezen, niets schrijven): zie _b2SeedFromSystem.
         * Fix B3: de seed krijgt de cache mee en overschrijft NOOIT wat al in de cache staat (de replay hierboven
         * heeft immers de echte audiostatus al gezet). */
        this._b2SeedFromSystem(sys, cache);
        this._b2UpdateSbIcons();
        /* Fix B2: de watcher in EIGEN try, VOOR de home-klasse: gooit iets ervoor, dan is body.OemplusB2Home gezet
         * zonder watcher, maar de verborgen SBN-startpositie hangt af van B2SbnWatch (niet van OemplusB2Home),
         * dus de banner is dan gewoon zichtbaar (fail-visible). */
        try
        {
            this._b2WatchSbn();
        }
        catch (eW)
        {
            this._b2Log("_b2WatchSbn", eW);
            this._b2SbnWatch(false);
        }
        this._b2SetHomeClass(true);
    }
    catch (e)
    {
        this._b2Log("_b2Start", e);
        this._b2SbnWatch(false);
    }
};

MainMenuCtrl.prototype._b2Stop = function()
{
    try
    {
        if (this._b2)
        {
            clearInterval(this._b2.clockTimerId);
            clearInterval(this._b2.sbTimerId);
            clearInterval(this._b2.sbnTimerId);
            this._b2.clockTimerId = null;
            this._b2.sbTimerId = null;
            this._b2.sbnTimerId = null;
        }
        this._b2SbnWatch(false);   /* v1.2-fix B2: watcher-klasse weg -> SBN niet meer verborgen startpositie */
        this._b2SetHomeClass(false);
    }
    catch (e)
    {
        this._b2Log("_b2Stop", e);
    }
};

/* OEMPLUS-B2 v1.2: vult de contextpanelen uit de gecachete systemApp-state (aangeroepen in _b2Start). Alleen LEZEN
 * uit systemApp; niets wordt geschreven.
 * Fix B3 (review V3): "cache" = sys._oemplusB2Data (de berichten die VOOR deze aanroep al zijn gereplayd). Per paneel
 * wordt ALLEEN geseed als het bijbehorende bericht NIET in de cache staat -- de seed mag nooit betere (echte) data
 * uit de cache overschrijven (v1.2 zette Ent altijd op "Actieve bron"/Pause.png, ook als StatusUpdateAudioSource al
 * "Speelt nu" had gezet). Fix B6: per paneel een eigen try/catch. Fix B5: Set toont "In orde" alleen als er echt
 * data is (image2 expliciet een string, of _SchedMaintDueStatus een boolean) -- anders blijft het vak statisch.
 * Bronnen (v74 systemApp.js): _communicationsDataList label1 per mmuiEvent (r.1425-1463, 1700-1730),
 * _masterApplicationDataList image2 SelectSchedMaint + _SchedMaintDueStatus (r.1795-1815),
 * _masterEntertainmentDataList image1 IcnListEntNowPlaying = actieve audiobron (r.1556-1599). */
MainMenuCtrl.prototype._b2SeedFromSystem = function(sys, cache)
{
    if (!sys)
    {
        return;
    }
    var has = function (name)
    {
        return !!(cache && cache.hasOwnProperty && cache.hasOwnProperty(name));
    };

    /* --- Com: tellers uit _communicationsDataList, ALLEEN als er geen StatusUpdate-bericht in de cache staat --- */
    try
    {
        var com = this._b2.els.Com;
        if (com && !has("StatusUpdateNotifications") && !has("StatusUpdateMissedCallCount") &&
            sys._communicationsDataList && sys._communicationsDataList.items)
        {
            var items = sys._communicationsDataList.items;
            var tot = null, missed = null;
            for (var i = 0; i < items.length; i++)
            {
                var ev = items[i].appData ? items[i].appData.mmuiEvent : null;
                var l1 = items[i].label1;
                if (ev === "SelectNotifications")
                {
                    tot = (l1 === "" || l1 === null || l1 === undefined) ? 0 : this._b2Count(l1);
                }
                else if (ev === "SelectCallHistory")
                {
                    missed = (l1 === "" || l1 === null || l1 === undefined) ? 0 : this._b2Count(l1);
                }
            }
            if (tot !== null && com.num2)
            {
                this._b2Text(com.num2, tot);
                com.num2.className = "B2Num B2C2" + ((tot === 0) ? " B2Zero" : "");
            }
            if (missed !== null && com.num1)
            {
                this._b2Text(com.num1, missed);
                com.num1.className = "B2Num B2C1" + ((missed === 0) ? " B2Zero" : "");
            }
        }
    }
    catch (eCom)
    {
        this._b2Log("_b2SeedFromSystem Com", eCom);
    }

    /* --- Set: onderhoud, ALLEEN als er geen StatusUpdateSchedMaint in de cache staat en er echte data is (fix B5) --- */
    try
    {
        var set = this._b2.els.Set;
        if (set && !has("StatusUpdateSchedMaint"))
        {
            var due = null;
            if (typeof sys._SchedMaintDueStatus === "boolean")
            {
                due = sys._SchedMaintDueStatus;
            }
            else if (sys._masterApplicationDataList && sys._masterApplicationDataList.items)
            {
                var apps = sys._masterApplicationDataList.items;
                for (var j = 0; j < apps.length; j++)
                {
                    if (apps[j].appData && apps[j].appData.mmuiEvent === "SelectSchedMaint")
                    {
                        /* fix B5: zonder _SchedMaintDueStatus-boolean is image2 initieel "" (ook na due=false),
                         * dus alleen een NIET-LEGE string telt als data (due=true); anders blijft het vak statisch
                         * en toont het nooit "In orde" zonder ooit een bericht te hebben gehad. */
                        if (typeof apps[j].image2 === "string" && apps[j].image2 !== "")
                        {
                            due = true;
                        }
                        break;
                    }
                }
            }
            if (due !== null)
            {
                this._b2Text(set.hdText, "ONDERHOUD");
                set.hdIcon.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/HdWrench.png)";
                this._b2Text(set.hero, due ? "Onderhoud nodig" : "In orde");
                this._b2Text(set.subText, due ? "Gepland onderhoud is bereikt" : "Geen gepland onderhoud nodig");
                set.subIcon.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/" + (due ? "Due" : "Ok") + ".png)";
                set.box.classList.add("B2HasData");
            }
        }
    }
    catch (eSet)
    {
        this._b2Log("_b2SeedFromSystem Set", eSet);
    }

    /* --- Ent: actieve audiobron, ALLEEN als er geen StatusUpdateAudioSource in de cache staat (fix B3) --- */
    try
    {
        var ent = this._b2.els.Ent;
        if (ent && !has("StatusUpdateAudioSource") &&
            sys._masterEntertainmentDataList && sys._masterEntertainmentDataList.items)
        {
            var ents = sys._masterEntertainmentDataList.items;
            for (var k = 0; k < ents.length; k++)
            {
                if (ents[k].image1 && String(ents[k].image1).indexOf("IcnListEntNowPlaying") !== -1)
                {
                    var src = ents[k].appData ? ents[k].appData.audioSourceId : null;
                    if (src && src !== "None")
                    {
                        var map = this._B2_SOURCES[src];
                        var label = map ? this._b2Loc(map[0], map[1]) : String(src);
                        this._b2Text(ent.hdText, "AUDIO");
                        ent.hdIcon.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/HdAudio.png)";
                        this._b2Text(ent.hero, label);
                        this._b2Text(ent.subText, "Actieve bron");
                        /* neutraal icoon bij "Actieve bron" (fix B3: geen Pause.png suggereren) */
                        ent.subIcon.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/HdAudio.png)";
                        ent.box.classList.add("B2HasData");
                    }
                    break;
                }
            }
        }
    }
    catch (eEnt)
    {
        this._b2Log("_b2SeedFromSystem Ent", eEnt);
    }
};

/* OEMPLUS-B2 v1.2-fix B2: watcher-klasse op body. Zolang deze klasse er is, mag de CSS de SBN-banner op de
 * verborgen startpositie top:-60px zetten (SbnCtrl-oemplusb2.css: body.OemplusB2.B2SbnWatch .SbnCtrl /
 * body.OemplusB2Home.B2SbnWatch .SbnCtrl).
 * Zonder watcher staat de banner ALTIJD op top:1px (fail-visible: een SBN is nooit onzichtbaar alleen omdat
 * de watcher niet draait of _b2Start faalde). */
MainMenuCtrl.prototype._b2SbnWatch = function(on)
{
    try
    {
        if (on)
        {
            document.body.classList.add("B2SbnWatch");
        }
        else
        {
            document.body.classList.remove("B2SbnWatch");
        }
    }
    catch (e)
    {
        this._b2Log("_b2SbnWatch", e);
    }
};

/* OEMPLUS-B2 v1.2: SBN-banner bewaken. De banner (SbnCtrl op document.body, x 59-685, y 1-59) moet binnen de
 * bovenste 64 px blijven; de B2-layout begint daaronder (klok y 71, rijen y 121). Zet B2SbnUp op de control als er
 * een SBN is en start de slide-in: de CSS zet de banner op top:-60px ZOLANG body.B2SbnWatch staat
 * (SbnCtrl-oemplusb2.css); hier wordt de klasse B2SbnIn toegevoegd zodat de -o-transition naar top:1px loopt.
 * Fix B2: de watcher zet zelf body.B2SbnWatch aan (pas in deze functie, in eigen scope) en _b2Stop haalt hem weg. */
MainMenuCtrl.prototype._b2WatchSbn = function()
{
    try
    {
        var self = this;
        if (this._b2.sbnTimerId)
        {
            return;
        }
        this._b2SbnWatch(true);
        this._b2.sbnTimerId = setInterval(function ()
        {
            try
            {
                var sbn = document.querySelector(".SbnCtrl");
                var has = !!sbn;
                if (has !== self._b2.sbnSeen)
                {
                    self._b2.sbnSeen = has;
                    if (self.divElt)
                    {
                        if (has)
                        {
                            self.divElt.classList.add("B2SbnUp");
                        }
                        else
                        {
                            self.divElt.classList.remove("B2SbnUp");
                        }
                    }
                }
                if (sbn && !sbn.classList.contains("B2SbnIn"))
                {
                    sbn.classList.add("B2SbnIn");
                }
            }
            catch (e2) { }
        }, 400);
    }
    catch (e)
    {
        this._b2SbnWatch(false);
        this._b2Log("_b2WatchSbn", e);
    }
};

// body-klasse: StatusBarCtrl.css verbergt dan de hele OEM-statusbalk (v1.1; AA/CarPlay-knop blijft), B2 toont klok + iconen zelf
MainMenuCtrl.prototype._b2SetHomeClass = function(on)
{
    try
    {
        if (on)
        {
            document.body.classList.add("OemplusB2Home");
        }
        else
        {
            document.body.classList.remove("OemplusB2Home");
        }
    }
    catch (e)
    {
        this._b2Log("_b2SetHomeClass", e);
    }
};

MainMenuCtrl.prototype._b2UpdateClock = function()
{
    try
    {
        var ms = 0;
        try
        {
            ms = framework.common.getCurrentTime();
        }
        catch (e1)
        {
            ms = 0;
        }
        var t = (typeof ms === "number" && ms > 0) ? new Date(ms) : new Date();
        var h = t.getHours();
        var m = t.getMinutes();
        if (isNaN(h) || isNaN(m))
        {
            return;
        }
        var fmt = "24hrs";
        try
        {
            fmt = framework.localize.getTimeFormat();
        }
        catch (e2)
        {
        }
        var hh = h;
        if (fmt == "12hrs")
        {
            hh = (h > 12) ? h - 12 : ((h === 0) ? 12 : h);
        }
        else
        {
            hh = (h > 9) ? h : "0" + h;
        }
        var clock = hh + ":" + (m > 9 ? m : "0" + m);
        var date = this._B2_DAYS[t.getDay()] + " " + t.getDate() + " " + this._B2_MONTHS[t.getMonth()];
        if (clock !== this._b2.lastClock)
        {
            this._b2.lastClock = clock;
            this._b2Text(this._b2.els.clock, clock);
        }
        if (date !== this._b2.lastDate)
        {
            this._b2.lastDate = date;
            this._b2Text(this._b2.els.date, date);
        }
    }
    catch (e)
    {
        this._b2Log("_b2UpdateClock", e);
    }
};

// Leest de status van de statusbalk-iconen (achtergrond-URL bevat de stand, bv. IcnSbPhoneSignal_03.png).
MainMenuCtrl.prototype._b2ReadSbIcon = function(container)
{
    var res = { visible : false, bg : "" };
    try
    {
        var sb = framework.common.statusBar;
        var div = (sb && sb._iconDivs) ? sb._iconDivs[container] : null;
        if (div)
        {
            var disp = div._display || div.style.display;
            res.bg = div.style.backgroundImage || "";
            res.visible = (disp && disp !== "none" && res.bg !== "" && res.bg !== "none") ? true : false;
        }
    }
    catch (e)
    {
    }
    return res;
};

// OEMPLUS-B2 v1.1: kop-iconen = spiegel van de (op home verborgen) statusbalk. Alleen schrijven bij verandering.
MainMenuCtrl.prototype._b2UpdateStatIcons = function()
{
    try
    {
        var st = this._b2.els.stat;
        if (!st)
        {
            return;
        }
        var want = {}, n = 0, i, name;
        for (i = 0; i < this._B2_STAT_PRIO.length; i++)
        {
            name = this._B2_STAT_PRIO[i];
            var r = this._b2ReadSbIcon(name);
            if (r.visible && n < this._B2_STAT_MAX)
            {
                want[name] = r.bg;
                n++;
            }
        }
        for (i = 0; i < this._B2_STAT_ORDER.length; i++)
        {
            name = this._B2_STAT_ORDER[i];
            var el = st[name];
            if (!el)
            {
                continue;
            }
            if (want.hasOwnProperty(name))
            {
                if (el.style.backgroundImage !== want[name])
                {
                    el.style.backgroundImage = want[name];
                }
                if (!el.classList.contains("B2On"))
                {
                    el.classList.add("B2On");
                }
            }
            else if (el.classList.contains("B2On"))
            {
                el.classList.remove("B2On");
            }
        }
    }
    catch (e)
    {
        this._b2Log("_b2UpdateStatIcons", e);
    }
};

MainMenuCtrl.prototype._b2UpdateSbIcons = function()
{
    this._b2UpdateStatIcons();
    try
    {
        var els = this._b2.els.Com;
        if (!els || !els.sbSig)
        {
            return;
        }
        var bt = this._b2ReadSbIcon("Bluetooth");   // container voor PhoneSignal / Bluetooth / Music
        var batt = this._b2ReadSbIcon("Batt");
        var sig = (bt.visible && bt.bg.indexOf("PhoneSignal") !== -1) ? bt.bg : "none";
        var bat = batt.visible ? batt.bg : "none";
        if (els.sbSig.style.backgroundImage !== sig)
        {
            els.sbSig.style.backgroundImage = sig;
        }
        if (els.sbBatt.style.backgroundImage !== bat)
        {
            els.sbBatt.style.backgroundImage = bat;
        }
        // Held: alleen "Verbonden" als de statusbalk een telefoonicoon toont; anders neutraal "Telefoon".
        this._b2Text(els.hero, (bt.visible || batt.visible) ? "Verbonden" : "Telefoon");
    }
    catch (e)
    {
        this._b2Log("_b2UpdateSbIcons", e);
    }
};

// Wordt aangeroepen bij focuswissel (index = nieuw focus-item of -1).
MainMenuCtrl.prototype._b2Refresh = function(index)
{
    try
    {
        if (index >= 0 && index < this._coins.length)
        {
            var k = this._coins[index].key;
            if (k === "Com")
            {
                this._b2UpdateSbIcons();
            }
            else if (k === "App")
            {
                this._b2UpdateRit();
            }
        }
    }
    catch (e)
    {
        this._b2Log("_b2Refresh", e);
    }
};

/* v1.5 punt 7: rijstijl-regel in het contextvak bij Applicaties (App). Bron: window.OemplusLive (als geladen).
 * Vorige rit (N): "Rijstijl 8,6 \u25b2" (trend t.o.v. de rit ervoor; \u25bc/\u2013 anders). Lopende rit (S):
 * "Rit 12 km \u00b7 9/11 soepel". Zonder data: verborgen (B2HasData eraf, regel "\u2013"). Alleen lezen. */
MainMenuCtrl.prototype._b2UpdateRit = function()
{
    try
    {
        var app = this._b2.els.App;
        if (!app || !app.ritLine) { return; }
        var L = window.OemplusLive;
        var st = L && L.status ? L.status() : null;
        var d = st && st.last;
        var txt = null;
        /* v1.5 review: vers = server age_s <= 5 EN lokaal laatste frame <= 5 s geleden (anders blijft oude tekst staan als de Pi wegvalt);
         * soepel/schakelingen = HELE rit (rit.soepel/rit.schakelingen), niet rit.recent (= laatste 2 min). */
        if (d && typeof d.age_s === "number" && d.age_s <= 5 && st && typeof st.rxAgeS === "number" && st.rxAgeS <= 5)
        {
            var rit = d.rit, vr = d.vorige_rit;
            if (rit && typeof rit.km === "number" && rit.km >= 0.5)
            {
                var sm = (typeof rit.soepel === "number" && typeof rit.schakelingen === "number" && rit.schakelingen > 0)
                    ? (rit.soepel + "/" + rit.schakelingen + " soepel") : null;
                txt = "Rit " + rit.km.toFixed(0) + " km" + (sm ? (" \u00b7 " + sm) : "");
            }
            else if (vr && typeof vr.cijfer === "number")
            {
                var arr = " \u25b2";
                if (Object.prototype.toString.call(vr.trend) === "[object Array]" && vr.trend.length >= 2 &&
                    typeof vr.trend[vr.trend.length - 2] === "number")
                {
                    var dd = vr.cijfer - vr.trend[vr.trend.length - 2];
                    arr = Math.abs(dd) < 0.05 ? " \u2013" : (dd > 0 ? " \u25b2" : " \u25bc");
                }
                txt = "Rijstijl " + vr.cijfer.toFixed(1).replace(".", ",") + arr;
            }
        }
        if (txt)
        {
            this._b2Text(app.ritLine, txt);
            app.box.classList.add("B2HasData");
        }
        else
        {
            this._b2Text(app.ritLine, "\u2013");
            app.box.classList.remove("B2HasData");
        }
    }
    catch (e)
    {
        this._b2Log("_b2UpdateRit", e);
    }
};

// Vak terug naar de statische variant (kop + groot icoon + omschrijving).
MainMenuCtrl.prototype._b2Static = function(els)
{
    els.box.classList.remove("B2HasData");
    this._b2Text(els.hdText, els.hdDefault);
    els.hdIcon.style.backgroundImage = els.hdIconDefault;
};

MainMenuCtrl.prototype._b2Count = function(n)
{
    var v = parseInt(n, 10);
    return (isNaN(v) || v < 0) ? null : v;
};

/*
 * (public, OEMPLUS-B2) Aangeroepen door systemApp._oemplusB2Note met de payload van een v1-bericht.
 * Ontbrekende of rare data -> vak blijft/wordt statisch; nooit een exception naar buiten.
 */
MainMenuCtrl.prototype.oemplusB2Update = function(name, payload)
{
    try
    {
        if (!this._b2 || !this._b2.els)
        {
            return;
        }
        this._b2.data[name] = payload;
        var els;
        switch (name)
        {
            case "StatusUpdateMissedCallCount":
                els = this._b2.els.Com;
                if (els && els.num1)
                {
                    var mc = payload ? this._b2Count(payload.missedCallCount) : null;
                    this._b2Text(els.num1, (mc === null) ? "\u2013" : mc);
                    els.num1.className = "B2Num B2C1" + ((mc === 0) ? " B2Zero" : "");
                }
                break;

            case "StatusUpdateNotifications":
                els = this._b2.els.Com;
                if (els && els.num2)
                {
                    var mcs = (payload && payload.messageCounts) ? payload.messageCounts : null;
                    var sms = mcs ? this._b2Count(mcs.countSMS) : null;
                    var mail = mcs ? this._b2Count(mcs.countEmail) : null;
                    var tot = (sms === null && mail === null) ? null : (sms || 0) + (mail || 0);
                    this._b2Text(els.num2, (tot === null) ? "\u2013" : tot);
                    els.num2.className = "B2Num B2C2" + ((tot === 0) ? " B2Zero" : "");
                }
                break;

            case "StatusUpdateAudioSource":
                els = this._b2.els.Ent;
                if (els && els.box)
                {
                    var sa = (payload && payload.statusAudio) ? payload.statusAudio : null;
                    var src = sa ? sa.audioSource : null;
                    if (!src || src === "None" || src === "Off")
                    {
                        this._b2Static(els);
                        break;
                    }
                    var map = this._B2_SOURCES[src];
                    var label = map ? this._b2Loc(map[0], map[1]) : String(src);
                    var act = sa.audioActive;
                    var stateText = "Gestopt";
                    var icon = "Pause";
                    if (act === "Play")
                    {
                        stateText = "Speelt nu";
                        icon = "Play";
                    }
                    else if (act === "Pause" || act === "Paused")
                    {
                        stateText = "Gepauzeerd";
                    }
                    this._b2Text(els.hdText, (act === "Play") ? "NU SPEELT" : "AUDIO");
                    els.hdIcon.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/HdAudio.png)";
                    this._b2Text(els.hero, label);
                    this._b2Text(els.subText, stateText);
                    els.subIcon.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/" + icon + ".png)";
                    els.box.classList.add("B2HasData");
                }
                break;

            case "StatusUpdateSchedMaint":
                els = this._b2.els.Set;
                if (els && els.box)
                {
                    if (!payload || (payload.due !== true && payload.due !== false))
                    {
                        this._b2Static(els);
                        break;
                    }
                    this._b2Text(els.hdText, "ONDERHOUD");
                    els.hdIcon.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/HdWrench.png)";
                    this._b2Text(els.hero, payload.due ? "Onderhoud nodig" : "In orde");
                    this._b2Text(els.subText, payload.due ? "Gepland onderhoud is bereikt" : "Geen gepland onderhoud nodig");
                    els.subIcon.style.backgroundImage = "url(apps/system/controls/MainMenu/images/b2/" + (payload.due ? "Due" : "Ok") + ".png)";
                    els.box.classList.add("B2HasData");
                }
                break;

            default:
                break;
        }
    }
    catch (e)
    {
        this._b2Log("oemplusB2Update(" + name + ")", e);
    }
};

framework.registerCtrlLoaded("MainMenuCtrl");
