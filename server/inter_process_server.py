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
        # start the manager and save references to its objects
        print('creating connection server')
        self.connection_manager.start()
        self._lock = self.connection_manager.get_lock()
        self._lock.acquire()
        self._api = self.connection_manager.get_data_api()

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

    def start(self):
        print('subscribed to data stream...\n')
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
                    if data_in_shmem['value'] == 'abort':
                        self._lock.release()
                        break
                else:
                    sleep(0.01)
                self._lock.release()
            else:
                # locked by a node, sleep and try again later
                sleep(0.01)

        self.shutdown()

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
        while self.shared_array[0, 0] == -1:
            # counter += 1
            # if counter == 10000:
            #     print(f'waiting. {self.shared_array[0, 0]}')
            #     counter = 0
            continue
        print(f'share memory has value of {self.shared_array[0, 0]}')
        print("shared_memory connected to by client")

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
        print('reached end. exiting')
        break


# server.start()
# first_msg = server.test_data_alone()
#
# while True:
#     new_msg = server.test_data_with_node()
#     if new_msg['time'] <= first_msg['time']:
#         sleep(1)
#         continue
#     else:
#         print(new_msg)
#         break
#
# server.test_lock()
# server.test_shared_memory()
# server.shutdown()
