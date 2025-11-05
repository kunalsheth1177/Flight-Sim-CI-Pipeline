from __future__ import annotations

import json
import queue
import random
import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class RpcConfig:
    host: str = "127.0.0.1"
    port: int = 0  # 0 => OS picks an ephemeral port
    loss_p: float = 0.0
    latency_ms: int = 0
    rand_seed: int = 0


class UdpServer:
    def __init__(self, config: RpcConfig) -> None:
        self.config = config
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((config.host, config.port))
        self.address = self.sock.getsockname()
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._stop = threading.Event()
        # Queue of (apply_time_s, dict)
        self._pending: "queue.PriorityQueue[Tuple[float, dict]]" = queue.PriorityQueue()
        self._rand = random.Random(int(config.rand_seed))

    def start(self) -> None:
        self._rx_thread.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            self.sock.close()
        except Exception:
            pass
        self._rx_thread.join(timeout=1.0)

    def _rx_loop(self) -> None:
        self.sock.settimeout(0.2)
        while not self._stop.is_set():
            try:
                data, _peer = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                msg = json.loads(data.decode("utf-8"))
                # Packet loss
                if self._rand.random() < float(self.config.loss_p):
                    continue
                latency_s = max(0.0, float(self.config.latency_ms) / 1000.0)
                apply_time = time.monotonic() + latency_s
                self._pending.put((apply_time, msg))
            except Exception:
                # Drop malformed
                continue

    def poll_next(self, now_s: Optional[float] = None) -> Optional[dict]:
        now = time.monotonic() if now_s is None else now_s
        try:
            while True:
                apply_time, msg = self._pending.get_nowait()
                if apply_time <= now:
                    return msg
                else:
                    # Not ready yet, put back and exit
                    self._pending.put((apply_time, msg))
                    return None
        except queue.Empty:
            return None


class UdpClient:
    def __init__(self, server_addr: Tuple[str, int]) -> None:
        self.server_addr = server_addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, thrust_01: float, pitch_deg: float) -> None:
        msg = json.dumps({"thrust_01": float(thrust_01), "pitch_deg": float(pitch_deg)})
        try:
            self.sock.sendto(msg.encode("utf-8"), self.server_addr)
        except Exception:
            pass

