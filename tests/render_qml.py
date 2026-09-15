#!/usr/bin/env python3
"""Actual plugin QML with explicit host/process stubs; no real file actions."""
import json, os, sys, time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QUrl,QTimer,Qt,QObject,QMetaObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtQuick import QQuickWindow
root=Path(__file__).resolve().parents[1]
app=QGuiApplication([]);engine=QQmlApplicationEngine();engine.addImportPath(str(root/'tests/qml'))
now=time.time()
rows=[dict(path='/home/alex/'+p,ts=now-age,kind=k,sources=[s]) for p,age,k,s in [
 ('Documents/Household/Electricity bill.pdf',1200,'Docs','opened'),
 ('Pictures/Family/Weekend at the beach.jpg',3600,'Images','edited'),
 ('Downloads/Train tickets.pdf',6000,'Docs','downloaded'),
 ('Documents/School/Autumn term dates.docx',86400,'Docs','opened'),
 ('Pictures/Screenshot 2026-09-14.png',90000,'Images','edited'),
 ('Downloads/Holiday photos.zip',95000,'Archives','downloaded')]]
ctx=engine.rootContext();ctx.setContextProperty('fixtureJson',json.dumps(rows))
ctx.setContextProperty('previewWidth',int(os.getenv('PREVIEW_WIDTH','800')));ctx.setContextProperty('previewHeight',int(os.getenv('PREVIEW_HEIGHT','660')))
ctx.setContextProperty('previewLight',os.getenv('PREVIEW_LIGHT')=='1');ctx.setContextProperty('previewScale',float(os.getenv('PREVIEW_SCALE','1')))
errors=[];engine.warnings.connect(lambda es:errors.extend(e.toString() for e in es));engine.load(QUrl.fromLocalFile(str(root/'demo/Preview.qml')))
if not engine.rootObjects():sys.exit(1)
fixture=engine.rootObjects()[0]
def finish():
 try:
    panel=fixture.findChild(QObject,'recents-panel')
    win=next(w for w in app.allWindows() if w.isVisible() and w.height()>100)
    output=Path(sys.argv[1] if len(sys.argv)>1 else root/'preview.png');output.parent.mkdir(parents=True,exist_ok=True)
    assert win.grabWindow().save(str(output))
    search=panel.findChild(QObject,'search')
    # Delegates belong to the visual item tree, not necessarily QObject parents.
    def visual_items(item):
        yield item
        for child in item.childItems():
            yield from visual_items(child)
    sinks = {item.objectName(): item for item in visual_items(win.contentItem())
             if item.objectName() in ('recent-file-name','recent-file-parent','recent-detail','recent-message')}
    assert len(sinks)==4, sinks.keys()
    for name,item in sinks.items():
        # QQuickText's private enum has no direct PySide converter. Compare it
        # inside Qt's JS engine, which reads the QML property as a number.
        engine.globalObject().setProperty('sinkUnderTest',engine.newQObject(item))
        assert engine.evaluate('sinkUnderTest.textFormat === 0').toBool(), name
    # Letter action keys remain ordinary typing while searching.
    QTest.keyClick(win,Qt.Key.Key_D);assert panel.property('query')=='d';assert panel.property('pendingPath')==''
    QTest.keyClick(win,Qt.Key.Key_Backspace)
    QTest.keyClick(win,Qt.Key.Key_Tab);assert panel.property('typeIndex')==1
    QTest.keyClick(win,Qt.Key.Key_Backtab);assert panel.property('typeIndex')==0
    QTest.keyClick(win,Qt.Key.Key_Down)
    QTest.keyClick(win,Qt.Key.Key_D);assert panel.property('pendingPath')!=''
    QTest.keyClick(win,Qt.Key.Key_Down);assert panel.property('pendingPath')==''
    QTest.keyClick(win,Qt.Key.Key_D);assert panel.property('pendingPath')!=''
    QTest.keyClick(win,Qt.Key.Key_Escape);assert panel.property('opened');assert panel.property('pendingPath')==''
    QTest.keyClick(win,Qt.Key.Key_S);assert panel.property('sourceIndex')==1
    QTest.keyClick(win,Qt.Key.Key_R);assert fixture.property('calls')==1
    fg=panel.property('foreground');QMetaObject.invokeMethod(fixture,'changeTheme');app.processEvents();assert panel.property('foreground')!=fg
    QTest.keyClick(win,Qt.Key.Key_Slash);[QTest.keyClick(win,getattr(Qt.Key,'Key_'+c.upper())) for c in 'holiday'];assert panel.property('query')=='holiday'
    QTest.keyClick(win,Qt.Key.Key_Escape);assert not panel.property('opened')
    QMetaObject.invokeMethod(fixture,'verifyActions');assert fixture.property('actionChecks')==6
    assert not errors,'\n'.join(errors)
    print('Rendered and checked actual QML:',output);app.exit(0)
 except Exception:
    import traceback;traceback.print_exc();app.exit(1)
QTimer.singleShot(600,finish);sys.exit(app.exec())
