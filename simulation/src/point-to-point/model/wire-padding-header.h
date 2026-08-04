#ifndef WIRE_PADDING_HEADER_H
#define WIRE_PADDING_HEADER_H

#include "ns3/header.h"

namespace ns3 {

/**
 * Diagnostic-only bytes appended to a DATA payload before transport/network
 * headers are added.  The bytes have no protocol semantics; the receiver
 * removes them before RDMA payload accounting.
 */
class WirePaddingHeader : public Header
{
public:
  static const uint32_t SIZE = 42;

  static TypeId GetTypeId (void);
  virtual TypeId GetInstanceTypeId (void) const;
  virtual void Print (std::ostream &os) const;
  virtual uint32_t GetSerializedSize (void) const;
  virtual void Serialize (Buffer::Iterator start) const;
  virtual uint32_t Deserialize (Buffer::Iterator start);
};

} // namespace ns3

#endif /* WIRE_PADDING_HEADER_H */
