#include "common.hpp"

PYBIND11_MODULE(bmq, m) {
    bmq::BMQ_Init(m);
    bmq::BEncode_Init(m);
}
