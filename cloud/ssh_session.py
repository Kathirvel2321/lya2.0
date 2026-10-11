"""Bounded SSH exchange; keep stdin open so cancellation reaches the router."""
import subprocess
import threading
import time
from types import SimpleNamespace


def exchange(command, body, cancelled=None, popen=subprocess.Popen, timeout=30,
             close_stdin=False, output_limit=65536):
    if type(output_limit) is not int or not 1<=output_limit<=12000000:
        raise ValueError('Invalid output limit.')
    if cancelled is not None and cancelled.is_set():
        raise InterruptedError()
    process = popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    result = []
    def communicate():
        try:
            process.stdin.write((body + '\n').encode('utf-8'))
            process.stdin.flush()
            if close_stdin:
                process.stdin.close()
            result.append(process.stdout.read(output_limit+1))
        except (OSError, ValueError):
            result.append(b'')
    worker = threading.Thread(target=communicate, daemon=True)
    worker.start()
    deadline = time.monotonic() + timeout
    try:
        while worker.is_alive():
            if cancelled is not None and cancelled.is_set():
                # Termination disconnects the stream; remote watcher sees EOF.
                # Do not close a pipe while its writer may be blocked connecting.
                process.kill()
                raise InterruptedError()
            if time.monotonic() >= deadline:
                raise TimeoutError()
            worker.join(.05)
        process.wait(timeout=max(.01, deadline-time.monotonic()))
        return SimpleNamespace(returncode=process.returncode, stdout=result[0].decode('utf-8'))
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)
        worker.join(2)
        for pipe in (process.stdin, process.stdout):
            try:
                pipe.close()
            except OSError:
                pass
