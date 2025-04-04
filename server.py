import socket
import threading
import random
import time
import pickle
import logging
import pygame
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

pygame.init()
UI_WIDTH, UI_HEIGHT = 600, 400
UI_SCREEN = pygame.display.set_mode((UI_WIDTH, UI_HEIGHT))
pygame.display.set_caption("phago.io - Server Setup")
FONT = pygame.font.SysFont('Arial', 24, bold=True)
FOOTER_FONT = pygame.font.SysFont('Arial', 20, bold=False)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)

WIDTH, HEIGHT = 1080, 720
GAME_DURATION = 300
BUFFER_SIZE = 4096
MSG_UPDATE = 1

class Player:
    def __init__(self, pid: int, name: str, x: float, y: float):
        self.pid = pid
        self.name = name
        self.x = x
        self.y = y
        self.size = 20
        self.score = 0
        self.sensitivity = 1.5
        self.last_dx = 0 
        self.last_dy = 0 

    def move(self, mx: float, my: float) -> None:
        dx = mx - self.x
        dy = my - self.y
        dist = (dx**2 + dy**2)**0.5
        speed = (1000 / self.size) * 1.1 * self.sensitivity

        border_margin = 50
        speed_boost = 1.0
        if self.x < border_margin or self.x > WIDTH - border_margin:
            speed_boost = 1.5
        if self.y < border_margin or self.y > HEIGHT - border_margin:
            speed_boost = max(speed_boost, 1.5)

        speed *= speed_boost

        if dist > 0:
            self.last_dx = dx / dist  
            self.last_dy = dy / dist
            self.x += (dx / dist) * speed * (1/60)
            self.y += (dy / dist) * speed * (1/60)
        elif self.last_dx != 0 or self.last_dy != 0:
            self.x += self.last_dx * speed * (1/60)
            self.y += self.last_dy * speed * (1/60)

        self.x = max(self.size * 0.5, min(WIDTH - self.size * 0.5, self.x))
        self.y = max(self.size * 0.5, min(HEIGHT - self.size * 0.5, self.y))
        logger.debug(f"Player {self.pid} moved to ({self.x:.1f}, {self.y:.1f})")

class Food:
    def __init__(self, width: int, height: int):
        self.x = random.randint(0, width - 10)
        self.y = random.randint(0, height - 10)
        self.size = 5

class Game:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.players: Dict[int, Player] = {}
        self.food: List[Food] = [Food(width, height) for _ in range(75)]
        self.lock = threading.Lock()
        self.start_time = None
        self.last_decay = time.time()

    def add_player(self, pid: int, name: str) -> None:
        with self.lock:
            if not self.players:
                self.start_time = time.time()
                logger.info("First player joined, starting game timer")
            self.players[pid] = Player(pid, name, random.randint(0, self.width), random.randint(0, self.height))
            logger.info(f"Added player {pid}: {name}")

    def remove_player(self, pid: int) -> None:
        with self.lock:
            if pid in self.players:
                del self.players[pid]
                logger.info(f"Removed player {pid}")

    def move_players(self, pid: int, mx: float, my: float) -> None:
        with self.lock:
            if pid in self.players:
                self.players[pid].move(mx, my)

    def check_eat(self) -> None:
        with self.lock:
            players_list = list(self.players.values())
            for p1 in players_list:
                for p2 in players_list:
                    if p1 == p2:
                        continue
                    if p1.size > p2.size:
                        dist = ((p1.x - p2.x)**2 + (p1.y - p2.y)**2)**0.5
                        if dist < p1.size:
                            logger.info(f"Player {p1.pid} (size {p1.size}) ate {p2.pid} (size {p2.size})")
                            p1.size += p2.size * 0.5
                            p1.score += int(p2.score / 2)
                            p2.size = 20
                            p2.score = 0
                            logger.debug(f"Player {p1.pid} score: {p1.score}, Player {p2.pid} score reset to: {p2.score}")
                            p2.x = random.randint(0, self.width - p2.size)
                            p2.y = random.randint(0, self.height - p2.size)

                for food in self.food[:]:
                    dist = ((p1.x - food.x)**2 + (p1.y - food.y)**2)**0.5
                    # Eat food when the blob's edge touches the food (use sum of radii)
                    if dist < (p1.size + food.size):
                        p1.size += food.size
                        p1.score += food.size
                        self.food.remove(food)
                        self.food.append(Food(self.width, self.height))
                        logger.debug(f"Player {p1.pid} ate food at ({food.x}, {food.y})")

    def decay(self) -> None:
        with self.lock:
            now = time.time()
            if now - self.last_decay >= 1.0:
                for p in self.players.values():
                    if p.size > 20:
                        p.size *= 0.98
                        logger.debug(f"Player {p.pid} decayed to {p.size:.1f}")
                self.last_decay = now

    def get_state(self) -> Dict:
        with self.lock:
            if self.start_time is None:
                elapsed = GAME_DURATION
            else:
                elapsed = int(GAME_DURATION - (time.time() - self.start_time))
            return {
                'players': {p.pid: (p.x, p.y, p.size, p.name, int(p.score)) for p in self.players.values()},
                'food': [(f.x, f.y, f.size) for f in self.food],
                'time_left': elapsed if elapsed > 0 else 0
            }

class Server:
    def __init__(self, host: str, port: int):
        self.game = Game(WIDTH, HEIGHT)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.bind((host, port))
        except Exception as e:
            logger.error(f"Failed to bind to {host}:{port}: {e}")
            raise
        self.socket.listen(5)
        self.pid_counter = 0
        self.connections: Dict[int, socket.socket] = {}
        logger.info(f"Server running on {host}:{port}")

    def handle_client(self, conn: socket.socket, addr: Tuple[str, int], pid: int, name: str) -> None:
        logger.info(f"Starting client handler for {pid}: {name}")
        self.game.add_player(pid, name)
        self.connections[pid] = conn
        conn.setblocking(False)
        try:
            conn.send(pickle.dumps(("PID", pid)))
        except Exception as e:
            logger.error(f"Failed to send PID to {addr}: {e}")
            return
        last_sent = time.time()
        try:
            while True:
                try:
                    data = conn.recv(BUFFER_SIZE)
                    if not data:
                        logger.debug(f"No data from {addr}, closing")
                        break
                    _, (mx, my) = pickle.loads(data)
                    logger.debug(f"Received update from {pid}: ({mx:.1f}, {my:.1f})")
                    self.game.move_players(pid, mx, my)
                    self.game.check_eat()
                    self.game.decay()
                except BlockingIOError:
                    pass
                except Exception as e:
                    logger.error(f"Receive error from {addr}: {e}")
                    break

                if time.time() - last_sent > 0.01:
                    state = self.game.get_state()
                    try:
                        conn.send(pickle.dumps((MSG_UPDATE, state)))
                        last_sent = time.time()
                        logger.debug(f"Sent state to {pid}")
                    except Exception as e:
                        logger.error(f"Send failed to {addr}: {e}")
                        break
                time.sleep(0.005)
        except Exception as e:
            logger.error(f"Client {addr} crashed: {e}")
        finally:
            self.game.remove_player(pid)
            self.connections.pop(pid, None)
            conn.close()
            logger.info(f"Client {addr} disconnected")

    def run(self) -> None:
        while True:
            try:
                self.socket.settimeout(10)
                conn, addr = self.socket.accept()
                logger.info(f"New connection from {addr}")
                try:
                    conn.setblocking(True)
                    conn.settimeout(5)
                    name = pickle.loads(conn.recv(BUFFER_SIZE))
                    logger.info(f"Received name from {addr}: {name}")
                    thread = threading.Thread(target=self.handle_client, args=(conn, addr, self.pid_counter, name))
                    thread.daemon = True
                    thread.start()
                    self.pid_counter += 1
                except Exception as e:
                    logger.error(f"Error accepting {addr}: {e}")
                    conn.close()
            except socket.timeout:
                logger.warning("Socket accept timed out, continuing...")
                continue
            except Exception as e:
                logger.error(f"Server error: {e}")
                break

def get_server_config() -> Tuple[str, int]:
    default_ip = socket.gethostbyname(socket.gethostname())
    default_port = "1401"
    ip = default_ip
    port = default_port
    active_field = "ip"
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None, None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if ip and port:
                        try:
                            port_num = int(port)
                            return ip, port_num
                        except ValueError:
                            continue
                elif event.key == pygame.K_TAB:
                    active_field = "port" if active_field == "ip" else "ip"
                elif event.key == pygame.K_BACKSPACE:
                    if active_field == "ip":
                        ip = ip[:-1]
                    else:
                        port = port[:-1]
                elif event.unicode.isprintable():
                    if active_field == "ip":
                        ip += event.unicode
                    else:
                        port += event.unicode

        UI_SCREEN.fill(BLACK)
        branding = FONT.render("phago.io", True, WHITE)
        UI_SCREEN.blit(branding, (UI_WIDTH//2 - branding.get_width()//2, 30))
        title = FONT.render("Configure Server", True, WHITE)
        UI_SCREEN.blit(title, (UI_WIDTH//2 - title.get_width()//2, 90))
        ip_label = FONT.render("Enter IP:", True, WHITE)
        UI_SCREEN.blit(ip_label, (UI_WIDTH//2 - ip_label.get_width()//2, 140))
        ip_text = FONT.render(ip, True, WHITE if active_field == "ip" else GRAY)
        UI_SCREEN.blit(ip_text, (UI_WIDTH//2 - ip_text.get_width()//2, 170))
        port_label = FONT.render("Enter Port:", True, WHITE)
        UI_SCREEN.blit(port_label, (UI_WIDTH//2 - port_label.get_width()//2, 220))
        port_text = FONT.render(port, True, WHITE if active_field == "port" else GRAY)
        UI_SCREEN.blit(port_text, (UI_WIDTH//2 - port_text.get_width()//2, 250))
        credit1 = FOOTER_FONT.render("23XT46 - Computer Networks Lab", True, GRAY)
        UI_SCREEN.blit(credit1, (UI_WIDTH//2 - credit1.get_width()//2, UI_HEIGHT - 100))
        credit2 = FOOTER_FONT.render("23PT01 - Aakash Velusamy", True, GRAY)
        UI_SCREEN.blit(credit2, (UI_WIDTH//2 - credit2.get_width()//2, UI_HEIGHT - 70))
        credit3 = FOOTER_FONT.render("23PT14 - Kabilan S", True, GRAY)
        UI_SCREEN.blit(credit3, (UI_WIDTH//2 - credit3.get_width()//2, UI_HEIGHT - 40))
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    try:
        host, port = get_server_config()
        if host is None or port is None:
            pygame.quit()
            exit()
        server = Server(host, port)
        pygame.quit()
        server.run()
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        pygame.quit()
