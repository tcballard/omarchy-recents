import QtQuick
import qs.Commons
import qs.Ui as Ui
import "Model.js" as Model

Ui.BarWidget {
    id: root
    moduleName: "io.github.tcballard.recents"
    property var shell: null
    property var service: null
    readonly property var sourceService: service || (shell ? shell.serviceFor(moduleName) : (bar && bar.shell ? bar.shell.serviceFor(moduleName) : null))
    readonly property string label: sourceService && sourceService.config.showTodayCount && !vertical ? String(sourceService.rows.filter(function(r) { return Model.group(r.ts, Date.now()/1000)==="Today" }).length) : ""
    readonly property bool opened: panelLoader.item ? panelLoader.item.opened : false
    readonly property bool popoutSwitchClosing: panelLoader.item ? panelLoader.item.popoutSwitchClosing : false
    function open() { if (panelLoader.item) panelLoader.item.open() }
    function close() { if (panelLoader.item) panelLoader.item.close() }
    function closeForPopoutSwitch() { if (panelLoader.item) panelLoader.item.closeForPopoutSwitch() }
    function injectPanel() {
        if (!panelLoader.item) return
        panelLoader.item.bar = root.bar
        panelLoader.item.settings = root.settings
        panelLoader.item.anchorItem = button
        panelLoader.item.hostWidget = root
        panelLoader.item.service = root.sourceService
    }
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    onBarChanged: injectPanel()
    onSettingsChanged: injectPanel()
    onSourceServiceChanged: injectPanel()
    Loader {
        id: panelLoader
        active: true
        visible: false
        source: Qt.resolvedUrl("Panel.qml")
        onLoaded: { root.injectPanel(); Qt.callLater(root.injectPanel) }
    }
    Ui.WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: (!root.sourceService || !root.sourceService.glyphsSupported || root.sourceService.config.plainGlyphs ? "R" : "󰋚") + (root.label ? " " + root.label : "")
        active: root.opened
        tooltipText: "Recents — click to browse files; right-click to rescan" + (root.vertical ? " · " + root.label : "")
        onPressed: function(mouseButton) {
            if (mouseButton === Qt.RightButton) { if (root.sourceService) root.sourceService.refresh() }
            else if (mouseButton === Qt.LeftButton) { if (root.opened) root.close(); else root.open() }
        }
    }
}
