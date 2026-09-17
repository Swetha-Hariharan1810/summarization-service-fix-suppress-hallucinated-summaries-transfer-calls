#ifndef BIRCHSUMM_CSRC_AUTH_H_
#define BIRCHSUMM_CSRC_AUTH_H_

#include <string>
namespace birchsumm {
bool auth_request(std::string const &server_url,
                  std::string const &bearer_token);
} // namespace birchsumm

#endif
