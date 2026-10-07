#include <cstdint>
#include <cstddef>
#include "ProcessRGB.hpp"
extern "C" void etc2_rgba(uint32_t* bgra, uint64_t* dst, uint32_t w, uint32_t h) {
    CompressEtc2Rgba(bgra, dst, w * h / 16, w, true);
}
