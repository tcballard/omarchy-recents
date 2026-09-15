pragma Singleton
import QtQuick
QtObject {
    property real scale: 1
    function space(n) { return Math.round(n*scale) }
    function spaceReal(n) { return n*scale }
    function hoverFillFor(fg, accent) { return Qt.rgba(accent.r,accent.g,accent.b,.12) }
    property QtObject font: QtObject { property string family: "DejaVu Sans Mono"; property int body: 13*Style.scale; property int bodySmall: 11*Style.scale; property int caption: 10*Style.scale; property int heading: 22*Style.scale }
    property QtObject bar: QtObject { property int sizeHorizontal: 32*Style.scale }
}
