
from netstring import *
import marshal, traceback, time, re, urllib
from disco_worker import re_reader

DISCO_NEW_JOB_URL = "/disco/job/new"
DISCO_RESULTS = "/disco/ctrl/get_results"
HTTP_PORT = "8989"

def default_partition(key, nr_reduces):
        return hash(str(key)) % nr_reduces

def make_range_partition(min_val, max_val):
        r = max_val - min_val
        f = "lambda k, n: int(round(float(int(k) - %d) / %d * (n - 1)))" %\
                (min_val, r)
        return eval(f)

def map_line_reader(fd, sze, fname):
        for x in re_reader("(.*?)\n", fd, sze, fname):
                yield x[0]
        
def job(master, name, input_files, fun_map, map_reader = map_line_reader,\
        reduce = None, partition = default_partition, combiner = None,\
        nr_maps = None, nr_reduces = None, sort = True,\
        mem_sort_limit = 256 * 1024**2, async = False):

        if len(input_files) < 1:
                raise "Must have at least one input file"

        if re.search("\W", name):
                raise "Only characters in [a-zA-Z0-9_] are allowed in job name"

        req = {}
        req["name"] = "%s@%d" % (name, int(time.time()))
        req["input"] = " ".join(input_files)
        req["map_reader"] = marshal.dumps(map_reader.func_code)
        req["map"] = marshal.dumps(fun_map.func_code)
        req["partition"] = marshal.dumps(partition.func_code)

        if not nr_maps or nr_maps > len(input_files):
                nr_maps = len(input_files)
        req["nr_maps"] = str(nr_maps)
        
        req["sort"] = str(int(sort))
        req["mem_sort_limit"] = str(mem_sort_limit)

        if reduce:
                req["reduce"] = marshal.dumps(reduce.func_code)
                nr_reduces = nr_reduces or max(nr_maps / 2, 1)
        else:
                nr_reduces = nr_reduces or 1

        req["nr_reduces"] = str(nr_reduces)

        if combiner:
                req["combiner"] = marshal.dumps(combiner.func_code)

        msg = encode_netstring_fd(req)
        if master.startswith("stdout:"):
                print msg,
        elif master.startswith("disco:"):
                reply = urllib.urlopen(master.replace("disco:", "http:", 1)\
                        + DISCO_NEW_JOB_URL, msg)
                r = reply.read()
                if "job started" not in r:
                        raise "Failed to start a job. Server replied: " + r
                reply.close()
        else:
                raise "Unknown host specifier: %s" % master

        if not async:
                return wait_job(master, req['name']) 
        else:
                return name

def wait_job(master, name, poll_interval = 5, timeout = None):
        url = master.replace("disco:", "http:", 1)\
                + DISCO_RESULTS + "?name=" + name
        t = time.time()
        print url
        while True:
                time.sleep(poll_interval)
                R = urllib.urlopen(url).read()
                R = eval(R)
                if R[0] == "ready":
                        return R[1]
                if R[0] != "active":
                        raise "Job failed"
                if timeout and time.time() - t > timeout:
                        raise "Timeout"

def result_iterator(results, notifier = None):
        results.sort()
        for part_id, url in results:
                host, fname = url[8:].split("/", 1)
                ext_host = host + ":" + HTTP_PORT
                ext_file = "/" + fname

                http = httplib.HTTPConnection(ext_host)
                http.request("GET", ext_file, "")
                fd = http.getresponse()
                if fd.status != 200:
                        raise "HTTP error %d" % fd.status
                
                sze = int(fd.getheader("content-length"))

                if notifier:
                        notifier(part_id, url)

                for x in re_reader("(.*?) (.*?)\000", fd, sze, fname):
                        yield x
                http.close()







                


        


        





        




