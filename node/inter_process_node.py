from multiprocessing.managers import BaseManager
from multiprocessing import shared_memory
import numpy as np
from time import sleep


class InterProcessNode:
    def __init__(self, ipc_address, shared_mem_name, shared_mem_template):
        # initiate connections and shared memory blocks, node side
        # define connection objects
        class ConnectionManager(BaseManager): pass
        ConnectionManager.register('get_lock')
        ConnectionManager.register("get_api")
        self.connection_manager = ConnectionManager(address=ipc_address, authkey=b'secret password')

        # init shared memory
        print('trying to connect to shared_memory')
        while True:
            try:
                self.shm = shared_memory.SharedMemory(create=False, name=shared_mem_name, size=shared_mem_template.nbytes)

                break
            except FileNotFoundError:
                continue
        buffer = self.shm.buf
        self.input_array = np.ndarray((200, 200), dtype=np.int64, buffer=buffer)
        print(f'connected to shared memory, first argument is {self.input_array[0, 0]}')

    def start(self):
        # TODO: arrange init<->start calls
        print('waiting for server')
        while True:
            try:
                self.connection_manager.connect()
                self._lock = self.connection_manager.get_lock()
                self._api = self.connection_manager.get_api()
                print('connected to server')
                break
            except (EOFError, ConnectionRefusedError):
                continue

    def test_data(self):
        print(self._api.get_data())
        self._api.update_data(2, 7)
        print(self._api.get_data())

    def test_lock(self):
        print('releasing lock')
        self._lock.release()

    def test_shared_memory(self):
        print(f'share memory has value of {self.input_array[0, 0]}')
        self.input_array[0, 0] = 1
        print(f'share memory has value of {self.input_array[0, 0]}')


address = ('localhost', 6000)
SHM_NAME = "NUMPY_SHMEM"
array_template = np.ones(shape=(200, 200), dtype=np.int64)

node = InterProcessNode(ipc_address=address, shared_mem_name=SHM_NAME, shared_mem_template=array_template)
node.start()
node.test_data()
node.test_lock()
node.test_shared_memory()
print('shutting down')
node.shm.close()
node.shm.unlink()
