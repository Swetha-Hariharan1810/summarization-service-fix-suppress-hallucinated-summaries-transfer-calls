#include "dict.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

namespace birchsumm {
Dict::Dict(std::string const &dict_file) {
  std::cerr << "Info: Loading dictionary from " << dict_file << "file"
            << std::endl;
  bos_index_ = add_symbol("<s>");
  pad_index_ = add_symbol("<pad>");
  eos_index_ = add_symbol("</s>");
  unk_index_ = add_symbol("<unk>");
  std::ifstream is(dict_file);
  if (not is) {
    std::cerr << "Error: " << dict_file << "doesn't exist." << std::endl;
    return;
  }
  std::string line;
  while (std::getline(is, line)) {
    std::istringstream iss(line);
    int count;
    std::string field;
    if (!(iss >> field >> count)) {
      std::cerr << "Error: line formate error" << line << std::endl;
      break;
    }
    add_symbol(field);
  }
  std::cerr << size() << " symbols in dictionary" << std::endl;
}

std::size_t Dict::size() const { return symbols_.size(); }
void Dict::print() const {
  for (auto const &ele : indices_) {
    std::cerr << ele.first << ": " << ele.second << std::endl;
  }
}

std::string const &Dict::get_symbol(std::size_t idx) const {
  return symbols_.at(idx);
}
int Dict::get_idx(std::string const &symbol) const {
  try {
    int idx = indices_.at(symbol);
    return idx;
  } catch (const std::out_of_range &e) {
    std::cout << "Error: out of range -" << symbol << "not found in dictionary"
              << std::endl;
    throw e;
  }
}

int Dict::add_symbol(std::string const &word) {
  std::size_t index = symbols_.size();
  symbols_.push_back(word);
  indices_[word] = index;
  return index;
}

torch::Tensor Dict::encode_line(std::string const &sent,
                                bool append_eos) const {
  std::vector<std::string> sent_tokens;
  std::stringstream ss(sent);
  std::string token;
  while (ss >> token) {
    sent_tokens.push_back(token);
  }
  return encode_line(sent_tokens);
}
torch::Tensor Dict::encode_line(std::vector<std::string> const &sent,
                                bool append_eos) const {
  auto options = torch::TensorOptions()
                     .dtype(torch::kInt64)
                     .device(torch::kCPU)
                     .requires_grad(false);
  using namespace torch::indexing;

  int tensor_size = sent.size();
  if (append_eos) {
    tensor_size++;
  }
  auto result = torch::zeros(tensor_size, options);
  for (std::size_t i = 0; i < sent.size(); ++i) {
    result.index_put_({static_cast<int>(i)}, get_idx(sent.at(i)));
  }
  if (append_eos) {
    int pos = tensor_size - 1;
    result.index_put_({pos}, eos_index_);
  }
  return result;
}

std::string Dict::decode(torch::Tensor const &tokens) const {
  auto accessor = tokens.accessor<long, 1>();
  std::string result;
  for (int i = 0; i < accessor.size(0); ++i) {

    std::size_t idx = accessor[i];
    if (idx != bos_index_ && idx != eos_index_) {
      result += get_symbol(idx) + " ";
    }
  }
  result.erase(result.end() - 1);
  return result;
}
} // namespace birchsumm
