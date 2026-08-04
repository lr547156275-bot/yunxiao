/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "prt-probe-tag.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (PrtProbeTag);

PrtProbeTag::PrtProbeTag ()
  : m_groupId (0),
    m_probeId (0)
{
}

PrtProbeTag::PrtProbeTag (uint32_t groupId, uint8_t probeId)
  : m_groupId (groupId),
    m_probeId (probeId)
{
}

TypeId
PrtProbeTag::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::PrtProbeTag")
    .SetParent<Tag> ()
    .AddConstructor<PrtProbeTag> ();
  return tid;
}

TypeId
PrtProbeTag::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

uint32_t
PrtProbeTag::GetSerializedSize (void) const
{
  return 5;
}

void
PrtProbeTag::Serialize (TagBuffer buffer) const
{
  buffer.WriteU32 (m_groupId);
  buffer.WriteU8 (m_probeId);
}

void
PrtProbeTag::Deserialize (TagBuffer buffer)
{
  m_groupId = buffer.ReadU32 ();
  m_probeId = buffer.ReadU8 ();
}

void
PrtProbeTag::Print (std::ostream &stream) const
{
  stream << "group=" << m_groupId << ",probe=" << (uint32_t)m_probeId;
}

uint32_t
PrtProbeTag::GetGroupId (void) const
{
  return m_groupId;
}

uint8_t
PrtProbeTag::GetProbeId (void) const
{
  return m_probeId;
}

} // namespace ns3
