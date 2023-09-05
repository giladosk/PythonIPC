from multiprocessing.managers import BaseManager
from multiprocessing import shared_memory
import numpy as np
from time import sleep


class InterProcessNode:
    def __init__(self, ipc_address, shared_mem_name, shared_mem_template=None):
        # initiate connections and shared memory blocks, node side
        class ConnectionManager(BaseManager): pass

        ConnectionManager.register('get_lock')
        ConnectionManager.register("get_api")
        self.connection_manager = ConnectionManager(address=ipc_address, authkey=b'secret password')

    def start(self):
        print('waiting for server')
        while True:
            try:
                self.connection_manager.connect()
                self._lock = self.connection_manager.get_lock()
                self._api = self.connection_manager.get_api()
                print('connected to server')
                break
            except EOFError:
                continue

    def test_data(self):
        print(self._api.get_data())
        self._api.update_data(2, 7)
        print(self._api.get_data())

    def test_lock(self):
        # sleep(5)
        print('releasing lock')
        self._lock.release()


address = ('localhost', 6000)
SHM_NAME = "NUMPY_SHMEM"
node = InterProcessNode(ipc_address=address, shared_mem_name=SHM_NAME)
node.start()
node.test_data()
node.test_lock()
