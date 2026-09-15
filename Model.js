// Pure functions shared by Qt's JavaScript engine and Node tests.
function merge(rows, now, days) {
    var byPath = Object.create(null)
    rows.forEach(function(r) {
        if (!r || typeof r.path !== 'string' || r.path[0] !== '/' || !isFinite(r.ts)) return
        var ts = Math.min(Number(r.ts), now)
        if (ts < now - (days || 14) * 86400) return
        var old = byPath[r.path]
        var sources = r.sources || [r.source]
        if (!old) old = byPath[r.path] = {path:r.path, ts:ts, kind:r.kind || 'Docs', sources:[]}
        old.ts = Math.max(old.ts, ts)
        sources.forEach(function(s) { if (['edited','opened','downloaded'].indexOf(s)>=0 && old.sources.indexOf(s)<0) old.sources.push(s) })
    })
    return Object.keys(byPath).map(function(p) { return byPath[p] }).sort(function(a,b) { return b.ts-a.ts || a.path.localeCompare(b.path) }).slice(0,2000)
}
function fuzzy(query, text) {
    query=query.toLowerCase(); text=text.toLowerCase()
    if (!query) return 1
    var exact=text.indexOf(query)
    if (exact>=0) return 4 + query.length / Math.max(text.length,1)
    var i=0, last=-1, gaps=0
    for (var j=0;j<text.length && i<query.length;j++) {
        if (text[j]===query[i]) { if(last>=0) gaps+=j-last-1; last=j; i++ }
    }
    return i===query.length ? 1/(1+gaps) : 0
}
function name(path) { return path.slice(path.lastIndexOf('/')+1) }
function parent(path,home) { var p=path.slice(0,path.lastIndexOf('/')); return home && (p===home || p.indexOf(home+'/')===0) ? '~'+p.slice(home.length) : p }
function select(rows, query, type, source, now, home) {
    return rows.filter(function(r) { return (type==='All'||r.kind===type) && (source==='All'||r.sources.indexOf(source)>=0) })
      .map(function(r) { return {row:r,score:fuzzy(query,name(r.path)+' '+parent(r.path,home))*Math.pow(.5,Math.max(0,now-r.ts)/(3*86400))} })
      .filter(function(x) { return x.score>0 })
      .sort(function(a,b) { return query ? b.score-a.score || b.row.ts-a.row.ts : b.row.ts-a.row.ts })
      .map(function(x) { return x.row })
}
function group(ts,now) {
    var day=new Date(now*1000); day.setHours(0,0,0,0)
    var yesterday=new Date(day); yesterday.setDate(yesterday.getDate()-1)
    var week=new Date(day); week.setDate(week.getDate()-((week.getDay()+6)%7))
    return ts>=day.getTime()/1000 ? 'Today' : ts>=yesterday.getTime()/1000 ? 'Yesterday' : ts>=week.getTime()/1000 ? 'This week' : 'Earlier'
}
function glyph(kind,plain) {
    var tags={Docs:'doc',Images:'img',Video:'vid',Audio:'aud',Archives:'zip',Code:'code'}
    var icons={Docs:'󰈙',Images:'󰋩',Video:'󰕧',Audio:'󰎆',Archives:'󰀼',Code:'󰅩'}
    return plain ? '['+(tags[kind]||'file')+']' : icons[kind]||'󰈙'
}
if (typeof module!=='undefined') module.exports={merge:merge,fuzzy:fuzzy,select:select,group:group,name:name,parent:parent,glyph:glyph}
