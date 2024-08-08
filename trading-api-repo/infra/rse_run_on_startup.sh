#!/bin/bash

# Script vars:
EC2_AVAIL_ZONE=`curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone`
EC2_REGION="`echo \"$EC2_AVAIL_ZONE\" | sed 's/[a-z]$//'`"
IMAGE='713011802156.dkr.ecr.eu-west-1.amazonaws.com/rse'
IMAGE_TAG='{%IMAGE_TAG%}'
export EC2_AVAIL_ZONE
export EC2_REGION
export IMAGE
export IMAGE_TAG

# Become root, so the rest doesn't need sudo:
sudo su -

apt update -y && apt install nginx docker.io awscli -y
snap start amazon-ssm-agent
usermod -a -G docker ubuntu

sh -c 'printf "server {\nlisten 80;\nserver_name _;\nlocation / {\ninclude proxy_params;\nproxy_pass http://localhost:8080;\n\n}\n}\n" >> /etc/nginx/sites-available/rse.conf'
unlink /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/rse.conf /etc/nginx/sites-enabled/rse.conf
service nginx configtest
systemctl stop nginx
systemctl start nginx
systemctl enable nginx

# Configure aws-cli & ecr
aws configure set region $EC2_REGION
# Run the following command to login to ECR and execute the output, which is required.
# shellcheck disable=SC2091
$(aws ecr get-login --no-include-email --region $EC2_REGION)

# Run papertrail logspout docker container
docker run --restart=always -d \
  -v=/var/run/docker.sock:/var/run/docker.sock  \
  -e "SYSLOG_HOSTNAME=rse-{%STAGE_NAME%}-{%NODE_NUMBER%}" \
  gliderlabs/logspout \
  syslog+tls://logs6.papertrailapp.com:45366

# Pull image and run it
docker pull $IMAGE:$IMAGE_TAG
docker run -d -p 8080:8080 \
  --name "rse" \
  -e REGION_NAME=$EC2_REGION \
  -e STAGE={%STAGE_NAME%} \
  --restart unless-stopped \
  $IMAGE \
  sh -c 'pipenv run gunicorn rse.api.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080 --timeout 120 --graceful-timeout 60 --keep-alive 20 --threads 4'
