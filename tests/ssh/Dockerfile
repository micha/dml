# Local offline SSH-host fixture only; not packaged or a Docker execution backend.
FROM scratch
COPY rootfs /
COPY --chown=1000:1000 exchanges /work/exchanges
ENTRYPOINT ["/opt/fixture/sshd"]
