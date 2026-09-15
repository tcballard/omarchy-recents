import QtQuick
import Quickshell
import Quickshell.Io
import "." as Plugin

// One-shot, headless probe: no service, desktop window, scan, or file action.
ShellRoot {
    Plugin.HelperProcess {
        command: ["/usr/bin/python3", "-I", "-c",
                  "import json,os; print(json.dumps({'path':os.environ.get('PATH'), 'pythonpath':'PYTHONPATH' in os.environ, 'loader':'LD_PRELOAD' in os.environ, 'bash':'BASH_ENV' in os.environ}))"]
        running: true
        stdout: StdioCollector { id: output }
        onExited: function(code) {
            try {
                var result = JSON.parse(output.text)
                if (code !== 0 || result.path !== "/usr/bin" || result.pythonpath || result.loader || result.bash)
                    throw new Error("Unexpected child environment")
                console.log("RECENTS_NATIVE_PROCESS_PASS")
            } catch (error) {
                console.error("RECENTS_NATIVE_PROCESS_FAIL: " + error)
            }
            Qt.quit()
        }
    }
}
