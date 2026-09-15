#include "csrc/auth.h"
#include <curl/curl.h>
#include <iostream>

namespace birchsumm {

bool auth_request(std::string const &server_url,
                  std::string const &bearer_token) {
  CURL *curl = curl_easy_init();
  if (!curl) {
    std::cerr << "curl init failed." << std::endl;
    return false;
  }
  CURLcode res;
  curl_easy_setopt(curl, CURLOPT_URL, server_url.c_str());
  struct curl_slist *headers = NULL;
  headers = curl_slist_append(headers, "Content-Type: application/json");

  headers = curl_slist_append(
      headers, (std::string("Authorization: Bearer ") + bearer_token).c_str());
  curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
  curl_easy_setopt(curl, CURLOPT_POSTFIELDS,
                   "{\"text\" : \"###CLIENT-VERINT\"}");
  res = curl_easy_perform(curl);

  long http_code = 0;

  curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);

  if ((http_code == 200 || http_code == 201) &&
      res != CURLE_ABORTED_BY_CALLBACK) {
    // Succeeded
    curl_easy_cleanup(curl);
    return true;
  } else {
    std::cerr << "Authentication failed: " << http_code << std::endl;
    curl_easy_cleanup(curl);
    return false;
  }
}

} // namespace birchsumm
