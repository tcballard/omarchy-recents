import QtQuick
Item {
    id: root
    property var bar: null
    property var settings: ({})
    property string moduleName: ""
    property bool manageIpc: false
    property bool opened: false
    property bool popoutSwitchClosing: false
    property QtObject controller: QtObject { function show() { root.opened=true } function hide() { root.opened=false } }
    function open() { opened=true }
    function close() { opened=false }
    function closeForPopoutSwitch() { close() }
}
