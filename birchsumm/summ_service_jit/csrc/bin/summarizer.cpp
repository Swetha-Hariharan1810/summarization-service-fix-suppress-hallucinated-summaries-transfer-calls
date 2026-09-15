#include <torch/script.h>
#include <torch/serialize.h>

#include <iostream>
#include <memory>
#include <vector>

std::vector<char> get_the_bytes(std::string filename)
{
  std::ifstream input(filename, std::ios::binary);
  std::vector<char> bytes(
      (std::istreambuf_iterator<char>(input)),
      (std::istreambuf_iterator<char>()));

  input.close();
  return bytes;
}
torch::NoGradGuard no_grad;

int main(int argc, const char *argv[])
{
  if (argc != 2)
  {
    std::cerr << "usage: example-app <path-to-exported-script-module>\n";
    return -1;
  }
  torch::jit::script::Module module;
  try
  {
    // Deserialize the ScriptModule from a file using torch::jit::load().
    module = torch::jit::load(argv[1]);
    module.eval();
    at::Tensor tokens = torch::pickle_load(get_the_bytes("tokens.pt")).toTensor();
    at::Tensor lengths = torch::pickle_load(get_the_bytes("lengths.pt")).toTensor();
    at::Tensor params = torch::pickle_load(get_the_bytes("params.pt")).toTensor();
    auto results = module.forward({tokens, lengths, params});
    auto bytes = torch::jit::pickle_save(results);
    std::ofstream fout("result.pt", std::ios::out | std::ios::binary);
    fout.write(bytes.data(), bytes.size());
    fout.close();
  }
  catch (const c10::Error &e)
  {
    std::cerr << "error loading the model \n";
    return -1;
  }

  std::cout << "ok\n";
}
