import pygame
import socket
import pickle
import time
import logging
import os
from typing import Optional, Tuple

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

pygame.init()
os.environ['SDL_VIDEO_CENTERED'] = '1'
UI_WIDTH, UI_HEIGHT = 600, 400
GAME_WIDTH, GAME_HEIGHT = 960, 720  
MAP_WIDTH, MAP_HEIGHT = 1080, 720
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRID_COLOR = (200, 200, 200)
BORDER_COLOR = (100, 100, 100)
CELL_COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
FOOD_COLOR = (100, 255, 100)
ENEMY_COLOR = (255, 0, 0)
FONT = pygame.font.SysFont('Arial', 24, bold=True)
FOOTER_FONT = pygame.font.SysFont('Arial', 20, bold=False)
SMALL_FONT = pygame.font.SysFont('Arial', 20, bold=True)
WINNER_FONT = pygame.font.SysFont('Arial', 40, bold=True)
GRAY = (150, 150, 150)

MINIMAP_WIDTH = 200
MINIMAP_HEIGHT = 150
MINIMAP_SCALE_X = MINIMAP_WIDTH / MAP_WIDTH
MINIMAP_SCALE_Y = MINIMAP_HEIGHT / MAP_HEIGHT

class Camera:
    def __init__(self):
        self.zoom = 2.0
        self.target_zoom = 2.0
        self.offset_x = 0
        self.offset_y = 0
        self.target_offset_x = 0
        self.target_offset_y = 0
        self.base_zoom = 2.0
        self.min_zoom = 0.5
        self.max_zoom = 2.2
        self.smoothing = 0.1
        self.min_threshold = 20
        self.max_threshold = 50

    def update(self, player_x: float, player_y: float, player_size: float) -> None:
        self.target_offset_x = GAME_WIDTH / 2 - player_x * self.zoom
        self.target_offset_y = GAME_HEIGHT / 2 - player_y * self.zoom
        self.offset_x += (self.target_offset_x - self.offset_x) * self.smoothing
        self.offset_y += (self.target_offset_y - self.offset_y) * self.smoothing

        desired_diameter = min(GAME_WIDTH, GAME_HEIGHT) * 0.5
        if player_size > self.max_threshold:
            self.target_zoom = desired_diameter / (player_size * 2)
            self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))
            self.min_threshold = self.max_threshold
            self.max_threshold = player_size * 1.5
            logger.debug(f"Zooming out: size={player_size}, zoom={self.target_zoom}, new min={self.min_threshold}, new max={self.max_threshold}")
        elif player_size < self.min_threshold:
            self.target_zoom = desired_diameter / (player_size * 2)
            self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))
            self.max_threshold = self.min_threshold
            self.min_threshold = player_size * 0.5
            logger.debug(f"Zooming in: size={player_size}, zoom={self.target_zoom}, new min={self.min_threshold}, new max={self.max_threshold}")

        self.zoom += (self.target_zoom - self.zoom) * self.smoothing

    def apply(self, pos: Tuple[float, float]) -> Tuple[int, int]:
        x, y = pos
        screen_x = (x * self.zoom) + self.offset_x
        screen_y = (y * self.zoom) + self.offset_y
        return int(screen_x), int(screen_y)

class Client:
    def __init__(self, name: str, host: str, port: int):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name
        self.host = host
        self.port = port
        self.connected = False
        self.pid = None

    def connect(self) -> bool:
        try:
            self.socket.connect((self.host, self.port))
            self.socket.send(pickle.dumps(self.name))
            logger.info(f"Sent name: {self.name}")
            self.socket.setblocking(True)
            data = self.socket.recv(4096)
            msg_type, pid = pickle.loads(data)
            if msg_type == "PID":
                self.pid = pid
                logger.info(f"Received PID: {self.pid}")
            self.socket.setblocking(False)
            self.connected = True
            logger.info("Connected to server")
            return True
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            return False

    def send(self, payload: Tuple[float, float]) -> None:
        if self.connected:
            try:
                self.socket.send(pickle.dumps((1, payload)))
            except:
                self.connected = False
                logger.debug("Send failed, disconnected")

    def receive(self) -> Optional[dict]:
        if self.connected:
            try:
                data = self.socket.recv(4096)
                if data:
                    return pickle.loads(data)[1]
            except BlockingIOError:
                return None
            except:
                self.connected = False
                logger.debug("Receive failed, disconnected")
        return None

class GameView:
    def __init__(self):
        self.screen = pygame.display.set_mode((UI_WIDTH, UI_HEIGHT))
        pygame.display.set_caption("phago.io")
        self.clock = pygame.time.Clock()
        self.camera = Camera()
        self.minimap_surface = pygame.Surface((MINIMAP_WIDTH, MINIMAP_HEIGHT))
        self.start_time = None
        self.watermark = SMALL_FONT.render("phago.io - 23PT01 - 23PT14", True, (0, 0, 0))
        self.watermark.set_alpha(50)

    def resize_for_game(self):
        self.screen = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))

    def draw_grid(self) -> None:
        for x in range(0, MAP_WIDTH, 20):
            start_pos = self.camera.apply((x, 0))
            end_pos = self.camera.apply((x, MAP_HEIGHT))
            pygame.draw.line(self.screen, GRID_COLOR, start_pos, end_pos)
        for y in range(0, MAP_HEIGHT, 20):
            start_pos = self.camera.apply((0, y))
            end_pos = self.camera.apply((MAP_WIDTH, y))
            pygame.draw.line(self.screen, GRID_COLOR, start_pos, end_pos)

    def draw_map_border(self) -> None:
        top_left = self.camera.apply((0, 0))
        top_right = self.camera.apply((MAP_WIDTH, 0))
        bottom_left = self.camera.apply((0, MAP_HEIGHT))
        bottom_right = self.camera.apply((MAP_WIDTH, MAP_HEIGHT))
        pygame.draw.line(self.screen, BORDER_COLOR, top_left, top_right, 5)
        pygame.draw.line(self.screen, BORDER_COLOR, top_left, bottom_left, 5)
        pygame.draw.line(self.screen, BORDER_COLOR, bottom_left, bottom_right, 5)
        pygame.draw.line(self.screen, BORDER_COLOR, top_right, bottom_right, 5)

    def draw_minimap(self, state: dict, my_pid: int) -> None:
        self.minimap_surface.fill(BLACK)
        for fx, fy, _ in state['food']:
            minimap_x = fx * MINIMAP_SCALE_X
            minimap_y = fy * MINIMAP_SCALE_Y
            pygame.draw.circle(self.minimap_surface, FOOD_COLOR, (minimap_x, minimap_y), 1)
        for pid, (px, py, _, _, _) in state['players'].items():
            minimap_x = px * MINIMAP_SCALE_X
            minimap_y = py * MINIMAP_SCALE_Y
            if pid == my_pid:
                color = CELL_COLORS[pid % len(CELL_COLORS)]
            else:
                color = ENEMY_COLOR
            pygame.draw.circle(self.minimap_surface, color, (minimap_x, minimap_y), 2)
        pygame.draw.rect(self.minimap_surface, WHITE, (0, 0, MINIMAP_WIDTH, MINIMAP_HEIGHT), 2)
        self.screen.blit(self.minimap_surface, (10, GAME_HEIGHT - MINIMAP_HEIGHT - 10))

    def draw_menu(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        self.screen.fill(BLACK)
        default_ip = socket.gethostbyname(socket.gethostname())
        default_port = "1401"
        username = ""
        ip = default_ip
        port = default_port
        active_field = "ip"

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None, None, None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and username and ip and port:
                        return username, ip, port
                    elif event.key == pygame.K_TAB:
                        if active_field == "ip":
                            active_field = "port"
                        elif active_field == "port":
                            active_field = "username"
                        else:
                            active_field = "ip"
                    elif event.key == pygame.K_BACKSPACE:
                        if active_field == "username":
                            username = username[:-1]
                        elif active_field == "ip":
                            ip = ip[:-1]
                        else:
                            port = port[:-1]
                    elif event.unicode.isprintable():
                        if active_field == "username":
                            username += event.unicode
                        elif active_field == "ip":
                            ip += event.unicode
                        else:
                            port += event.unicode

            self.screen.fill(BLACK)
            branding = FONT.render("phago.io", True, WHITE)
            self.screen.blit(branding, (UI_WIDTH//2 - branding.get_width()//2, 30))
            ip_label = FONT.render("Enter IP:", True, WHITE)
            self.screen.blit(ip_label, (UI_WIDTH//2 - ip_label.get_width()//2, 80))
            ip_text = FONT.render(ip, True, WHITE if active_field == "ip" else GRAY)
            self.screen.blit(ip_text, (UI_WIDTH//2 - ip_text.get_width()//2, 110))
            port_label = FONT.render("Enter Port:", True, WHITE)
            self.screen.blit(port_label, (UI_WIDTH//2 - port_label.get_width()//2, 150))
            port_text = FONT.render(port, True, WHITE if active_field == "port" else GRAY)
            self.screen.blit(port_text, (UI_WIDTH//2 - port_text.get_width()//2, 180))
            username_label = FONT.render("Enter Username:", True, WHITE)
            self.screen.blit(username_label, (UI_WIDTH//2 - username_label.get_width()//2, 220))
            username_text = FONT.render(username, True, WHITE if active_field == "username" else GRAY)
            self.screen.blit(username_text, (UI_WIDTH//2 - username_text.get_width()//2, 250))
            credit1 = FOOTER_FONT.render("23XT46 - Computer Networks Lab", True, GRAY)
            self.screen.blit(credit1, (UI_WIDTH//2 - credit1.get_width()//2, UI_HEIGHT - 100))
            credit2 = FOOTER_FONT.render("23PT01 - Aakash Velusamy", True, GRAY)
            self.screen.blit(credit2, (UI_WIDTH//2 - credit2.get_width()//2, UI_HEIGHT - 70))
            credit3 = FOOTER_FONT.render("23PT14 - Kabilan S", True, GRAY)
            self.screen.blit(credit3, (UI_WIDTH//2 - credit3.get_width()//2, UI_HEIGHT - 40))
            pygame.display.flip()
            self.clock.tick(30)

    def draw_game(self, state: dict, my_pid: int) -> None:
        self.screen.fill(WHITE)
        if my_pid in state['players']:
            px, py, psize, _, _ = state['players'][my_pid]
            self.camera.update(px, py, psize)
        else:
            return
        self.draw_grid()
        self.draw_map_border()
        for fx, fy, fsize in state['food']:
            pos = self.camera.apply((fx, fy))
            pygame.draw.circle(self.screen, FOOD_COLOR, pos, fsize * self.camera.zoom)
        for pid, (px, py, psize, pname, pscore) in state['players'].items():
            color = CELL_COLORS[pid % len(CELL_COLORS)]
            pos = self.camera.apply((px, py))
            pygame.draw.circle(self.screen, color, pos, psize * self.camera.zoom)
            pygame.draw.circle(self.screen, BLACK, pos, psize * self.camera.zoom, 2)
            text = FONT.render(pname, True, WHITE)
            text_pos = (pos[0] - text.get_width()/2, pos[1] - text.get_height()/2)
            self.screen.blit(text, text_pos)
        self.draw_minimap(state, my_pid)

        # Timer at the center (top)
        timer = FONT.render(f"Time: {state['time_left']//60:02d}:{state['time_left']%60:02d}", True, BLACK)
        timer_x = GAME_WIDTH // 2 - timer.get_width() // 2
        self.screen.blit(timer, (timer_x, 10))

        # Score at the top right
        my_score = FONT.render(f"Score: {state['players'][my_pid][4]}", True, BLACK)
        score_x = GAME_WIDTH - my_score.get_width() - 10
        self.screen.blit(my_score, (score_x, 10))

        # Leaderboard at the top left
        sorted_scores = sorted(state['players'].items(), key=lambda x: x[1][4], reverse=True)
        for i, (pid, (_, _, _, name, score)) in enumerate(sorted_scores[:5]):
            score_text = FONT.render(f"{name}: {int(score)}", True, BLACK)
            self.screen.blit(score_text, (10, 10 + i * 25))

        # Draw watermark at bottom right
        self.screen.blit(self.watermark, (GAME_WIDTH - self.watermark.get_width() - 10, GAME_HEIGHT - self.watermark.get_height() - 10))
        pygame.display.flip()
        self.clock.tick(FPS)

    def display_winner(self, state: dict) -> None:
        sorted_players = sorted(state['players'].items(), key=lambda x: x[1][4], reverse=True)
        if sorted_players:
            winner_pid, (_, _, _, winner_name, winner_score) = sorted_players[0]
            winner_text = f"Winner: {winner_name} with {int(winner_score)} points!"
        else:
            winner_text = "No players in the game!"
        
        self.screen.fill(BLACK)
        winner_surface = WINNER_FONT.render(winner_text, True, WHITE)
        self.screen.blit(winner_surface, (GAME_WIDTH//2 - winner_surface.get_width()//2, GAME_HEIGHT//2 - winner_surface.get_height()//2))
        pygame.display.flip()
        pygame.time.wait(3000)

def main():
    view = GameView()
    username, ip, port = view.draw_menu()
    if not username or not ip or not port:
        pygame.quit()
        return
    try:
        port_num = int(port)
    except ValueError:
        logger.error("Invalid port number")
        pygame.quit()
        return
    client = Client(username, ip, port_num)
    if not client.connect():
        logger.error("Connection failed, exiting")
        pygame.quit()
        return

    view.resize_for_game()
    view.start_time = time.time()

    running = True
    game_ended = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            elif event.type == pygame.WINDOWMOVED:
                pygame.event.clear()
                continue

        mx, my = pygame.mouse.get_pos()
        client.send((mx, my))
        state = client.receive()
        if state:
            view.draw_game(state, client.pid)
            elapsed = time.time() - view.start_time
            if state['time_left'] <= 0 and not game_ended and elapsed > 5:
                view.display_winner(state)
                game_ended = True
                pygame.time.wait(1000)
                running = False
        time.sleep(0.001)
    pygame.quit()

if __name__ == "__main__":
    main()
