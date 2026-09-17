#include "csrc/auth.h"
#include "csrc/model.h"
#include <iostream>
#include <torch/serialize.h>

std::vector<char> get_the_bytes(std::string filename) {
  std::ifstream input(filename, std::ios::binary);
  std::vector<char> bytes((std::istreambuf_iterator<char>(input)),
                          (std::istreambuf_iterator<char>()));

  input.close();
  return bytes;
}
torch::NoGradGuard no_grad;
int main(int argc, const char *argv[]) {

  // auto model = birchsumm::Model(argv[1], argv[2]);
  auto dict = birchsumm::Dict(argv[1]);
  auto result = dict.encode_line("1462");
  std::cerr << result << std::endl;
  // birchsumm::auth_request("a72dcdc8329aa4dfcb4db650aa20636c-197144256.us-west-2.elb.amazonaws.com:8080/api/summarization/",
  // "ZGV2dGVzdF96aXl1YW46WEUtUGJWeFFrY0d6YmlhTktTeW1IRS00REhhcGV4eUZKQ1pLRnBwVkg3U3dDWGxTUTY2SW5faUVMbFRUZldjOFpwUmdCYUpYTGYtQXZCRmU1a29DSUE=");
  // check connection
  // cpr::Response r =
  // cpr::Get(cpr::Url{"http://a72dcdc8329aa4dfcb4db650aa20636c-197144256.us-west-2.elb.amazonaws.com:8080/prob/health"});
  // std::cerr << r.status_code << std::endl;

  // at::Tensor tokens =
  // torch::pickle_load(get_the_bytes("tokens.pt")).toTensor(); at::Tensor
  // lengths = torch::pickle_load(get_the_bytes("lengths.pt")).toTensor();
  // at::Tensor params =
  // torch::pickle_load(get_the_bytes("params.pt")).toTensor(); auto results =
  // model.generate(tokens, lengths, params); auto bytes =
  // torch::jit::pickle_save(results); std::ofstream fout("result.pt",
  // std::ios::out | std::ios::binary); fout.write(bytes.data(), bytes.size());
  // fout.close();
  std::cerr << "OK" << std::endl;
}
