import QtQuick
Item {
    property var command: []
    property bool clearEnvironment: false
    property var environment: ({})
    property bool running: false
    property QtObject stdout: null
    property QtObject stderr: null
    property bool stdinEnabled: false
    property string input: ""
    function write(s) { input=s }
    signal exited(int code, int status)
    function finish(code, output, error) {
        if(stdout) { stdout.text=output; stdout.streamFinished() }
        if(stderr) { stderr.text=error; stderr.streamFinished() }
        running=false
        exited(code,0)
    }
}
