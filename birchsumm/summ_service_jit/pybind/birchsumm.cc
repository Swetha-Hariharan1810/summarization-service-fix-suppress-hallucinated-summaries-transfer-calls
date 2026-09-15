#include "csrc/model.h"
#include <memory>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <torch/extension.h>
#include <torch/torch.h>

namespace py = pybind11;

namespace birchsumm {
PYBIND11_MODULE(_birchsumm, m) {
  py::class_<Model>(m, "Model")
      .def(py::init([](const std::string &model_file,
                       const std::string &dict_file,
                       bool optimize_for_inference =
                           false) -> std::unique_ptr<Model> {
             return std::make_unique<Model>(model_file, dict_file,
                                            optimize_for_inference);
           }),
           py::arg("model_file"), py::arg("dict_file"),
           py::arg("optimize_for_inference") = false)
      .def("generate", &Model::generate, py::arg("sents_list"),
           py::arg("params"), py::arg("api_token"),
           py::call_guard<py::gil_scoped_release>())
      .def("get_max_position", &Model::get_max_position,
            py::call_guard<py::gil_scoped_release>());
  ;
}

} // namespace birchsumm
