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
sudo mkdir -p /data/shard1 /var/log/mongodb
sudo chown -R mongodb:mongodb /data/shard1 /var/log/mongodb

#Arrumando arquivos .conf e .service em seu devido lugar
sudo cp ./MongoCluster/shard1.service /etc/systemd/system/
sudo cp ./MongoCluster/shard1.conf /etc/

# Subindo Shard 2
sudo systemctl daemon-reload
sudo systemctl enable shard1
sudo systemctl start shard1

sleep 10

# Inicialização
mongosh --port 27019 --eval 'rs.initiate({_id: "shard1rs", members: [{_id: 0, host: "shard1:27019"}]})'

echo "shard 1 pronto"
