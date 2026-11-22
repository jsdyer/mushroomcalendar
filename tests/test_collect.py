import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect import normalize,validate,ROOT
class CollectionTests(unittest.TestCase):
 def record(self):
  return {'id':123,'taxon':{'id':456,'name':'Test fungus','rank':'species'},'observed_on':'2024-10-23','license_code':'cc-by','quality_grade':'research','geojson':{'coordinates':[-122.654321,49.123456]},'public_positional_accuracy':12,'user':{'login':'test'}}
 def test_obscured_and_taxon_private_records_never_keep_precise_day_or_coordinates(self):
  for field,value in [('obscured',True),('coordinates_obscured',True),('geoprivacy','obscured'),('taxon_geoprivacy','private')]:
   source=self.record();source[field]=value;r=normalize(source,'langley');self.assertEqual(r['date'],'2024-10');self.assertIsNone(r['week']);self.assertIsNone(r['latitude']);self.assertIsNone(r['longitude'])
 def test_public_coordinates_are_rounded_before_persistence(self):
  r=normalize(self.record(),'langley');self.assertEqual(r['latitude'],49.12);self.assertEqual(r['longitude'],-122.66);self.assertEqual(r['date'],'2024-10-23')
 def test_unlicensed_bad_dates_and_out_of_period_are_rejected(self):
  for field,value in [('license_code',None),('license_code','cc-by-sa'),('observed_on','2024-99-01'),('observed_on','2026-01-01')]:
   source=self.record();source[field]=value;self.assertIsNone(normalize(source,'langley'))
 def test_real_snapshot_integrity_complete_coverage_and_safe_coordinates(self):
  payload=json.loads((ROOT/'data/current.json').read_text());validate(payload)
  self.assertTrue(all(q['retrieved']==q['source_total'] for q in payload['queries']))
  self.assertTrue(all(q['included']+q['skipped_invalid']==q['retrieved'] for q in payload['queries']))
  for entry in json.loads((ROOT/'data/history.json').read_text()):
   raw=gzip.decompress((ROOT/entry['file']).read_bytes());self.assertEqual(hashlib.sha256(raw).hexdigest(),entry['sha256']);validate(json.loads(raw))
 def test_incomplete_refresh_is_rejected(self):
  payload=json.loads((ROOT/'data/current.json').read_text());payload['queries'][0]['complete']=False
  with self.assertRaisesRegex(ValueError,'Incomplete'):validate(payload)
 def test_duplicate_source_id_is_rejected(self):
  payload=json.loads((ROOT/'data/current.json').read_text());payload['records'].append(copy.deepcopy(payload['records'][0]))
  with self.assertRaisesRegex(ValueError,'Duplicate'):validate(payload)
