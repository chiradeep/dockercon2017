VERSION ?= latest
HOST_IP := $(shell ifconfig en0 | grep "inet "| awk -F" " '{print $$2}')

.PHONY: pull build stop write_urls registrator consul rm 

pull:
	docker pull consul
	docker pull gliderlabs/registrator

build:
	(cd loginjs; docker build -t login-service .)
	(cd cartjs; docker build -t cart-service .)
	(cd catalogjs; docker build -t catalog-service .)
	docker build -t cpx-consul-sidecar .

consul: 
	docker run --name consul -d -p 8400:8400 -p 8500:8500 -p 8600:53/udp -h ${HOST_IP} consul

registrator: 
	docker run   --net=host --name registrator   -d -h ${HOST_IP}  -v /var/run/docker.sock:/tmp/docker.sock  gliderlabs/registrator -cleanup -resync 5 consul://localhost:8500 

write_urls: 
	docker run --net=host consul kv put widgetshop/services/login-service/url "/api/login/*"
	docker run --net=host consul kv put widgetshop/services/cart-service/url "/api/cart/*"
	docker run --net=host consul kv put widgetshop/services/catalog-service/url "/api/catalog/*"

run_microservices: 
	(cd app; docker-compose up -d)

run_cpx: 
	docker-compose up -d

stop:
	docker-compose down
	(cd app; docker-compose down)
	docker stop registrator
	docker stop consul

rm:
	docker rm registrator
	docker rm consul

sleep:
	sleep 20

print_urls:
	@echo "http://localhost:$$(docker port cpx 8088|awk -F':' '{print $$2}')/api/catalog/"
	@echo "http://localhost:$$(docker port cpx 8088|awk -F':' '{print $$2}')/api/cart/"
	@echo "http://localhost:$$(docker port cpx 8088|awk -F':' '{print $$2}')/api/login/"

all:  pull build consul registrator sleep write_urls sleep run_microservices sleep run_cpx
	
cleanup: stop rm
	docker rmi login-service
	docker rmi cart-service
	docker rmi catalog-service
	docker rmi cpx-consul-sidecar

