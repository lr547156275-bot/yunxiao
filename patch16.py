import io
p='/work/simulation/scratch/third.cc'
src=io.open(p,encoding='utf-8',errors='surrogateescape').read()
old='''	k.sip = qp->sip; k.dip = qp->dip;'''
assert src.count(old)==1
# RdmaQueuePair::sip/dip are Ipv4Address on the QP side, plain uint32 in the
# CustomHeader.  Normalise to the header's representation so both sides agree.
src=src.replace(old,'''	k.sip = qp->sip.Get(); k.dip = qp->dip.Get();''')
io.open(p,'w',encoding='utf-8',errors='surrogateescape').write(src)
print("fixed Ipv4Address -> uint32 via Get()")
