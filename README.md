# Software Tools and Techniques for AI 
This repository contains the code and flask application for the first assignment of CS203 (2024-25) Software Tools and Techniques for AI.

## Installation
1. Clone the repository:
    ```sh
    git clone https://github.com/nikhil-405/stt-ai-01.git
    ```
2. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Install [Docker Desktop](https://docs.docker.com/engine/install/)

## Usage
After installation, you need to start a pre-built docker image using the following command: 
```sh
$ docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HTTP_PORT=9411 \
  -p 5775:5775/udp \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 14268:14268 \
  -p 9411:9411 \
  jaegertracing/all-in-one:1.6.0
```
After starting an image of Jaeger, you can simply run the [app](app.py) and access it at the localhost URL given in the logs.log file. And you can access the Jaeger UI [here](http://localhost:16686/).
