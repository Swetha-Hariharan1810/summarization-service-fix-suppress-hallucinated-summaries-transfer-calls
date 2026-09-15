#ifndef BIRCHSUMM_CSRC_MODEL_H_
#define BIRCHSUMM_CSRC_MODEL_H_

#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)

#include "dict.h"
#include <chrono>
#include <torch/script.h>
#include <torch/torch.h>
#include <unordered_map>
#include <vector>

namespace birchsumm {
class Model {
public:
  explicit Model(std::string const &model_file, std::string const &dict_file,
                 bool optimize_for_inference = false);
  std::vector<std::string> generate(std::vector<std::string> const &sents_list,
                                    torch::Tensor const &params,
                                    std::string const &api_token);
  ~Model() = default;
  int get_max_position();

private:
  torch::jit::script::Module model_;
  Dict dict_;
  std::chrono::seconds delay_;
  long int expire_;
  bool check_aws_login_;
};

} // namespace birchsumm

#endif
