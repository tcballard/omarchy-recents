import QtQuick
import QtQuick.Layouts
import Quickshell.Io
import qs.Commons
import qs.Ui as Ui
import "Model.js" as Model

Item {
    id: root
    objectName: "recents-panel"
    property var bar: null
    property var settings: ({})
    property var anchorItem: null
    property var hostWidget: null
    property var service: null
    property bool opened: false
    property bool popoutSwitchClosing: false
    property string query: ""
    property int typeIndex: 0
    property int sourceIndex: 0
    property int selected: 0
    property double now: Date.now()/1000
    property string pendingPath: ""
    property string message: ""
    property string detail: ""
    property int generation: 0
    property int checkGeneration: 0
    property int actionGeneration: 0
    property string actionPath: ""
    property string actionKind: ""
    readonly property var types: ["All","Docs","Images","Video","Audio","Archives","Code"]
    readonly property var sources: ["All","edited","opened","downloaded"]
    readonly property color foreground: Color.popups.text
    readonly property var rows: Model.select(service ? service.rows : [],query,types[typeIndex],sources[sourceIndex],now,service ? service.home : "")
    readonly property var current: rows.length ? rows[Math.max(0,Math.min(selected,rows.length-1))] : null
    readonly property string helper: decodeURIComponent(Qt.resolvedUrl("bin/recents-scan").toString().replace(/^file:\/\//,""))
    function open(payloadJson) {
        popoutSwitchClosing=false; opened=true; now=Date.now()/1000; generation++
        pendingPath=""; detail=""; message=""; search.forceActiveFocus()
        if (service) service.panelOpened()
        checkTimer.restart()
    }
    function close() { opened=false; pendingPath=""; confirmTimer.stop(); checkTimer.stop(); generation++; checkProcess.running=false }
    function closeForPopoutSwitch() { popoutSwitchClosing=true; close() }
    function move(delta) { selected=Math.max(0,Math.min(rows.length-1,selected+delta)); list.positionViewAtIndex(selected,ListView.Contain); list.forceActiveFocus() }
    function cycle(delta) { typeIndex=(typeIndex+delta+types.length)%types.length }
    function requestAction(kind) {
        if (!current || actionProcess.running) return
        if (kind==="trash" && pendingPath!==current.path) {
            pendingPath=current.path; message="Press d again within 2 seconds to move this file to Trash"; confirmTimer.restart(); return
        }
        pendingPath=""; confirmTimer.stop(); actionPath=current.path; actionKind=kind; actionGeneration=generation
        actionProcess.command=["timeout","20s",decodeURIComponent(Qt.resolvedUrl("bin/recents-act").toString().replace(/^file:\/\//,"")),kind,actionPath]
        actionProcess.running=true
    }
    function key(event,inSearch) {
        if (event.isAutoRepeat && event.key===Qt.Key_D) { event.accepted=true; return }
        if (event.key===Qt.Key_Escape) { if(pendingPath) {pendingPath="";message="";confirmTimer.stop()} else close() }
        else if (event.key===Qt.Key_Tab || event.key===Qt.Key_Backtab) cycle((event.modifiers & Qt.ShiftModifier) || event.key===Qt.Key_Backtab ? -1 : 1)
        else if (event.key===Qt.Key_Down) move(1)
        else if (event.key===Qt.Key_Up) move(-1)
        else if (event.key===Qt.Key_Return || event.key===Qt.Key_Enter) requestAction("open")
        else if (!inSearch && event.modifiers===Qt.NoModifier) {
            if (event.key===Qt.Key_J) move(1)
            else if (event.key===Qt.Key_K) move(-1)
            else if (event.key===Qt.Key_O) requestAction("reveal")
            else if (event.key===Qt.Key_Y) requestAction("copy-path")
            else if (event.key===Qt.Key_C) requestAction("copy-file")
            else if (event.key===Qt.Key_P) requestAction("copy-image")
            else if (event.key===Qt.Key_D) requestAction("trash")
            else if (event.key===Qt.Key_I) { if(detail) detail=""; else requestAction("details") }
            else if (event.key===Qt.Key_S) sourceIndex=(sourceIndex+1)%sources.length
            else if (event.key===Qt.Key_R) { if(service) service.refresh(false) }
            else if (event.key===Qt.Key_Slash) search.forceActiveFocus()
            else { event.accepted=false; return }
        } else { event.accepted=false; return }
        event.accepted=true
    }
    function checkVisible() {
        if (!opened || checkProcess.running || !rows.length) return
        var first=Math.max(0,list.indexAt(1,list.contentY))
        var paths=rows.slice(first,first+Math.min(100,Math.ceil(list.height/Style.space(58))+2)).map(function(r){return r.path})
        checkGeneration=generation
        checkProcess.command=["timeout","5s",helper,"check"]
        checkProcess.running=true
        checkProcess.write(JSON.stringify(paths)); checkProcess.stdinEnabled=false
    }
    onRowsChanged: { selected=Math.min(selected,Math.max(0,rows.length-1)); pendingPath=""; detail=""; if(opened) checkTimer.restart() }
    onSelectedChanged: { pendingPath=""; detail=""; message=""; confirmTimer.stop() }
    onQueryChanged: { selected=0; pendingPath="" }
    onServiceChanged: if(opened && service) { service.panelOpened(); checkTimer.restart() }
    Timer { id: confirmTimer; interval:2000; onTriggered:{root.pendingPath="";root.message=""} }
    Timer { id: checkTimer; interval:150; onTriggered:root.checkVisible() }
    Timer { interval:60000; running:root.opened; repeat:true; onTriggered:root.now=Date.now()/1000 }
    Process {
        id: checkProcess
        objectName: "check-process"
        stdinEnabled: true
        stdout: StdioCollector { id: checkOutput }
        onExited: function(code) {
            stdinEnabled=true
            if (code!==0 || !root.opened || root.checkGeneration!==root.generation) return
            try { var missing=JSON.parse(checkOutput.text).missing || []; if(missing.length && root.service) root.service.removePaths(missing) } catch(e) { root.message="Could not check visible files" }
        }
    }
    Process {
        id: actionProcess
        objectName: "action-process"
        stdout: StdioCollector { id: actionOutput }
        onExited: function(code) {
            try {
                var result=JSON.parse(actionOutput.text)
                if(code!==0 || result.error) throw new Error(result.error || "Action failed")
                if(root.actionKind==="trash" && root.service) root.service.removePaths([root.actionPath])
                if(root.actionGeneration!==root.generation || !root.opened) return
                if(root.actionKind==="open") root.close()
                else if(root.actionKind==="details") root.detail=result.bytes.toLocaleString()+" bytes · "+root.actionPath
                else root.message=root.actionKind==="trash" ? "Moved to Trash" : root.actionKind==="reveal" ? "Opened in Files" : "Copied"
            } catch(e) { if(root.actionGeneration===root.generation) root.message=String(e).slice(0,240) }
        }
    }
    Component.onDestruction: { actionProcess.running=false; checkProcess.running=false }
    Ui.KeyboardPanel {
        id: popup
        bar: root.bar; anchorItem: root.anchorItem; owner: root.hostWidget || root
        open: root.opened
        focusTarget: search
        contentWidth: fittedContentWidth(Style.space(780))
        contentHeight: cappedContentHeight(Style.space(620))
        ColumnLayout {
            anchors.fill: parent
            spacing: Style.space(12)
            RowLayout {
                Layout.fillWidth: true
                Text { text:"Recents"; color:root.foreground; font.family:Style.font.family; font.pixelSize:Style.font.heading; font.bold:true }
                Item { Layout.fillWidth:true }
                Text { text:root.service && root.service.refreshing ? "Updating…" : root.rows.length+" files"; color:root.foreground; opacity:.6; font.pixelSize:Style.font.caption }
                Text { text:"×"; color:root.foreground; font.pixelSize:Style.font.heading; MouseArea {anchors.fill:parent;onClicked:root.close()} }
            }
            Rectangle {
                Layout.fillWidth:true; Layout.preferredHeight:Style.space(40)
                color:"transparent"; border.color:search.activeFocus ? Color.accent : root.foreground; border.width:1
                TextInput {
                    id: search; objectName:"search"
                    anchors.fill:parent; anchors.margins:Style.space(10)
                    color:root.foreground; font.family:Style.font.family; font.pixelSize:Style.font.body
                    clip:true; selectByMouse:true; maximumLength:256
                    onTextChanged:root.query=text
                    Keys.onPressed:function(event){root.key(event,true)}
                    Text { visible:!search.text; text:"Search file name or folder"; color:root.foreground; opacity:.45; font:search.font }
                }
            }
            Flow {
                Layout.fillWidth:true; Layout.preferredHeight:childrenRect.height; spacing:Style.space(6)
                Repeater {
                    model:root.types
                    Rectangle {
                        required property string modelData; required property int index
                        width:label.implicitWidth+Style.space(16); height:Style.space(28)
                        color:index===root.typeIndex ? Color.accent : "transparent"
                        Text { id:label; anchors.centerIn:parent; text:modelData; color:index===root.typeIndex ? Color.popups.background : root.foreground; font.pixelSize:Style.font.bodySmall; font.family:Style.font.family }
                        MouseArea { anchors.fill:parent; onClicked:root.typeIndex=index }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth:true
                Text { text:"Source: "+root.sources[root.sourceIndex]+" ▾"; color:root.foreground; font.pixelSize:Style.font.caption; MouseArea {anchors.fill:parent;onClicked:root.sourceIndex=(root.sourceIndex+1)%root.sources.length} }
                Item { Layout.fillWidth:true }
                Text { text:search.activeFocus ? "↓ browse · Tab type" : "j/k move · / search · s source"; color:root.foreground; opacity:.55; font.pixelSize:Style.font.caption }
            }
            ListView {
                id:list; objectName:"file-list"
                Layout.fillWidth:true; Layout.fillHeight:true
                clip:true; model:root.rows; spacing:Style.space(2)
                currentIndex:root.selected
                onContentYChanged:if(root.opened)checkTimer.restart()
                Keys.onPressed:function(event){root.key(event,false)}
                delegate:Column {
                    required property var modelData; required property int index
                    width:list.width
                    property string groupName:Model.group(modelData.ts,root.now)
                    Text {
                        visible:!root.query && (index===0 || Model.group(root.rows[index-1].ts,root.now)!==groupName)
                        height:visible ? Style.space(28) : 0
                        text:groupName.toUpperCase(); color:Color.accent; font.family:Style.font.family; font.pixelSize:Style.font.caption; font.bold:true; verticalAlignment:Text.AlignVCenter
                    }
                    Rectangle {
                        width:parent.width; height:Style.space(58)
                        color:index===root.selected ? Style.hoverFillFor(root.foreground,Color.accent) : "transparent"
                        border.color:index===root.selected ? Color.accent : "transparent"
                        RowLayout {
                            anchors.fill:parent; anchors.margins:Style.space(9); spacing:Style.space(12)
                            Text { text:Model.glyph(modelData.kind,!(root.service && root.service.glyphsSupported) || !!root.service.config.plainGlyphs); color:Color.accent; font.family:Style.font.family; font.pixelSize:Style.font.body }
                            ColumnLayout {
                                Layout.fillWidth:true; spacing:Style.space(3)
                                Text { Layout.fillWidth:true; text:Model.name(modelData.path); color:root.foreground; font.family:Style.font.family; font.pixelSize:Style.font.body; elide:Text.ElideMiddle }
                                Text { Layout.fillWidth:true; text:Model.parent(modelData.path,root.service ? root.service.home : ""); color:root.foreground; opacity:.55; font.family:Style.font.family; font.pixelSize:Style.font.caption; elide:Text.ElideMiddle }
                            }
                            ColumnLayout {
                                Text { Layout.alignment:Qt.AlignRight; text:Qt.formatDateTime(new Date(modelData.ts*1000),"HH:mm"); color:root.foreground; font.pixelSize:Style.font.bodySmall }
                                Text { text:modelData.sources.join(" · "); color:root.foreground; opacity:.55; font.pixelSize:Style.font.caption }
                            }
                        }
                        MouseArea { anchors.fill:parent; onClicked:{root.selected=index;list.forceActiveFocus()} onDoubleClicked:{root.selected=index;root.requestAction("open")} }
                    }
                }
                Text {
                    anchors.centerIn:parent; width:parent.width*.9; horizontalAlignment:Text.AlignHCenter; wrapMode:Text.WordWrap
                    visible:root.rows.length===0
                    text:!root.service ? "Waiting for Recents service…" : root.service.lastError ? "Unable to read recent files. See the error below." : !root.service.initialized ? "Scanning… first results in a few seconds." : root.query || root.typeIndex || root.sourceIndex ? "No matching files" : root.service.notice ? "No files found in the available sources" : "Nothing touched in the last "+root.service.config.windowDays+" days"
                    color:root.foreground; opacity:.65; font.pixelSize:Style.font.body
                }
            }
            Text { Layout.fillWidth:true; visible:!!root.detail; text:root.detail; elide:Text.ElideMiddle; color:root.foreground; font.pixelSize:Style.font.caption }
            Text {
                Layout.fillWidth:true; visible:!!text; wrapMode:Text.Wrap
                text:root.message || (root.service ? root.service.lastError || root.service.notice : "")
                color:root.pendingPath ? Color.urgent : root.foreground; font.pixelSize:Style.font.caption
            }
            Text { visible:!!(root.service && root.service.capped); text:"Showing most recent 2,000 · search covers this index"; color:root.foreground; font.pixelSize:Style.font.caption }
            Flow {
                Layout.fillWidth:true; Layout.preferredHeight:childrenRect.height; spacing:Style.space(12)
                Repeater {
                    model:[{label:"Enter Open",kind:"open"},{label:"o Reveal",kind:"reveal"},{label:"y Path",kind:"copy-path"},{label:"c File",kind:"copy-file"},{label:"p Image",kind:"copy-image"},{label:"d Trash",kind:"trash"}]
                    Text {
                        required property var modelData
                        text:modelData.label; color:modelData.kind==="trash" ? Color.urgent : root.foreground; font.pixelSize:Style.font.caption
                        opacity:root.current ? 1 : .4
                        MouseArea {anchors.fill:parent; enabled:!!root.current; onClicked:{list.forceActiveFocus();root.requestAction(modelData.kind)}}
                    }
                }
            }
        }
    }
}
