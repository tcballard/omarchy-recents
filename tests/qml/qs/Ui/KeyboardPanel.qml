import QtQuick
import QtQuick.Window
import qs.Commons
Window {
    id: root
    property var bar: null
    property var anchorItem: null
    property var owner: null
    property bool open: false
    property Item focusTarget: null
    property int contentWidth: 760
    property int contentHeight: 560
    default property alias contents: body.data
    function fittedContentWidth(n) { return Math.min(n, previewWidth) }
    function cappedContentHeight(n) { return Math.min(n, previewHeight) }
    width: contentWidth; height: contentHeight
    visible: open
    color: Color.popups.background
    onOpenChanged: if (open && focusTarget) Qt.callLater(function() { root.requestActivate(); root.focusTarget.forceActiveFocus() })
    Item { id: body; anchors.fill:parent; anchors.margins:16*Style.scale }
}
