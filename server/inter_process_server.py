from multiprocessing.managers import SyncManager
from multiprocessing import shared_memory, Lock
import numpy as np
from time import sleep
from queue import Queue, Full
from threading import Thread


class DataExchangeAPI:
    def __init__(self):
        self.data = {'time': 0, 'value': None}

    def update_data_object(self, new_time, new_value):
        self.data['time'] = new_time
        self.data['value'] = new_value

    def get_data_object(self):
        return self.data


class InterProcessServer:
    def __init__(self, ipc_address, shmem_name, shmem_template, queue):
        # initiate connections and shared memory blocks, server side

        # init connection objects
        # create custom manager with shared objects
        class ConnectionManager(SyncManager): pass

        lock = Lock()
        ConnectionManager.register('get_lock', callable=lambda: lock)
        data_object_api = DataExchangeAPI()
        ConnectionManager.register("get_data_api", callable=lambda: data_object_api)
        self.connection_manager = ConnectionManager(address=ipc_address, authkey=b'secret password')
        self.create_manager(ipc_address)

        # init shared memory
        print('creating shared_memory')
        self.shm = shared_memory.SharedMemory(create=True, name=shmem_name, size=shmem_template.nbytes)
        self.shared_array = np.ndarray(shmem_template.shape, dtype=np.int64, buffer=self.shm.buf)
        self.shared_array.fill(-1)

        # link to consumer queue
        self.consumer_queue = queue
        self.latest_timestamp = 0

        # start the service
        Thread(target=self.start, name='inter_process_server', daemon=True).start()

    def create_manager(self, ipc_address):

        # start the manager and save references to its objects
        print('creating connection server')
        self.connection_manager.start()
        self._lock = self.connection_manager.get_lock()
        self._lock.acquire()
        self._api = self.connection_manager.get_data_api()

    def start(self):
        print('processing data stream...\n')
        while True:
            if self._lock.acquire(block=False):
                # if the lock is released, check if the data is new
                data_in_shmem = self._api.get_data_object()
                if data_in_shmem['time'] > self.latest_timestamp:
                    print(f'got new data, hurray!')
                    self.latest_timestamp = data_in_shmem['time']
                    try:  # push most recent data to the consumer queue
                        self.consumer_queue.put_nowait((data_in_shmem, self.shared_array))
                    except Full:
                        self.consumer_queue.get()
                        self.consumer_queue.put((data_in_shmem, self.shared_array))

                    # exit condition:
                    if data_in_shmem['value'] == 'break':
                        self._lock.release()
                        print('got shutdown keyword')
                        break
                else:
                    sleep(0.01)
                self._lock.release()
            else:
                # locked by a node, sleep and try again later
                sleep(0.01)

        self.shutdown()

    def shutdown(self):
        print('shutting down')
        self.connection_manager.shutdown()
        self.shm.close()
        # self.shm.unlink()
        # sleep(1)


address = ('localhost', 6000)
data_queue = Queue(maxsize=1)
SHM_NAME = "NUMPY_SHMEM"
array_template = np.ones(shape=(200, 200), dtype=np.int64)

server = InterProcessServer(ipc_address=address, shmem_name=SHM_NAME, shmem_template=array_template, queue=data_queue)

while True:
    new_data = data_queue.get()
    print(f'new data extracted: {new_data[0]} {new_data[1][0, 0]}\n')
    if new_data[0]['value'] == 'break':
        break

