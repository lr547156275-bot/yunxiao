import sys
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
from controller_ref import *
print("=== deriving the command deadband from existing quantities ===")
print("  The law is continuous, so SOME quantisation is required or every epoch")
print("  issues a command.  Derive it, do not pick it.")
print()
print("  A command is only meaningful if its effect on the queue over one")
print("  H_guard exceeds the actuation quantum -- one on-wire packet per sender:")
q_quantum = N_FLOWS*ON_WIRE
print("    queue quantum  = N * on_wire        = %d B" % q_quantum)
db = q_quantum*8.0/H_GUARD_S
print("    rate deadband  = quantum*8/H_guard  = %.3f Mbps = %.5f C"
      % (db/1e6, db/C))
print()
print("  Sanity: the law's own slope across the YELLOW band")
span=HARD_BYTES-SOFT_BYTES
slope=(MAX_BOOST+MAX_DRAIN)/span     # bit/s per byte of queue
print("    du/dQ = (MAX_BOOST+MAX_DRAIN)/(hard-soft) = %.1f bps/B" % slope)
dq_per_epoch = MAX_BOOST*EPOCH_S/8.0
print("    dQ per epoch at full boost = %.1f B" % dq_per_epoch)
du_per_epoch = slope*dq_per_epoch
print("    du per epoch               = %.3f Mbps = %.6f C"
      % (du_per_epoch/1e6, du_per_epoch/C))
print()
print("  deadband / du_per_epoch = %.1f epochs" % (db/du_per_epoch))
print("  -> one command per ~%.0f epochs (~%.0f us) instead of every epoch,"
      % (db/du_per_epoch, db/du_per_epoch*5))
print("     which is well under H_guard=175us so braking is not delayed.")
print()
print("  Check it does not exceed the whole band:")
print("    deadband as fraction of MAX_BOOST+MAX_DRAIN = %.4f" % (db/(MAX_BOOST+MAX_DRAIN)))
