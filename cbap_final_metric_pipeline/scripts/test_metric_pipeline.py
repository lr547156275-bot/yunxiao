#!/usr/bin/env python3
import csv,gzip,hashlib,json,os,sys,tempfile,unittest
sys.path.insert(0,os.path.dirname(__file__))
from collect_full_work_metrics import collect

def write_csv(path,fields,rows):
 with open(path,"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def digest(path):
 h=hashlib.sha256();h.update(open(path,"rb").read());return h.hexdigest()

class PipelineTests(unittest.TestCase):
 def fixture(self,flows,queue=None):
  td=tempfile.TemporaryDirectory();run=os.path.join(td.name,"run");out=os.path.join(td.name,"out");os.makedirs(run)
  incumbents=[x["flow_id"] for x in flows if x["role"]=="incumbent"]
  newcomers=[x["flow_id"] for x in flows if x["role"]=="newcomer"]
  json.dump({"scenario":"unit","capacity_bps":100000000000,"incumbent_flow_ids":incumbents,
             "pending_flow_ids":newcomers,"common_release_ns":1000},open(os.path.join(run,"scenario_meta.json"),"w"))
  json.dump({"algorithm":"unit","seed":1},open(os.path.join(run,"run_meta.json"),"w"))
  open(os.path.join(run,"config.txt"),"w").write("SIMULATOR_STOP_TIME 0.001\nDATA_RATE 100Gbps\n")
  write_csv(os.path.join(run,"flow_plan.csv"),["flow_id","group_id","round_id","round_bytes"],
            [{"flow_id":x["flow_id"],"group_id":0 if x["role"]=="incumbent" else 1,"round_id":0,"round_bytes":x["planned"]} for x in flows])
  fs=[];rs=[];incs=[];rates=[]
  for x in flows:
   delivered=x.get("delivered",x["planned"] if x.get("completed",True) else 0);completed=x.get("completed",True);finish=x.get("finish",0.0005)
   if x.get("flow_record",True): fs.append({"scenario":"unit","algorithm":"unit","seed":1,"flow_id":x["flow_id"],"qp_id":"q","src":x["flow_id"],"dst":9,"total_size_bytes":x["planned"],"start_time":x.get("ready",0.000001),"finish_time":finish if completed else 0,"fct":finish-x.get("ready",0.000001) if completed else 0,"acked_bytes":delivered,"completed":int(completed),"flow_goodput":0})
   rs.append({"scenario":"unit","algorithm":"unit","seed":1,"flow_id":x["flow_id"],"qp_id":"q","round_id":0,"round_group_id":0 if x["role"]=="incumbent" else 1,"participant_count":1,"release_time":x.get("ready",0.000001),"injection_end_time":0,"ack_completion_time":finish if completed and x.get("round_complete",True) else 0,"round_completion_time":0,"round_bytes":x["planned"]})
   rates.append({"flow_id":x["flow_id"],"final_sample_remaining_bytes":x["planned"]-delivered})
   if x["role"]=="incumbent": incs.append({"time_ns":1000000,"flow_id":x["flow_id"],"size_bytes":x["planned"],"acked_bytes":delivered,"remaining_bytes":x["planned"]-delivered,"finished":int(completed),"delivered_bytes":delivered,"completion_time_seconds":finish if completed else 0})
  write_csv(os.path.join(run,"flow_summary.csv"),["scenario","algorithm","seed","flow_id","qp_id","src","dst","total_size_bytes","start_time","finish_time","fct","acked_bytes","completed","flow_goodput"],fs)
  write_csv(os.path.join(run,"round_summary.csv"),["scenario","algorithm","seed","flow_id","qp_id","round_id","round_group_id","participant_count","release_time","injection_end_time","ack_completion_time","round_completion_time","round_bytes"],rs)
  write_csv(os.path.join(run,"rate_summary.csv"),["flow_id","final_sample_remaining_bytes"],rates)
  write_csv(os.path.join(run,"incumbent_summary.csv"),["time_ns","flow_id","size_bytes","acked_bytes","remaining_bytes","finished","delivered_bytes","completion_time_seconds"],incs)
  write_csv(os.path.join(run,"control_summary.csv"),["summary_messages","grant_messages","total_control_bytes"],[{"summary_messages":1,"grant_messages":2,"total_control_bytes":64}])
  q=queue or [(0.0,0,0),(0.00001,10,1000),(0.00003,30,2000)]
  write_csv(os.path.join(run,"selected_link_timeseries.csv"),["time","link_id","queue_bytes","utilization","tx_bytes_delta","ecn_marks_delta","pfc_paused","pfc_event_delta"],[{"time":t,"link_id":"L","queue_bytes":v,"utilization":.5,"tx_bytes_delta":tx,"ecn_marks_delta":0,"pfc_paused":0,"pfc_event_delta":0} for t,v,tx in q])
  return td,run,out

 def run_fixture(self,flows,queue=None):
  td,run,out=self.fixture(flows,queue);r,l,p=collect(run,out);self.addCleanup(td.cleanup);return r,l,p,run

 def test_01_completed_newcomer(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":100}]);self.assertTrue(r["all_newcomers_completed"])
 def test_02_completed_incumbent(self):
  r,l,_,_=self.run_fixture([{"flow_id":0,"role":"incumbent","planned":100}]);self.assertTrue(r["all_incumbents_completed"])
 def test_03_incomplete_incumbent(self):
  r,l,_,_=self.run_fixture([{"flow_id":0,"role":"incumbent","planned":100,"delivered":40,"completed":False}]);self.assertEqual(r["incumbent_remaining_bytes"],60)
 def test_04_incomplete_newcomer(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":100,"delivered":40,"completed":False}]);self.assertFalse(r["all_newcomers_completed"])
 def test_05_missing_completion_record(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":100,"delivered":40,"completed":False,"flow_record":False}]);self.assertTrue(l[0]["censored"])
 def test_06_plan_flow_not_deleted(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":100,"completed":False,"flow_record":False}]);self.assertEqual(len(l),1)
 def test_07_byte_conservation(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":100,"delivered":40,"completed":False}]);self.assertEqual(r["total_planned_bytes"],r["total_delivered_bytes"]+r["total_remaining_bytes"])
 def test_08_completed_requires_bytes(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":100,"delivered":99,"completed":True,"round_complete":False}]);self.assertFalse(l[0]["completed"])
 def test_09_makespan(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":100,"ready":.0001,"finish":.0006}]);self.assertAlmostEqual(r["all_work_makespan_us"],500)
 def test_10_censored_makespan(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":100,"ready":.0001,"completed":False}]);self.assertIsNone(r["all_work_makespan_us"]);self.assertAlmostEqual(r["censored_makespan_lower_bound_us"],900)
 def test_11_irregular_queue_auc(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":1}],[(0,0,0),(.00001,10,1),(.00003,30,1)]);self.assertAlmostEqual(r["queue_auc_byte_seconds"],.00045)
 def test_12_duplicate_timestamp_audit(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":1}],[(0,0,0),(0,10,1),(.00001,20,1)]);self.assertTrue(any("duplicate_queue_timestamp" in x for x in r["suspicious_findings"]))
 def test_13_utilization_window(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":1,"ready":0,"finish":.00003}],[(0,0,0),(.00001,0,125000),(.00003,0,250000)]);self.assertAlmostEqual(r["utilization_active_window"],1.0)
 def test_14_utilization_above_one_audit(self):
  r,l,_,_=self.run_fixture([{"flow_id":1,"role":"newcomer","planned":1,"ready":0,"finish":.00001}],[(0,0,0),(.00001,0,250000)]);self.assertTrue(any("utilization_above_one" in x for x in r["suspicious_findings"]))
 def test_15_source_hash_unchanged(self):
  td,run,out=self.fixture([{"flow_id":1,"role":"newcomer","planned":100}]);p=os.path.join(run,"flow_summary.csv");before=digest(p);collect(run,out);self.assertEqual(before,digest(p));td.cleanup()
 def test_16_applied_capacity_audit_file(self):
  td,run,out=self.fixture([{"flow_id":1,"role":"newcomer","planned":100}])
  write_csv(os.path.join(run,"applied_rate_audit.csv"),
   ["applied_capacity_violation","applied_capacity_excess_bps"],
   [{"applied_capacity_violation":1,"applied_capacity_excess_bps":5000000000}])
  r,_,_=collect(run,out);self.assertEqual(r["applied_capacity_violation_count"],1)
  self.assertEqual(r["applied_capacity_max_excess_bps"],5000000000);td.cleanup()
 def test_17_sender_pacing_audit_file(self):
  td,run,out=self.fixture([{"flow_id":1,"role":"newcomer","planned":100}])
  write_csv(os.path.join(run,"sender_tx_trace.csv"),
   ["event","previous_tx_time_ns","actual_gap_ns","expected_gap_ns"],
   [{"event":"TX_SEND","previous_tx_time_ns":10,"actual_gap_ns":8,"expected_gap_ns":10},
    {"event":"TX_SEND","previous_tx_time_ns":20,"actual_gap_ns":10,"expected_gap_ns":10}])
  r,_,_=collect(run,out);self.assertEqual(r["pacing_violation_count"],1);td.cleanup()
 def test_18_compressed_applied_capacity_audit_file(self):
  td,run,out=self.fixture([{"flow_id":1,"role":"newcomer","planned":100}])
  plain=os.path.join(run,"applied_rate_audit.csv")
  write_csv(plain,["applied_capacity_violation","applied_capacity_excess_bps"],
   [{"applied_capacity_violation":0,"applied_capacity_excess_bps":0},
    {"applied_capacity_violation":1,"applied_capacity_excess_bps":7000000000}])
  with open(plain,"rb") as source,gzip.open(plain+".gz","wb") as destination:
   destination.write(source.read())
  os.unlink(plain)
  r,_,p=collect(run,out);self.assertEqual(r["applied_capacity_violation_count"],1)
  self.assertEqual(r["applied_capacity_max_excess_bps"],7000000000)
  self.assertIn("applied_rate_audit.csv.gz",p["input_file_hashes"]);td.cleanup()

if __name__=="__main__":
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(PipelineTests);res=unittest.TextTestRunner(verbosity=2).run(suite)
 print("UNIT_TESTS passed=%d total=%d"%(res.testsRun-len(res.failures)-len(res.errors),res.testsRun))
 raise SystemExit(0 if res.wasSuccessful() else 1)
