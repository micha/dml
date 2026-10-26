"""Linux sealed input object: one source read, no mutable path fallback."""
import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import stat

MAX_PLAN_BYTES = 16 * 1024 * 1024

class SealUnavailable(RuntimeError):
    pass

class SealedPlan:
    def __init__(self, fd, sha256):
        self.fd, self.sha256 = fd, sha256
    @property
    def path(self):
        # Resolved by the child itself; pass_fds preserves the same descriptor.
        return '/proc/self/fd/' + str(self.fd)
    @property
    def pass_fds(self):
        return (self.fd,)

@contextlib.contextmanager
def sealed_plan(path, expected_digest=None):
    fd = None
    try:
        required = ('F_ADD_SEALS','F_GET_SEALS','F_SEAL_WRITE','F_SEAL_GROW','F_SEAL_SHRINK','F_SEAL_SEAL')
        if not hasattr(os,'memfd_create') or not all(hasattr(fcntl,n) for n in required):
            raise SealUnavailable('Linux plan sealing unavailable')
        # The pathname is read only here, once. Hash this byte object before transfer.
        source = os.open(Path(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(source,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise SealUnavailable('not a regular saved plan')
            data = stream.read(MAX_PLAN_BYTES + 1)
        if not data or len(data) > MAX_PLAN_BYTES:
            raise SealUnavailable('empty/oversized saved plan')
        sha256 = hashlib.sha256(data).hexdigest()
        if expected_digest is not None and sha256 != expected_digest:
            raise SealUnavailable('changed plan bytes')
        fd = os.memfd_create('dml-candidate-approved-plan',os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        os.fchmod(fd,0o600)
        view = memoryview(data)
        while view:
            written = os.write(fd,view)
            if written <= 0:
                raise SealUnavailable('failed sealed plan transfer')
            view = view[written:]
        mask = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
        fcntl.fcntl(fd,fcntl.F_ADD_SEALS,mask)
        if fcntl.fcntl(fd,fcntl.F_GET_SEALS) & mask != mask:
            raise SealUnavailable('incomplete Linux plan seals')
        if hashlib.sha256(os.pread(fd,len(data),0)).hexdigest() != sha256:
            raise SealUnavailable('sealed plan transfer mismatch')
        os.lseek(fd,0,os.SEEK_SET)
    except (AttributeError,OSError) as e:
        if fd is not None:
            os.close(fd)
        raise SealUnavailable('Linux plan sealing unavailable: '+type(e).__name__) from e
    except BaseException:
        if fd is not None:
            os.close(fd)
        raise
    try:
        yield SealedPlan(fd,sha256)
    finally:
        os.close(fd)
