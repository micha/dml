# Private response-suppression/evidence variant; no installed DML file changes.
ARG BASE
FROM ${BASE}
COPY retain.py lost_manifest.py /opt/fixture/
ENTRYPOINT ["/opt/dml/bin/python", "/opt/fixture/lost_manifest.py"]
