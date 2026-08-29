import sys
sys.path.insert(0,'/work/simulation/experiment/scheme1_sba')
from controller_ref import *
print("=== correcting the deadband derivation ===")
print("  WRONG (previous): quantum = N*on_wire aggregated, giving 0.307C =")
print("  47% of the band -- the controller would barely respond.  And my note")
print("  '660us is well under H_guard=175us' was false: 660 > 175.")
print()
print("  RIGHT: a command re-rates each of N flows by u/N.  The smallest")
print("  meaningful per-flow change is one on-wire packet per H_guard:")
per_flow = ON_WIRE*8.0/H_GUARD_S
print("    per-flow quantum = on_wire*8/H_guard = %.3f Mbps" % (per_flow/1e6))
db = per_flow*N_FLOWS/N_FLOWS   # per-flow granularity applies per flow
print("    as an aggregate deadband it is still per-flow: %.3f Mbps = %.6f C"
      % (per_flow/1e6, per_flow/C))
print()
span=HARD_BYTES-SOFT_BYTES
slope=(MAX_BOOST+MAX_DRAIN)/span
du_epoch=slope*MAX_BOOST*EPOCH_S/8.0
print("  du per epoch at full boost = %.3f Mbps" % (du_epoch/1e6))
print("  deadband/du_per_epoch      = %.1f epochs = %.0f us"
      % (per_flow/du_epoch, per_flow/du_epoch*5))
print("  fraction of the band       = %.5f" % (per_flow/(MAX_BOOST+MAX_DRAIN)))
print()
print("  -> a command roughly every %.0f us, far below H_guard=175us, so the"
      % (per_flow/du_epoch*5))
print("     brake still engages within one guard window.  This time the")
print("     arithmetic is consistent.")
print()
print("=== how many commands would 60ms of closed loop produce? ===")
print("  worst case (continuous max slope): %.0f commands" % (60e3/(per_flow/du_epoch*5)))
print("  vs 285 observed with a 1 bit/s threshold, and 4 with the frozen bug.")
