#include "model.h"
#include "auth.h"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <streambuf>
#include <cstdlib>

#include <stdio.h>
#include <sys/timex.h>

namespace birchsumm
{

  struct membuf : std::streambuf
  {
    membuf(char *begin, char *end) { this->setg(begin, begin, end); }
  };

  Model::Model(std::string const &model_file, std::string const &dict_file,
               bool optimize_for_inference)
      : dict_(dict_file)
  {
    std::ifstream is(model_file, std::ifstream::binary);
    if (not is)
    {
      std::cerr << "Error 105: " << model_file << "doesn't exist." << std::endl;
      return;
    }

    // get len of file
    is.seekg(0, is.end);
    std::streampos length = is.tellg() - 85 - 59;
    is.seekg(0, is.beg);

    std::vector<char> buffer(length);
    // read beginning padding of 85 chars
    is.read(&buffer[0], 85);
    is.read(&buffer[0], length);

    if (not is)
    {
      std::cerr << "Error 104: reading model file " << model_file << std::endl;
      return;
    }
    is.close();
    std::stringstream input_stream;
    input_stream.rdbuf()->pubsetbuf(&buffer[0], length);
    model_ = torch::jit::load(input_stream);

    if (optimize_for_inference)
      model_ = torch::jit::optimize_for_inference(model_);
#ifndef __DELAY__
    delay_ = std::chrono::seconds(0);
#else
    delay_ = std::chrono::seconds(__DELAY__);
#endif
#ifdef __EXPIRE__
    std::tm tm = {};
    std::stringstream ss(__EXPIRE__);
    ss >> std::get_time(&tm, "%b %d %Y %H:%M:%S");
    auto exp_time_t = std::mktime(&tm);
    auto exp_duration =
        std::chrono::system_clock::from_time_t(exp_time_t).time_since_epoch();
    expire_ =
        std::chrono::duration_cast<std::chrono::seconds>(exp_duration).count();

#endif
    check_aws_login_ = false;
#ifdef __AWS_LOGIN__
    int network = system("ping -c1 -s1 8.8.8.8  > /dev/null 2>&1 ");
    int aws_connection =
        system("ping -c1 -s1 sts.amazonaws.com  > /dev/null 2>&1 ");

    if (network == 0 && aws_connection == 0)
    {
      check_aws_login_ = true;
    }
    else
    {
      std::cerr << "Warning 103: " << network << " " << aws_connection
                << std::endl;
    }
#endif
  }

  std::vector<std::string>
  Model::generate(std::vector<std::string> const &sents_list,
                  torch::Tensor const &params, std::string const &api_token)
  {

#ifdef __AUTH__
    bool auth = auth_request("a72dcdc8329aa4dfcb4db650aa20636c-197144256.us-west-"
                             "2.elb.amazonaws.com:8080/api/summarization/",
                             api_token);
    if (!auth)
    {
      return std::vector<std::string>();
    }
#endif

#ifdef __AWS_LOGIN__
    if (check_aws_login_)
    {
      std::string aws_acc = std::string(std::getenv("DEV_AWS_KEY"));
      std::string aws_secret = std::string(std::getenv("DEV_AWS_SECRET"));
      std::string aws_region = std::string(std::getenv("DEV_AWS_REGION"));
      std::string env = "AWS_ACCESS_KEY_ID=" + aws_acc +
                        " AWS_SECRET_ACCESS_KEY=" + aws_secret +
                        " AWS_DEFAULT_REGION=" + aws_region;

      int status = system(
          (env + " aws sts get-caller-identity >/dev/null 2>/dev/null").c_str());

      if (status != 0)
      {
        std::cerr << "Error 103: " << status << std::endl;
        return std::vector<std::string>();
      }
    }
#endif

#ifdef __EXPIRE__
    // check system synced
    struct timex timex_info = {};
    timex_info.modes = 0; /* explicitly don't adjust any time parameters */
    int ntp_result = ntp_adjtime(&timex_info);
    bool synchronized = ntp_result >= 0 && ntp_result != TIME_ERROR;
    if (!synchronized)
    {
      // system time not synchronized
      std::cerr << "Warning 101: " << ntp_result << std::endl;
    }
    else if (timex_info.esterror > 15000000)
    {
      // system time syncrhonized, but different from internet time
      std::cerr << "Error 101" << std::endl;
      return std::vector<std::string>();
    }

    auto now = std::chrono::system_clock::now().time_since_epoch();
    long now_c = std::chrono::duration_cast<std::chrono::seconds>(now).count();
    if (now_c > expire_)
    {
      std::cerr << "Error 102" << std::endl;
      return std::vector<std::string>();
    }
#endif
    c10::InferenceMode guard;
    at::set_num_threads(1);
    std::vector<torch::Tensor> src_tokens;
    for (std::string const &sent : sents_list)
    {
      src_tokens.push_back(dict_.encode_line(sent));
    }
    std::vector<torch::Tensor> output_tokens =
        model_.run_method("summary_jit", src_tokens, params).toTensorVector();

    std::vector<std::string> summary_strs;
    for (torch::Tensor const &t : output_tokens)
    {
      summary_strs.push_back(dict_.decode(t));
    }
    auto end = std::chrono::system_clock::now() + delay_;
    int i = 0;
    while (std::chrono::system_clock::now() < end)
    {
      i++;
    }
    return summary_strs;
  }

  int Model::get_max_position()
  {
    return model_.run_method("get_max_position").toTensor().item<int>();
  }

} // namespace birchsumm
