from multiprocessing.managers import SyncManager
from multiprocessing import shared_memory, Lock
import numpy as np
from time import sleep


class DataExchangeAPI:
    def __init__(self):
        self.data = {'time': 0, 'value': None}

    def update_data_object(self, new_time, new_value):
        self.data['time'] = new_time
        self.data['value'] = new_value

    def get_data_object(self):
        return self.data


class InterProcessServer:
    def __init__(self, ipc_address, shared_mem_name, shared_mem_template):
        # initiate connections and shared memory blocks, server side

        # init connection objects
        # create custom manager with shared objects
        class ConnectionManager(SyncManager): pass
        lock = Lock()
        ConnectionManager.register('get_lock', callable=lambda: lock)
        data_object_api = DataExchangeAPI()
        ConnectionManager.register("get_data_api", callable=lambda: data_object_api)
        self.connection_manager = ConnectionManager(address=ipc_address, authkey=b'secret password')
        # start the manager and save references to its objects
        print('creating connection server')
        self.connection_manager.start()
        self._lock = self.connection_manager.get_lock()
        self._lock.acquire()
        self._api = self.connection_manager.get_data_api()

        # init shared memory
        print('creating shared_memory')
        self.shm = shared_memory.SharedMemory(create=True, name=shared_mem_name, size=shared_mem_template.nbytes)
        self.output_array = np.ndarray((200, 200), dtype=np.int64, buffer=self.shm.buf)
        self.output_array.fill(-1)

    def start(self):
        # TODO: arrange init<->start calls. "start" should be a thread that get requests and writes to a queue
        pass

    def test_data_alone(self):
        print(self._api.get_data_object())
        self._api.update_data_object(1, 1)
        first_msg = self._api.get_data_object()
        print(first_msg)
        return first_msg

    def test_data_with_node(self):
        return self._api.get_data_object()

    def test_lock(self):
        print('testing lock')
        released = self._lock.acquire(block=False)
        print(f'lock {released=}')
        while not released:
            released = self._lock.acquire(block=False)
        print('client connected to lock')

    def test_shared_memory(self):
        print('waiting for client to connect to shared memory')
        # counter = 0
        while self.output_array[0, 0] == -1:
            # counter += 1
            # if counter == 10000:
            #     print(f'waiting. {self.output_array[0, 0]}')
            #     counter = 0
            continue
        print(f'share memory has value of {self.output_array[0, 0]}')
        print("shared_memory connected to by client")

    def shutdown(self):
        print('shutting down')
        self.connection_manager.shutdown()
        self.shm.close()
        # self.shm.unlink()
        # sleep(1)


address = ('localhost', 6000)
SHM_NAME = "NUMPY_SHMEM"
array_template = np.ones(shape=(200, 200), dtype=np.int64)

server = InterProcessServer(ipc_address=address, shared_mem_name=SHM_NAME, shared_mem_template=array_template)
server.start()
first_msg = server.test_data_alone()

while True:
    new_msg = server.test_data_with_node()
    if new_msg['time'] <= first_msg['time']:
        sleep(1)
        continue
    else:
        print(new_msg)
        break

server.test_lock()
server.test_shared_memory()
server.shutdown()
