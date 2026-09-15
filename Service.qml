import QtQuick
import Quickshell.Io
import qs.Commons
import "Model.js" as Model

Item {
    id: root
    property var shell: null
    property var manifest: null
    property var rows: []
    property var config: ({windowDays:14})
    property string home: ""
    property double lastScan: 0
    property string lastError: ""
    property string notice: ""
    property bool capped: false
    property bool initialized: false
    property bool refreshing: scanProcess.running
    property var xbelMarker: null
    property bool alive: true
    property bool glyphsSupported: false
    readonly property string fontFamily: Style.font.family
    onFontFamilyChanged: if (!glyphProcess.running) glyphProcess.running=true
    readonly property string helper: Qt.resolvedUrl("bin/recents-scan").toString().replace(/^file:\/\//, "")
    function refresh(scheduled) {
        if (!alive || scanProcess.running || cacheProcess.running) return
        scanProcess.command = ["timeout", "160s", decodeURIComponent(helper), scheduled ? "scheduled" : "scan"]
        scanProcess.running = true
    }
    function accept(text, code, cached) {
        if (!alive) return
        try {
            var result=JSON.parse(text)
            if (code!==0 || result.error) throw new Error(result.error || "Scan failed")
            if (result.skipped) { notice=result.notice; return }
            config=result.config || config
            home=result.home || home
            rows=Model.merge(result.rows || [],Date.now()/1000,config.windowDays)
            lastScan=result.scannedAt || 0
            xbelMarker=result.xbelMarker || null
            capped=!!result.capped
            notice=(result.notices || []).join(" · ")
            initialized=!cached || !!lastScan
            lastError=""
        } catch (e) { lastError=String(e).slice(0,240) }
    }
    function panelOpened() { if (Date.now()/1000-lastScan>60) refresh(false) }
    function removePaths(paths) { rows=rows.filter(function(r) { return paths.indexOf(r.path)<0 }) }
    Process {
        id: glyphProcess
        command: ["timeout","3s",decodeURIComponent(root.helper),"glyphs",root.fontFamily]
        stdout: StdioCollector { id: glyphOutput }
        onExited: function(code) { try { root.glyphsSupported=code===0 && JSON.parse(glyphOutput.text).supported } catch(e) { root.glyphsSupported=false } }
    }
    Process {
        id: cacheProcess
        command: ["timeout", "5s", decodeURIComponent(root.helper), "cached"]
        stdout: StdioCollector { id: cacheOutput }
        onExited: function(code) { root.accept(cacheOutput.text,code,true) }
    }
    Process {
        id: scanProcess
        stdout: StdioCollector { id: scanOutput }
        onExited: function(code) { root.accept(scanOutput.text,code,false) }
    }
    Process {
        id: pollProcess
        command: ["timeout", "3s", decodeURIComponent(root.helper), "poll"]
        stdout: StdioCollector { id: pollOutput }
        onExited: function(code) {
            if (!root.alive || code!==0) return
            try { if (JSON.stringify(JSON.parse(pollOutput.text).marker)!==JSON.stringify(root.xbelMarker)) root.refresh(true) } catch(e) {}
        }
    }
    Timer { interval:30000; running:true; onTriggered:root.refresh(true) }
    Timer { interval:300000; running:true; repeat:true; onTriggered:root.refresh(true) }
    Timer { interval:15000; running:root.initialized && !!root.config.sources && root.config.sources.xbel; repeat:true; onTriggered:if(!pollProcess.running && !root.refreshing) pollProcess.running=true }
    IpcHandler {
        target: "io.github.tcballard.recents"
        function refresh(): void { root.refresh(false) }
        function status(): string { return JSON.stringify({count:root.rows.length,refreshing:root.refreshing,lastScan:root.lastScan,error:!!root.lastError}) }
    }
    Component.onCompleted: { cacheProcess.running=true; glyphProcess.running=true }
    Component.onDestruction: { alive=false; glyphProcess.running=false; scanProcess.running=false; cacheProcess.running=false; pollProcess.running=false }
}
