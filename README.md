# Demo of Citrix NetScaler CPX configuration driven from Consul
Designed to run on your laptop, shows how NetScaler CPX can be used as an application proxy for your backend (Dockerized) microservices. Service discovery is driven by [Registrator] (https://github.com/gliderlabs/registrator) and [Consul](https://consul.io).  

## Pre-requisites
* NetScaler CPX Express image (from [Citrix](https://www.citrix.com/products/netscaler-adc/cpx-express.html) or [microloadbalancer.com](https://microloadbalancer.com) )
* Docker on Windows or Mac (tested with v17.04.0-ce-mac7)
* Pull  the following docker images:
    - Consul : `docker pull consul`
    - Registrator : `docker pull registrator`
* Build the following microservice images:
    - Login: `(cd loginjs; docker build -t login-service .)`
    - Cart: `(cd cartjs; docker build -t cart-service .)`
    - Catalog: `(cd catalogjs; docker build -t catalog-service .)`
* Build the sidecar image
    - `docker build -t cpx-consul-sidecar .`


## Demo steps
* Determine your LAN IP. E.g., on a Mac:

```
export HOST_IP=$(ifconfig en0 | grep "inet "| awk -F" " '{print $2}')
```
This is used to point registrator and the CPX sidecar to the Consul server (in this demo Consul also runs locally)

* Run Consul

```
docker run --name consul -d -p 8400:8400 -p 8500:8500 -p 8600:53/udp -h $HOST_IP consul
```

* Run registrator

```
docker run   --net=host --name registrator   -d -h $HOST_IP  -v /var/run/docker.sock:/tmp/docker.sock  gliderlabs/registrator -cleanup -resync 5 consul://localhost:8500 
```

Note that registrator "discovers" the consul container and populates the consul registry with the "consul service"

* Register routes in Consul for each of the microservices (`login`, `cart` and `catalog`)

```
docker run --net=host consul kv put widgetshop/services/login-service/url "/api/login/*"
docker run --net=host consul kv put widgetshop/services/cart-service/url "/api/cart/*"
docker run --net=host consul kv put widgetshop/services/catalog-service/url "/api/catalog/*"
```

* Run the microservices using Docker Compose:

```
(cd app; docker-compose up -d)

```

* Run CPX and the sidecar

```
docker-compose up -d

```

* Check the logs of the sidecar:

```
docker logs cpx-sidecar
```
