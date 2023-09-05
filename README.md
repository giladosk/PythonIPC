# PythonIPC
share python objects across processes and dockers

Creates a shareable classes that allow data exchange between processes, while these can live in separate python instances (e.g. scripts, terminals, dockers).

This POC:
1. Should be process safe (not yet).
2. Is not secure- implementing proper security methods are intenionally left for the user, so they will be unique and therefore more secure.
