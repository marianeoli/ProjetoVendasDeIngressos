#!/bin/bash

# Instalação
sudo apt update
sudo apt install -y curl gnupg ca-certificates
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | \
sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
echo "deb [ arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

sudo apt update
sudo apt install -y mongodb-org

# Criando pastas necessárias
sudo mkdir -p /data/config /var/log/mongodb
sudo chown -R mongodb:mongodb /data/config /var/log/mongodb

# Arrumando arquivos .conf e .service em seu devido lugar
sudo cp ./MongoCluster/config.service /etc/systemd/system/
sudo cp ./MongoCluster/config.conf /etc/

# Subindo Config
sudo systemctl daemon-reload
sudo systemctl enable config
sudo systemctl start config

sleep 10

# Inicialização
mongosh --port 27018 --eval 'rs.initiate({_id: "configrs", configsvr: true, members: [{_id: 0, host: "configdb:27018"}]})'

echo "config pronto"

