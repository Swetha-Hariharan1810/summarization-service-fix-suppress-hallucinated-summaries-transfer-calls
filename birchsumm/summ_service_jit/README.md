# Setup: Birch Summarization Module
You would be provided with the docker image self-sufficient to work on its own, Size approx 10 GB. Along with an api key to get authorized through birch's server.
## Minimum Host Machine Requirements
cpu - 2 cores
Memory - 8 GB
OS - Linux (preffered/tested)
## Steps:
1. Download the docker image from the provided link
2. Setup Docker - https://docs.docker.com/engine/install/
3. Load docker image
 `docker load < `downloaded-docker-image`
4. Run docker
```
docker run -t -d -env API_KEY=$API_KEY -v /path/to/input/transcript/directory:/home/ubuntu/codebase/data/input-transcripts -v /path/to/output/transcript/directory:/home/ubuntu/codebase/data/output-summaries --name birch-summarization-container {{docker_image_id}}
```
pyth
Once the docker container is started,
You can put the transcripts in the input directory -> /path/to/input/transcript/directory
The summaries will be generated at the output directory -> /path/to/output/transcript/directory
These paths are the host machine paths, that are in sync with the docker. (Volumes)

## Authentication
An active internet connection will be required for the container to work properly.
1. Docker has an API key, which is used for the authentication process. The authentication API endpoint will be provided which needs to be whitelisted if the firewall is enabled
