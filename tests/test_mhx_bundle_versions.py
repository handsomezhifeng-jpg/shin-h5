import hashlib,io,sys,unittest,zipfile,collections
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_mhx_bundle_versions import Audit,VERSION

class BundleVersionAuditTest(unittest.TestCase):
 def setUp(self):
  self.original=b'original bundle';self.newer=b'newer bundle';self.md5=hashlib.md5(self.original).hexdigest();self.new_md5=hashlib.md5(self.newer).hexdigest();self.member='assets/Bundles/Android/Base/'+self.md5+'.bytes';self.new_member='assets/Bundles/Android/Base/'+self.new_md5+'.bytes'
  memory=io.BytesIO()
  with zipfile.ZipFile(memory,'w')as archive:
   archive.writestr(self.member,self.original);archive.writestr(self.new_member,self.newer);archive.writestr('assets/SettingV2/test.bytes',b'embedded setting')
  memory.seek(0);self.audit=Audit.__new__(Audit);self.audit.archive=zipfile.ZipFile(memory);self.audit.names=set(self.audit.archive.namelist());self.audit.args=SimpleNamespace(cache=Path('cache'));self.audit.by_hash={self.md5:{'name':'same_asset.bytes','hash':self.md5,'size':len(self.original)}};self.audit.by_name={'same_asset.bytes':self.audit.by_hash[self.md5]};self.audit.other={self.new_md5:{'version':'1.4.93.9','name':'same_asset.bytes'}};self.audit.refs=collections.defaultdict(list);self.audit.claims=[];self.audit.excluded_diagnostics=[]
 def tearDown(self):self.audit.archive.close()
 def test_original_version_and_source_sha_verified(self):
  row=self.audit.verify('apk:'+self.member,[{'claimedSha256':hashlib.sha256(self.original).hexdigest()}]);self.assertEqual(row['catalogVersion'],VERSION);self.assertEqual(row['issues'],[])
 def test_apk_bundle_does_not_receive_embedded_exception(self):
  row=self.audit.verify('apk:'+self.new_member,[]);self.assertEqual(row['status'],'version-mismatch');self.assertEqual(row['foundInVersion'],'1.4.93.9');self.assertEqual(row['expectedReplacement']['md5'],self.md5)
 def test_source_sha_claim_is_checked_independently(self):
  row=self.audit.verify('apk:'+self.member,[{'claimedSha256':'0'*64}]);self.assertIn('source-sha256-claim-mismatch',row['issues'])
 def test_embedded_nonbundle_is_verified_directly(self):
  row=self.audit.verify('apk:assets/SettingV2/test.bytes',[]);self.assertEqual(row['status'],'apk-embedded-non-bundle');self.assertEqual(row['issues'],[])
 def test_recursive_particle_key_and_catalog_bundle_are_included(self):
  self.audit.walk({'particleSources':{self.member:{'sha256':hashlib.sha256(self.original).hexdigest()}},'originalCatalog':{'bundles':[{'name':'same_asset.bytes','md5':self.md5,'size':len(self.original)}]}},'fx.json')
  self.assertEqual(len(self.audit.refs['apk:'+self.member]),2);self.assertEqual(self.audit.refs['apk:'+self.member][0]['claimedSha256'],hashlib.sha256(self.original).hexdigest())
 def test_explicit_rejected_cache_diagnostics_are_not_used_sources(self):
  self.audit.walk({'excludedBundles':[{'source':'apk:'+self.new_member}],'source':'apk:'+self.member},'assets/construction/source-version-audit.json');self.assertEqual(list(self.audit.refs),['apk:'+self.member]);self.assertEqual(self.audit.excluded_diagnostics[0]['count'],1)
 def test_source_hash_dictionary_values_are_verified(self):
  self.audit.walk({'sourceSHA256':{self.member:'0'*64}},'source-packages.json');row=self.audit.verify('apk:'+self.member,self.audit.refs['apk:'+self.member]);self.assertIn('source-sha256-claim-mismatch',row['issues'])

if __name__=='__main__':unittest.main()
