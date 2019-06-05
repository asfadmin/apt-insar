FROM ubuntu:18.04

ENV WORKDIR=/opt/isce2-2.3.1
ENV PYTHONPATH=$WORKDIR/configuration
ENV SCONS_CONFIG_DIR=$WORKDIR
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && \
    apt install -y gfortran libmotif-dev libhdf5-dev libfftw3-dev libgdal-dev scons python3 cython3 python3-scipy python3-matplotlib python3-h5py python3-gdal python3-pip wget && \
    cd /opt && \
    wget --no-verbose https://github.com/isce-framework/isce2/archive/v2.3.1.tar.gz && \
    tar -xzf v2.3.1.tar.gz

COPY SConfigISCE $WORKDIR/SConfigISCE

RUN cd $WORKDIR && \
    scons install

ENV ISCE_ROOT=$WORKDIR/install
ENV ISCE_HOME=$ISCE_ROOT/isce
ENV PATH=$ISCE_HOME/bin:$ISCE_HOME/applications:$PATH
ENV PYTHONPATH=$ISCE_ROOT:$ISCE_HOME/applications:$ISCE_HOME/component
