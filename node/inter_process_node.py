from multiprocessing.managers import BaseManager
from multiprocessing import shared_memory
import numpy as np
from time import sleep


class InterProcessNode:
    def __init__(self, ipc_address, shared_mem_name, shared_mem_template):
        # initiate connections and shared memory blocks, node side

        # init connection objects
        # declare custom manager references
        class ConnectionManager(BaseManager): pass
        ConnectionManager.register('get_lock')
        ConnectionManager.register("get_data_api")
        self.connection_manager = ConnectionManager(address=ipc_address, authkey=b'secret password')
        # connect to the server and save references to its objects
        print('connecting to server')
        while True:
            try:
                self.connection_manager.connect()
                self._lock = self.connection_manager.get_lock()
                self._api = self.connection_manager.get_data_api()
                break
            except (EOFError, ConnectionRefusedError):
                continue
        print('connected to server')

        # init shared memory
        print('connecting to shared_memory')
        while True:
            try:
                self.shm = shared_memory.SharedMemory(create=False, name=shared_mem_name, size=shared_mem_template.nbytes)
                buffer = self.shm.buf
                self.input_array = np.ndarray((200, 200), dtype=np.int64, buffer=buffer)
                break
            except FileNotFoundError:
                continue
        print(f'connected to shared memory, first argument is {self.input_array[0, 0]}')

    def start(self):
        # TODO: arrange init<->start calls. "start" should be a thread that get requests and writes to a queue
        pass

    def test_data(self):
        print(self._api.get_data_object())
        self._api.update_data_object(2, 7)
        print(self._api.get_data_object())

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
