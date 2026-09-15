import QtQuick
import ".." as Plugin
Item {
    id: test
    property int passed:0
    function check(ok,why) { if(!ok)throw new Error(why);passed++ }
    Plugin.Service {id:svc}
    function run() {
        var procs=[]
        for(var i=0;i<svc.children.length;i++) if('command' in svc.children[i] && 'finish' in svc.children[i])procs.push(svc.children[i])
        var cache=procs.filter(function(p){return p.command.indexOf('cached')>=0})[0]
        var scan=procs.filter(function(p){return p.command.length===0})[0]
        cache.finish(0,JSON.stringify({rows:[],config:{windowDays:14},scannedAt:0}),"")
        check(!svc.initialized,'empty cache is not a completed scan')
        svc.refresh(false);check(scan.running,'scan starts');var cmd=JSON.stringify(scan.command)
        svc.refresh(true);check(JSON.stringify(scan.command)===cmd,'overlap rejected')
        var payload={rows:[{path:'/home/alex/a.pdf',ts:Date.now()/1000,source:'edited'}],scannedAt:Date.now()/1000,config:{windowDays:14},notices:[]}
        scan.finish(0,JSON.stringify(payload),"");check(svc.rows.length===1 && svc.initialized,'scan accepts rows')
        svc.panelOpened();check(!scan.running,'fresh cache avoids rescan')
        svc.lastScan=0;svc.panelOpened();check(scan.running,'stale cache rescans')
        scan.finish(1,'{"error":"fixture failure"}',"");check(svc.rows.length===1 && svc.lastError.length>0,'failure preserves cache and error')
        svc.refresh(true);scan.finish(0,'{"skipped":true,"notice":"low battery"}',"");check(svc.rows.length===1 && svc.notice==='low battery','skip preserves cache')
        svc.removePaths(['/home/alex/a.pdf']);check(svc.rows.length===0,'visible missing removal')
        svc.alive=false;svc.accept(JSON.stringify(payload),0,false);check(svc.rows.length===0,'late results cannot resurrect service')
        return passed
    }
}
