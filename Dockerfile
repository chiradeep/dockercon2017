FROM python:2
MAINTAINER Chiradeep Vittal <chiradeep.vittal@citrix.com>
RUN mkdir -p /tmp  
RUN (cd /tmp && wget http://downloadns.citrix.com.edgesuite.net/11872/ns-11.0-65.31-sdk.tar.gz)
RUN (cd /tmp && tar xvzf ns-11.0-65.31-sdk.tar.gz && \
    tar xvzf ns-11.0-65.31-nitro-python.tgz && \
    tar xvf ns_nitro-python_ion_65_31.tar && \
    cd nitro-python-1.0/ && \
    python setup.py install && \
    cd / && \
    rm -rf /tmp && \
    mkdir -p /usr/src/app)

RUN pip install python-consul 

COPY *.py /usr/src/app/

ENTRYPOINT ["python", "/usr/src/app/main.py"]
