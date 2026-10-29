FROM scratch
COPY rootfs /
USER 1000:1000
WORKDIR /work
ENV HOME=/home/dml
CMD ["/opt/dml/bin/python", "-m", "daggerml.floci_worker"]
