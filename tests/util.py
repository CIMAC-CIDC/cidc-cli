from threading import Thread


class ExceptionCatchingThread(Thread):
    """
    A thread that throws any exception it encounters while
    running when its `join` method is called.
    """

    def __init__(self, target):
        Thread.__init__(self)
        self.target = target

    def run(self):
        self.exc = None
        try:
            self.target()
        except:
            import sys

            self.exc = sys.exc_info()

    def join(self):
        Thread.join(self)
        if self.exc:
            msg = "Thread '%s' threw an exception: %s" % (self.getName(), self.exc[1])
            new_exc = self.exc[0](msg)
            new_exc.with_traceback(self.exc[2])
            raise new_exc
