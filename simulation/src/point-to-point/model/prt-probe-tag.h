/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef PRT_PROBE_TAG_H
#define PRT_PROBE_TAG_H

#include "ns3/tag.h"

namespace ns3 {

// Simulation-only identity for the retired PRT diagnostic path. The tag has
// no wire bytes. PRT is excluded from the main-v1 registry and run manifest.
class PrtProbeTag : public Tag
{
public:
  PrtProbeTag ();
  PrtProbeTag (uint32_t groupId, uint8_t probeId);

  static TypeId GetTypeId (void);
  virtual TypeId GetInstanceTypeId (void) const;
  virtual uint32_t GetSerializedSize (void) const;
  virtual void Serialize (TagBuffer buffer) const;
  virtual void Deserialize (TagBuffer buffer);
  virtual void Print (std::ostream &stream) const;

  uint32_t GetGroupId (void) const;
  uint8_t GetProbeId (void) const;

private:
  uint32_t m_groupId;
  uint8_t m_probeId;
};

} // namespace ns3

#endif /* PRT_PROBE_TAG_H */
