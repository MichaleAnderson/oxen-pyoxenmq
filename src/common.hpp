#pragma once
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

namespace py = pybind11;

namespace bmq {

void BMQ_Init(py::module &mod);
void BEncode_Init(py::module & mod);

}
