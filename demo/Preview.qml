import QtQuick
import QtQuick.Window
import qs.Commons
import ".." as Plugin
Window {
    width:800; height:48; visible:true
    id: fixture
    property int calls: 0
    property string requested: ""
    property bool vertical: false
    property var svc: QtObject {
        property var rows: JSON.parse(fixtureJson)
        property var config: ({windowDays:14,plainGlyphs:true,showTodayCount:true})
        property string home: "/home/alex"
        property bool refreshing: false
        property bool glyphsSupported: false
        property bool initialized: true
        property string lastError: ""
        property string notice: ""
        property bool capped: false
        function panelOpened() {}
        function refresh(scheduled) { fixture.calls++ }
        function removePaths(paths) { rows=rows.filter(function(r){return paths.indexOf(r.path)<0}) }
    }
    property var fakeBar: QtObject {
        property bool vertical: fixture.vertical
        property int barSize: 32
    }
    Plugin.Panel { id: panel; service:fixture.svc; bar:fixture.fakeBar }
    Plugin.BarWidget { objectName:"fixture-widget"; service:fixture.svc; bar:fixture.fakeBar }
    property int actionChecks: 0
    function assertAction(ok,reason) { if(!ok)throw new Error(reason);actionChecks++ }
    function verifyActions() {
        panel.typeIndex=0; panel.sourceIndex=0;panel.query="";panel.selected=0;panel.open("{}")
        var process=null
        for(var i=0;i<panel.children.length;i++) if(panel.children[i].objectName==="action-process")process=panel.children[i]
        panel.requestAction("trash");assertAction(!process.running,"one activation must not trash")
        panel.key({key:Qt.Key_D,isAutoRepeat:true,accepted:false},false)
        assertAction(!process.running,"auto repeat must not trash")
        var path=panel.current.path
        panel.requestAction("trash");assertAction(process.running && process.command[3]==="trash" && process.command[4]===path,"second activation dispatches exact path")
        process.finish(1,'{"error":"fixture refusal"}',"")
        assertAction(panel.message.indexOf("fixture refusal")>=0 && panel.current.path===path,"failed trash preserves row")
        panel.requestAction("open");panel.close();panel.open("{}")
        process.finish(0,'{"ok":true}',"")
        assertAction(panel.opened,"late open completion cannot close new panel")
        panel.requestAction("trash");panel.requestAction("trash")
        process.finish(0,'{"ok":true}',"")
        assertAction(!panel.rows.some(function(r){return r.path===path}),"successful trash removes row")
        panel.close()
    }
    function changeTheme() { Color.light=!Color.light }
    Component.onCompleted: { Style.scale=previewScale; Color.light=previewLight;panel.open("{}") }
}
