import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('recents',Path(__file__).resolve().parents[1]/'bin/recents.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class HelperTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name); self.now=time.time()
        self.stack=[]
        for name,value in [('HOME',self.home),('CONFIG',self.home/'.config/recents/config.json'),('STATE',self.home/'.local/state/recents'),('XBEL',self.home/'.local/share/recently-used.xbel')]:
            p=patch.object(r,name,value);p.start();self.addCleanup(p.stop)
        self.c=json.loads(json.dumps(r.DEFAULT))
    def file(self,name):
        p=self.home/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture');return p
    def sink(self):return r.Candidates(self.c,self.now)
    def test_nul_find_handles_hostile_names(self):
        p=self.file('Documents/a\tline\n$(never);.pdf');sink=self.sink()
        partial,_=r.scan_root(p.parent,6,self.now-100,sink)
        self.assertFalse(partial);self.assertIn(str(p),sink.rows)
    def test_ctime_is_included_when_mtime_is_old(self):
        p=self.file('Documents/old.pdf');os.utime(p,(1,1));sink=self.sink()
        r.scan_root(p.parent,6,self.now-100,sink);self.assertIn(str(p),sink.rows)
    def test_depth_and_exclusions(self):
        for n in ['Documents/.hidden/a','Documents/node_modules/a','Documents/a.tmp','Documents/a.part','Documents/Unconfirmed123','Documents/deep/a.pdf']:self.file(n)
        sink=self.sink();r.scan_root(self.home/'Documents',1,0,sink);self.assertEqual(sink.rows,{})
    def test_canonical_dedup_and_external_symlink(self):
        p=self.file('Documents/a.pdf');q=self.home/'Documents/link.pdf';q.symlink_to(p);outside=self.home/'Documents/out';outside.symlink_to('/etc/passwd')
        sink=self.sink();sink.add(p,self.now,'edited');sink.add(q,self.now,'opened');sink.add(outside,self.now,'opened')
        self.assertEqual(len(sink.rows),1);self.assertEqual(sink.rows[str(p)]['sources'],['edited','opened'])
    def test_home_is_never_a_root(self):
        with patch.object(r.subprocess,'check_output',return_value=str(self.home).encode()):self.assertEqual(r.roots(self.c),[])
    def test_xbel_uri_entities_and_timestamp(self):
        p=self.file('Documents/a & b.pdf');r.XBEL.parent.mkdir(parents=True,exist_ok=True)
        r.XBEL.write_text('<xbel><bookmark href="'+p.as_uri().replace('&','&amp;')+'" visited="'+time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(self.now))+'"><info><mime-type type="application/pdf"/></info></bookmark></xbel>')
        sink=self.sink();r.xbel(sink);self.assertIn(str(p),sink.rows)
    def test_nonlocal_uri_rejected(self):
        self.assertIsNone(r.uri_path('file://remote/home/a'));self.assertIsNone(r.uri_path('https://example.test/a'));self.assertIsNone(r.uri_path('file:///etc/passwd'))
    def test_xml_entities_rejected(self):
        r.XBEL.parent.mkdir(parents=True);r.XBEL.write_text('<!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]><xbel/>')
        with self.assertRaises(ValueError):r.xbel(self.sink())
    def test_invalid_config_is_not_silently_defaulted(self):
        r.CONFIG.parent.mkdir(parents=True);r.CONFIG.write_text('{broken')
        with self.assertRaises(ValueError):r.config()
    def test_config_range(self):
        r.CONFIG.parent.mkdir(parents=True);r.CONFIG.write_text('{"maxDepth":100}')
        with self.assertRaises(ValueError):r.config()
    def test_atomic_state_private_and_replace(self):
        r.atomic_json('index.json',{'a':1});r.atomic_json('index.json',{'a':2})
        self.assertEqual(json.loads((r.STATE/'index.json').read_text()),{'a':2});self.assertEqual((r.STATE/'index.json').stat().st_mode&0o777,0o600)
    def test_state_symlink_rejected(self):
        r.STATE.parent.mkdir(parents=True);r.STATE.symlink_to(self.home)
        with self.assertRaises(ValueError):r.atomic_json('index.json',{})
    def test_visible_page_removes_missing_only(self):
        p=self.file('Documents/a.pdf');paths=[str(p),str(p)+'missing']
        import io
        with patch.object(r.sys,'stdin',io.StringIO(json.dumps(paths))):self.assertEqual(r.main(['check']),{'missing':[paths[1]]})
    def test_copy_file_uri_uses_encoded_bytes(self):
        p=self.file('Documents/a #b\n.pdf')
        with patch.object(r.subprocess,'run') as run:r.action('copy-file',str(p))
        self.assertEqual(run.call_args.args[0],['wl-copy','--type','text/uri-list']);self.assertEqual(run.call_args.kwargs['input'],(p.as_uri()+'\r\n').encode())
    def test_trash_has_option_boundary_no_shell(self):
        p=self.file('Documents/-rf $(touch nope)')
        with patch.object(r.subprocess,'run') as run:r.action('trash',str(p))
        self.assertEqual(run.call_args.args[0],['gio','trash','--',str(p)]);self.assertNotIn('shell',run.call_args.kwargs)
    def test_actions_reject_directories_and_external_paths(self):
        with self.assertRaises(ValueError):r.action('trash',str(self.home))
        with self.assertRaises(ValueError):r.action('open','/etc/passwd')
    def test_image_action_rejects_document(self):
        with self.assertRaises(ValueError):r.action('copy-image',str(self.file('a.pdf')))
    def test_browser_chromium_backup_reads_download(self):
        p=self.file('Downloads/report.pdf');dbpath=self.home/'.config/chromium/Default/History';dbpath.parent.mkdir(parents=True)
        with sqlite3.connect(dbpath) as db:db.execute('CREATE TABLE downloads(target_path,end_time,state)');db.execute('INSERT INTO downloads VALUES(?,?,1)',(str(p),int((self.now+11644473600)*1000000)))
        sink=self.sink();notices=[]
        with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.home/'.config'),'XDG_RUNTIME_DIR':str(self.home)}):r.browsers(sink,notices)
        self.assertEqual(notices,[]);self.assertIn(str(p),sink.rows);self.assertEqual(list(self.home.glob('recents-*')),[])
    def test_browser_firefox_destination(self):
        p=self.file('Downloads/photo.png');dbpath=self.home/'.mozilla/firefox/test/places.sqlite';dbpath.parent.mkdir(parents=True)
        with sqlite3.connect(dbpath) as db:
            db.executescript('CREATE TABLE moz_annos(content,anno_attribute_id,place_id);CREATE TABLE moz_anno_attributes(id,name);CREATE TABLE moz_places(id,last_visit_date);');db.execute('INSERT INTO moz_annos VALUES(?,1,1)',(p.as_uri(),));db.execute("INSERT INTO moz_anno_attributes VALUES(1,'downloads/destinationFileURI')");db.execute('INSERT INTO moz_places VALUES(1,?)',(int(self.now*1000000),))
        sink=self.sink()
        with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.home/'.config'),'XDG_RUNTIME_DIR':str(self.home)}):r.browsers(sink,[])
        self.assertIn(str(p),sink.rows)
    def test_battery_skip_does_not_overwrite_index(self):
        with patch.object(r,'low_battery',return_value=True):self.assertTrue(r.scan(True)['skipped'])
        self.assertFalse(r.STATE.exists())
    def test_timeout_keeps_partial_output(self):
        import subprocess,sys
        p=self.file('Documents/a.pdf');sink=self.sink()
        payload=(str(self.now)+'\0'+str(self.now)+'\0'+str(p)+'\0').encode()
        real_popen=subprocess.Popen
        def launch(*args,**kwargs):
            return real_popen([sys.executable,'-c','import sys,time;sys.stdout.buffer.write('+repr(payload)+');sys.stdout.flush();time.sleep(5)'],**kwargs)
        with patch.object(r.subprocess,'Popen',side_effect=launch):
            partial,_=r.scan_root(p.parent,6,0,sink,.1)
        self.assertTrue(partial);self.assertIn(str(p),sink.rows)
    def test_slow_root_reduces_depth_after_three_runs(self):
        folder=self.file('Documents/a.pdf').parent
        with patch.object(r,'roots',return_value=[folder]),patch.object(r,'scan_root',return_value=(False,9)) as scan_root,patch.object(r,'xbel'):
            for _ in range(4):r.scan()
        self.assertEqual([x.args[1] for x in scan_root.call_args_list],[6,6,6,3])
    def test_disabled_browser_source_is_never_read(self):
        with patch.object(r,'roots',return_value=[]),patch.object(r,'xbel'),patch.object(r,'browsers') as browser:r.scan()
        browser.assert_not_called()
    def test_openwith_passes_argv_without_shell_evaluation(self):
        p=self.file('Documents/a.md');self.c['openWith']={'md':['editor','--new-window']}
        with patch.object(r,'config',return_value=self.c),patch.object(r.subprocess,'run') as run:r.action('open',str(p))
        self.assertEqual(run.call_args.args[0],['editor','--new-window',str(p)])
    def test_cap_retains_newest(self):
        sink=self.sink()
        for i in range(5000):sink.add(self.home/f'{i}.pdf',self.now-i,'edited')
        sink.trim();self.assertEqual(len(sink.rows),2000);self.assertTrue(sink.capped);self.assertIn(str(self.home/'0.pdf'),sink.rows)

if __name__=='__main__':unittest.main()
