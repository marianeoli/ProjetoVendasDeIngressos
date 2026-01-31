# ProjetoVendaDeIngressos
Sistema escalável de vendas de ingressos como projeto final da disciplina de Sistemas Distribuídos, utilizando FastAPI, RabbitMQ e MongoDB Sharded.

## Como Rodar o Banco  
Instâncias linux t3.small (Fiz com Debian). Portas 27017, 27018, 27019 e 27020 abertas nos Security Groups da AWS para as instâncias. 

Para que os servidores se comuniquem por nomes, adicione os IPs privados de cada instância no arquivo /etc/hosts de todas as máquinas:  
**sudo nano /etc/hosts**
### Adicione:
<IP_PRIVADO_CONFIG>  configdb  
<IP_PRIVADO_SHARD1>  shard1  
<IP_PRIVADO_SHARD2>  shard2  
<IP_PRIVADO_MONGOS>  mongos

Em cada instância respectiva, execute os scripts de inicialização contidos na pasta ./MongoCluster:  
**No Config Server:**  
chmod +x ./MongoCluster/config-init.sh  
./MongoCluster/config-init.sh

**No Shards 1:**  
chmod +x ./MongoCluster/shard1-init.sh  
./MongoCluster/shard1-init.sh

**No Shards 2:**  
chmod +x ./MongoCluster/shard2-init.sh  
./shard2-init.sh

**No Mongos Roteador:** O Mongos deve ser o último a subir, pois ele depende que os shards e o config server já estejam ativos.  
chmod +x ./MongoCluster/mongos-init.sh  
./MongoCluster/mongos-init.sh

### Sobre os Arquivos de Configuração
*.conf - Arquivos de configuração do MongoDBDefine portas, caminhos de dados e papéis (sharding/replSetName).  
*.service - Unidades do SystemdPermite gerenciar o banco via systemctl (start/stop/enable).  
*-init.sh - Scripts de automação para instalar o MongoDB 7.0 e inicializa os Replica Sets.

## Comandos Úteis de Gerenciamento  
**Verificar o status dos serviços:** 
sudo systemctl status config # No config  
sudo systemctl status shard1 # Nos Shards  
sudo systemctl status mongos # No Mongos

**Verificar a saúde do cluster (pelo Mongos):**  
Conecte-se ao Mongos e rode sh.status() // Mostra os shards ativos e a distribuição dos bancos

**Verificar logs em caso de erro:**  
sudo journalctl -u config -f

## Sempre que reiniciar as instâncias, dar o comando:  
sudo systemctl start config # No config  
sudo systemctl start shard1 # No shard1  
sudo systemctl start shard2 # No shard2  
sudo systemctl start mongos # No mongos, DEVE SER O ÚLTIMO A SER STARTADO

## Conexão
Para ter a aplicação e banco conectados, adicione o ip público do servidor mongos no arquivo /etc/hosts da máquina que estão os arquivos da aplicação:  
**sudo nano /etc/hosts**  
### Adicione:  
<IP_PÚBLICO_MONGOS> mongos 
