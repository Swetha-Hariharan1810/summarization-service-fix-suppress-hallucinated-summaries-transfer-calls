

five9-prod:
June 12:
aws ecr  --profile five9-prod get-login-password --region us-east-1 | docker login --username AWS --password-stdin 179366111227.dkr.ecr.us-east-1.amazonaws.com
docker build -f k8s.Dockerfile -t summ-mcr:0.1.0 .
docker tag summ-mcr:0.1.0 179366111227.dkr.ecr.us-east-1.amazonaws.com/summ-mcr:0.1.0
docker push 179366111227.dkr.ecr.us-east-1.amazonaws.com/summ-mcr:0.1.0

