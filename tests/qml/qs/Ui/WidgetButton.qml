import QtQuick
import qs.Commons
Item {
    property var bar: null
    property string text: ""
    property bool active: false
    property string tooltipText: ""
    signal pressed(int mouseButton)
    implicitWidth: label.implicitWidth+20
    implicitHeight: 32
    Text { id:label; anchors.centerIn:parent; text:parent.text; color:parent.active?Color.urgent:Color.foreground; font.family:Style.font.family; font.pixelSize:Style.font.body }
    MouseArea { anchors.fill:parent; acceptedButtons:Qt.LeftButton|Qt.RightButton; onClicked:function(mouse){ parent.pressed(mouse.button) } }
}
