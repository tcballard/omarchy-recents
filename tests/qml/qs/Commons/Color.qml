pragma Singleton
import QtQuick
QtObject {
    property bool light: false
    property color foreground: light ? "#242424" : "#d4d4d4"
    property color urgent: light ? "#af2d28" : "#fa8a80"
    property color accent: light ? "#386532" : "#b8d597"
    property QtObject popups: QtObject { property color text: Color.foreground; property color background: Color.light ? "#f0eee8" : "#1c221e" }
}
