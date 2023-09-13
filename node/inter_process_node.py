from multiprocessing.managers import BaseManager
from multiprocessing import shared_memory
import numpy as np
from time import sleep
from queue import Queue, Empty
from threading import Thread


class InterProcessNode:
    def __init__(self, ipc_address, shmem_name, shmem_template, queue):
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
                self._lock.release()
                self._api = self.connection_manager.get_data_api()
                break
            except (EOFError, ConnectionRefusedError):
                continue
        print('connected to server')

        # init shared memory
        print('connecting to shared_memory')
        while True:
            try:
                self.shm = shared_memory.SharedMemory(create=False, name=shmem_name, size=shmem_template.nbytes)
                buffer = self.shm.buf
                self.shared_array = np.ndarray(shmem_template.shape, dtype=np.int64, buffer=buffer)
                break
            except FileNotFoundError:
                continue
        print('connected to shared memory')

        # link to feed queue
        self.feed_queue = queue

        # start the service
        Thread(target=self.start, name='inter_process_node', daemon=True).start()

    def start(self):
        print('subscribed to data stream...\n')
        while True:
            # TODO: wrap in try-except to re-establish lost connections
            try:
                new_results = self.feed_queue.get_nowait()
                print(f'data extracted from queue: {new_results["value"]}')
            except Empty:
                # no new results, wait a bit and try again later
                sleep(0.1)
                continue

            if self._lock.acquire(block=True):
                # when there is new data available, send it to the server
                self._api.update_data_object(new_results['time'], new_results['value'])
                self.shared_array[:] = new_results['array'][:]
                self._lock.release()
                print('data is shared\n')
                # exit condition:
                if new_results['value'] == 'break':
                    print('reached end')
                    break
            else:
                # locked by server, sleep and try again later
                sleep(1)

        self.shutdown()

    def test_data(self):
        print(self._api.get_data_object())
        self._api.update_data_object(2, 7)
        print(self._api.get_data_object())

    def test_lock(self):
        print('releasing lock')
        self._lock.release()

    def test_shared_memory(self):
        print(f'share memory has value of {self.shared_array[0, 0]}')
        self.shared_array[0, 0] = 1
        print(f'share memory has value of {self.shared_array[0, 0]}')

    def shutdown(self):
        print('shutting down')
        node.shm.close()
        node.shm.unlink()


address = ('localhost', 6000)
SHM_NAME = "NUMPY_SHMEM"
array_template = np.ones(shape=(200, 200), dtype=np.int64)
data_queue = Queue(maxsize=1)

node = InterProcessNode(ipc_address=address, shmem_name=SHM_NAME, shmem_template=array_template, queue=data_queue)

# let's feed some data in:
sleep(3)
feed1 = {'time': 1, 'value': 'good', 'array': np.full_like(array_template, fill_value=1)}
print('putting feed1 into queue')
data_queue.put(feed1)
sleep(5)

feed2 = {'time': 2, 'value': 'still good', 'array': np.full_like(array_template, fill_value=5)}
print('putting feed2 into queue')
data_queue.put(feed2)
sleep(5)

feed3 = {'time': 3, 'value': 'break', 'array': np.full_like(array_template, fill_value=-1)}
print('putting feed3 into queue')
data_queue.put(feed3)
sleep(1)

# node.start()
# node.test_data()
# node.test_lock()
# node.test_shared_memory()
# print('shutting down')
# node.shm.close()
# node.shm.unlink()
