#include "wire-padding-header.h"
#include "ns3/log.h"

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("WirePaddingHeader");
NS_OBJECT_ENSURE_REGISTERED (WirePaddingHeader);

TypeId
WirePaddingHeader::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::WirePaddingHeader")
    .SetParent<Header> ()
    .AddConstructor<WirePaddingHeader> ();
  return tid;
}

TypeId
WirePaddingHeader::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

void
WirePaddingHeader::Print (std::ostream &os) const
{
  os << "diagnostic-wire-padding=" << SIZE;
}

uint32_t
WirePaddingHeader::GetSerializedSize (void) const
{
  return SIZE;
}

void
WirePaddingHeader::Serialize (Buffer::Iterator start) const
{
  for (uint32_t index = 0; index < SIZE; ++index)
    start.WriteU8 (0);
}

uint32_t
WirePaddingHeader::Deserialize (Buffer::Iterator start)
{
  for (uint32_t index = 0; index < SIZE; ++index)
    start.ReadU8 ();
  return SIZE;
}

} // namespace ns3
