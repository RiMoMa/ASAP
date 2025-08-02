#ifndef _JPEG2000Codec
#define _JPEG2000Codec
#ifdef USE_JPEG2000
#  include "jpeg2kcodec_export.h"
#else
#  define JPEG2KCODEC_EXPORT
#endif

namespace pathology {
  enum class DataType;
  enum class ColorType;
}

class JPEG2KCODEC_EXPORT JPEG2000Codec
{
public:
#ifdef USE_JPEG2000
  JPEG2000Codec();
  ~JPEG2000Codec();
#else
  inline JPEG2000Codec() {}
  inline ~JPEG2000Codec() = default;
#endif

#ifdef USE_JPEG2000
  void encode(char* data, unsigned int& size, const unsigned int& tileSize, const unsigned int& rate, const unsigned int& nrComponents, const pathology::DataType& dataType, const pathology::ColorType& colorSpace) const;
  void decode(unsigned char* buf, const unsigned int& inSize, const unsigned int& outSize);
  void decode(unsigned char* inBuf, const unsigned int& inSize, unsigned char* outBuf, const unsigned int& outSize);
#else
  inline void encode(char*, unsigned int&, const unsigned int&, const unsigned int&, const unsigned int&, const pathology::DataType&, const pathology::ColorType&) const {}
  inline void decode(unsigned char*, const unsigned int&, const unsigned int&) {}
  inline void decode(unsigned char*, const unsigned int&, unsigned char*, const unsigned int&) {}
#endif
};

#endif
