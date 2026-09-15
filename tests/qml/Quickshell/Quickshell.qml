pragma Singleton
import QtQuick
QtObject {
    function env(name) {
        if (name === "HOME") return "/home/alex"
        if (name === "WAYLAND_DISPLAY") return "wayland-fixture"
        return ""
    }
}
