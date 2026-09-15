import QtQuick
import QtTest
import "../.." as Plugin
import ".." as Checks

TestCase {
    name: "RecentsBoundaries"
    property int previewWidth: 800
    property int previewHeight: 660
    Checks.ServiceChecks { id: serviceChecks }
    Plugin.HelperProcess { id: helper }
    QtObject {
        id: source
        property var rows: [{path:"/home/alex/<b>folder/<i>report.pdf", ts:Date.now()/1000, kind:"Docs", sources:["opened"]}]
        property var config: ({windowDays:14, plainGlyphs:true})
        property string home: "/home/alex"
        property bool refreshing: false
        property bool glyphsSupported: false
        property bool initialized: true
        property string lastError: "<b>helper error</b>"
        property string notice: ""
        property bool capped: false
        function panelOpened() {}
        function removePaths(paths) {}
    }
    Plugin.Panel { id: panel; service: source }

    function test_service_lifecycle() {
        compare(serviceChecks.run(), 11)
    }
    function test_helper_environment() {
        verify(helper.clearEnvironment)
        compare(helper.environment.PATH, "/usr/bin")
        compare(helper.environment.HOME, "/home/alex")
        compare(helper.environment.WAYLAND_DISPLAY, "wayland-fixture")
        verify(!("PYTHONPATH" in helper.environment))
        verify(!("LD_PRELOAD" in helper.environment))
        verify(!("BASH_ENV" in helper.environment))
    }
    function test_external_text_is_literal() {
        panel.open("{}")
        panel.detail = "<b>details</b>"
        var list = findChild(panel, "file-list")
        verify(list !== null)
        tryVerify(function() { return list.itemAtIndex(0) !== null })
        var names = ["recent-file-name", "recent-file-parent", "recent-detail", "recent-message"]
        for (var i = 0; i < names.length; i++) {
            var item = findChild(i < 2 ? list.itemAtIndex(0) : panel, names[i])
            verify(item !== null, names[i])
            compare(item.textFormat, Text.PlainText, names[i])
        }
        compare(findChild(panel, "recent-message").text, "<b>helper error</b>")
        compare(findChild(panel, "recent-detail").text, "<b>details</b>")
        compare(findChild(list.itemAtIndex(0), "recent-file-name").text, "<i>report.pdf")
        panel.close()
    }
}
