#ifndef BIRCHSUMM_CSRC_DICT_H_
#define BIRCHSUMM_CSRC_DICT_H_

#include <string>
#include <torch/script.h>
#include <torch/torch.h>
#include <unordered_map>
#include <vector>

namespace birchsumm {

class Dict {
public:
  explicit Dict(std::string const &dict_file);
  void print() const;
  int add_symbol(std::string const &word);
  std::string const &get_symbol(std::size_t idx) const;
  int get_idx(std::string const &symbol) const;
  std::size_t size() const;
  torch::Tensor encode_line(std::vector<std::string> const &sent,
                            bool append_eos = false) const;

  torch::Tensor encode_line(std::string const &sent,
                            bool append_eos = false) const;
  std::string decode(torch::Tensor const &tokens) const;

private:
  std::unordered_map<std::string, int> indices_;
  std::vector<std::string> symbols_;
  int eos_index_;
  int unk_index_;
  int bos_index_;
  int pad_index_;
};

} // namespace birchsumm

#endif
