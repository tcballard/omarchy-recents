import os,sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QUrl,QMetaObject,Q_RETURN_ARG
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
root=Path(__file__).resolve().parents[1]
app=QGuiApplication([]);engine=QQmlApplicationEngine();engine.addImportPath(str(root/'tests/qml'))
errors=[];engine.warnings.connect(lambda es:errors.extend(e.toString() for e in es))
engine.load(QUrl.fromLocalFile(str(root/'tests/ServiceChecks.qml')))
if not engine.rootObjects():sys.exit(1)
obj=engine.rootObjects()[0];QMetaObject.invokeMethod(obj,'run')
assert obj.property('passed')==11,(obj.property('passed'),errors)
assert not errors,errors
print('11 assertions against actual Service.qml passed')
