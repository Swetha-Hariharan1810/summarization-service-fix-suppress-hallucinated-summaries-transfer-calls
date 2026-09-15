pybind11_add_module(_birchsumm birchsumm.cc)
target_link_libraries(_birchsumm PRIVATE birchsumm_core)
target_link_libraries(_birchsumm PRIVATE ${TORCH_DIR}/lib/libtorch_python.so)
target_link_libraries(_birchsumm PRIVATE ${PYTHON_LIBRARY})
target_link_libraries(_birchsumm PUBLIC "-Wl,-rpath,$ORIGIN/birchsumm/lib")


install(TARGETS _birchsumm
  DESTINATION ../
)
