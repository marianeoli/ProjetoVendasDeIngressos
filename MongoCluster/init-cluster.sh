#!/bin/bash

echo "Inicializando containers..."
sleep 5

# Config Server
docker exec -it config mongosh --port 27018 --eval 'rs.initiate({_id: "configReplSet", configsvr: true, members: [{_id: 0, host: "configsvr:27018"}]})'

# Shards
docker exec -it shard1 mongosh --port 27019 --eval 'rs.initiate({_id: "shard1ReplSet", members: [{_id: 0, host: "shard1:27019"}]})'
docker exec -it shard2 mongosh --port 27020 --eval 'rs.initiate({_id: "shard2ReplSet", members: [{_id: 0, host: "shard2:27020"}]})'
docker exec -it shard3 mongosh --port 27021 --eval 'rs.initiate({_id: "shard3ReplSet", members: [{_id: 0, host: "shard3:27021"}]})'

echo "Criando a Estrutura do Banco de Dados..."
sleep 10

# Adição dos Shards ao roteador mongos e montando estrutura do banco de dados
docker exec -it mongos mongosh --port 27017 --eval '
  sh.addShard("shard1ReplSet/shard1:27019");
  sh.addShard("shard2ReplSet/shard2:27020");
  sh.addShard("shard3ReplSet/shard3:27021");

  var db = db.getSiblingDB("ingressos");
  sh.enableSharding("ingressos");
  sh.shardCollection("ingressos.pedidos", { "_id": "hashed" });
'

echo "Tudo pronto!"
