# 🎫 Bilheteria.io - Sistema Distribuído de Venda de Ingressos

> Projeto final da disciplina de Sistemas Distribuídos.

O **Bilheteria.io** é uma plataforma escalável para venda de ingressos de alta demanda. O sistema foi projetado para lidar com picos de tráfego, garantindo integridade de estoque (sem *overselling*) e alta disponibilidade através de uma arquitetura baseada em microsserviços, mensageria assíncrona e banco de dados distribuído (Sharded Cluster).

---

## 🚀 Principais Funcionalidades

### Para o Usuário
* **Compra em Tempo Real:** Visualização de eventos e setores (Pista, VIP, Camarote).
* **Reserva Atômica:** O sistema garante que, se você clicar em "Comprar", o ingresso é reservado instantaneamente, impedindo que outro usuário compre o mesmo assento no mesmo milissegundo.
* **Múltiplas Categorias:** Suporte a diferentes setores e preços (Inteira/Meia) no mesmo evento.
* **Feedback Visual:** Interface reativa com SweetAlert2 para notificações de sucesso/erro.

### Para o Administrador
* **Dashboard Financeiro:** Acompanhamento em tempo real de vendas e receita.
* **Gestão de Eventos:** CRUD completo (Criar, Editar, Pausar, Excluir) com suporte a múltiplos lotes/setores.
* **Controle de Concorrência:** Visualização do estoque real distribuído entre os shards.

---

## 🏗️ Arquitetura do Sistema

O sistema resolve o problema de **concorrência em vendas de ingressos** utilizando as seguintes estratégias:

1.  **API Gateway (FastAPI):** Recebe as requisições, valida tokens JWT e gerencia a lógica de negócio.
2.  **Reserva Atômica (MongoDB):** Utiliza operações `find_one_and_update` com filtros de consistência para garantir decremento seguro do estoque antes de processar o pagamento.
3.  **Processamento Assíncrono (RabbitMQ):** Após a reserva, o pedido é enviado para uma fila de mensagens, desacoplando a resposta ao usuário do processamento pesado (e-mail, confirmação financeira).
4.  **Banco de Dados Distribuído (MongoDB Sharded):**
    * **Sharding:** Os dados de vendas são particionados (sharded) com base no `usuario_id`, permitindo que a carga de escrita e leitura seja distribuída entre múltiplos servidores.
    * **Replication:** Cada shard possui réplicas para tolerância a falhas.

---

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python 3.11, FastAPI, Uvicorn.
* **Frontend:** HTML5, JavaScript (ES6), TailwindCSS, SweetAlert2.
* **Banco de Dados:** MongoDB 7.0 (Configurado em Cluster Sharded).
* **Mensageria:** RabbitMQ.
* **Infraestrutura:** Docker, Docker Compose, AWS EC2.

---

## 💻 Como Rodar Localmente (Docker)

Para testes rápidos e desenvolvimento, utilizamos o Docker Compose que sobe toda a stack (API, Rabbit, Mongo Single, Worker) automaticamente.

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/marianeoli/ProjetoVendasDeIngressos.git](https://github.com/marianeoli/ProjetoVendasDeIngressos.git)
    cd projeto-venda-ingressos
    ```

2.  **Suba os containers:**
    ```bash
    docker compose up --build
    ```

3.  **Acesse a aplicação:**
    * Frontend: `http://localhost:8000`
    * Documentação API (Swagger): `http://localhost:8000/docs`
    * RabbitMQ Manager: `http://localhost:15672` (User: guest / Pass: guest)

4.  **Popular Banco (Opcional):**
    Para criar eventos de teste automaticamente:
    ```bash
    python popula_banco.py
    ```

---

## ☁️ Implantação do Cluster MongoDB (AWS)

Para o ambiente de produção distribuído, configuramos um cluster manual em instâncias EC2 **t3.small** (Debian).

### Topologia do Cluster
* **Config Server:** Gerencia os metadados do cluster.
* **Shard 1 & Shard 2:** Armazenam os fragmentos de dados.
* **Mongos (Router):** Roteia as consultas da aplicação para o shard correto.

### Configuração de Rede e Hosts
Portas liberadas no Security Group: `27017` a `27020`.
Adicione os IPs privados no `/etc/hosts` de todas as máquinas:

```text
<IP_PRIVADO_CONFIG>  configdb
<IP_PRIVADO_SHARD1>  shard1
<IP_PRIVADO_SHARD2>  shard2
<IP_PRIVADO_MONGOS>  mongos
```

## Como Rodar o Banco  

Em cada instância respectiva, execute os scripts de inicialização contidos na pasta ./MongoCluster:  
**No Config Server:**  
```text
chmod +x ./MongoCluster/config-init.sh  
./MongoCluster/config-init.sh
```

**No Shards 1:**
```text
chmod +x ./MongoCluster/shard1-init.sh  
./MongoCluster/shard1-init.sh
```

**No Shards 2:**
```text
chmod +x ./MongoCluster/shard2-init.sh  
./shard2-init.sh
```

**No Mongos Roteador:** O Mongos deve ser o último a subir, pois ele depende que os shards e o config server já estejam ativos.
```text 
chmod +x ./MongoCluster/mongos-init.sh  
./MongoCluster/mongos-init.sh
```

### Sobre os Arquivos de Configuração
* .conf - Arquivos de configuração do MongoDBDefine portas, caminhos de dados e papéis (sharding/replSetName).  
* .service - Unidades do SystemdPermite gerenciar o banco via systemctl (start/stop/enable).  
* -init.sh - Scripts de automação para instalar o MongoDB 7.0 e inicializa os Replica Sets.

## Comandos Úteis de Gerenciamento  
**Verificar o status dos serviços:** 
```text
sudo systemctl status config # No config  
sudo systemctl status shard1 # Nos Shards  
sudo systemctl status mongos # No Mongos
```

**Verificar a saúde do cluster (pelo Mongos):**  
Conecte-se ao Mongos e rode sh.status() // Mostra os shards ativos e a distribuição dos bancos

**Verificar logs em caso de erro:**  
```text
sudo journalctl -u config -f
```

## Sempre que reiniciar as instâncias, dar o comando:  
```text
sudo systemctl start config # No config  
sudo systemctl start shard1 # No shard1  
sudo systemctl start shard2 # No shard2  
sudo systemctl start mongos # No mongos, DEVE SER O ÚLTIMO A SER STARTADO
```

## Conexão
Para ter a aplicação e banco conectados, adicione o ip público do servidor mongos no arquivo /etc/hosts da máquina que estão os arquivos da aplicação:  
**sudo nano /etc/hosts**  
### Adicione:  
```text
<IP_PÚBLICO_MONGOS> mongos 
```

---

## 👥 Autores
Mariane Silva e Milena Mota 