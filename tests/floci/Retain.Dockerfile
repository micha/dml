# Explicit PRIVATE lifetime/evidence variant of the already cached reviewed image.
# Installed DML package bytes are unchanged; this wrapper is outside that package.
ARG BASE
FROM ${BASE}
COPY retain.py /opt/fixture/retain.py
ENTRYPOINT ["/opt/dml/bin/python", "/opt/fixture/retain.py"]
