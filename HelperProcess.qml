import Quickshell
import Quickshell.Io

// Keep desktop routing and XDG locations, but never inherit interpreter,
// loader, shell startup, or executable-search overrides into a helper.
Process {
    clearEnvironment: true
    environment: helperEnvironment
    readonly property var helperEnvironment: {
        var result = {PATH: "/usr/bin", LANG: "C.UTF-8"}
        var keys = ["HOME", "USER", "LOGNAME", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                    "XDG_STATE_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR", "XDG_DATA_DIRS", "XDG_CONFIG_DIRS",
                    "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "DISPLAY",
                    "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS", "LANG", "LC_ALL", "LC_CTYPE",
                    "TZ", "OMARCHY_SCREENSHOT_DIR", "OMARCHY_SCREENRECORD_DIR"]
        for (var i = 0; i < keys.length; i++) {
            var value = Quickshell.env(keys[i])
            if (value) result[keys[i]] = value
        }
        return result
    }
}
