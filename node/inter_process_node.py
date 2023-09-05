from multiprocessing.managers import BaseManager, MakeProxyType
from multiprocessing import shared_memory
import numpy as np
from time import sleep


class EventManager(BaseManager): pass
EventManager.register('get_lock')
EventManager.register("get_api")


class InterProcessNode:
    def __init__(self, ipc_address, shared_mem_name, shared_mem_template=None):
        # initiate connections and shared memory blocks
        self.manager = EventManager(address=ipc_address, authkey=b'secret password')

    def start(self):
        print('waiting for server')
        while True:
            try:
                self.manager.connect()
                self._lock = self.manager.get_lock()
                self._api = self.manager.get_api()
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


# manager_lock = manager.get_access()
# f = manager.get_foo()
# print(f.get_x())
# f.set_x(7)
# f.append_x('3', 19)
# print(f.get_x())
# # f.overwrite_x('new type')
# manager_lock.release()
# print('lock acquired and released')

