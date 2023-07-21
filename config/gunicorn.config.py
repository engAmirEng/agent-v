from gevent import monkey

worker_class = "gevent"


def post_fork(server, worker):
    # patch calls for gevent workers #
    monkey.patch_all()
    #       #       #       #       #
