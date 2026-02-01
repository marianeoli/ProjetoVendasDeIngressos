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
sudo mkdir -p /var/log/mongodb
sudo chown -R mongodb:mongodb /var/log/mongodb

# Arrumando arquivos .conf e .service em seu devido lugar
sudo cp ./MongoCluster/mongos.service /etc/systemd/system/
sudo cp ./MongoCluster/mongos.conf /etc/

# Subindo o Mongos
sudo systemctl daemon-reload
sudo systemctl enable mongos
sudo systemctl start mongos

sleep 10

mongosh --port 27017 --eval '
  sh.addShard("shard1rs/shard1:27019");
  sh.addShard("shard2rs/shard2:27020");

  var db = db.getSiblingDB("bilheteria");
  sh.enableSharding("bilheteria");
  db.usuarios.createIndex({ "_id": "hashed" })
  sh.shardCollection("bilheteria.usuarios", { "_id": "hashed" });
  db.vendas.createIndex({ "usuario_id": "hashed" })
  sh.shardCollection("bilheteria.vendas", { "usuario_id": "hashed" })
  db.eventos.createIndex({ "_id": "hashed" })
  sh.shardCollection("bilheteria.eventos", { "_id": "hashed" })
'

echo "Tudo pronto!"
