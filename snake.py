#!/usr/bin/env python3
"""
贪吃蛇 — Pygame 实现
====================
碰墙即死贪吃蛇，支持速度递增、连击系统，无音效。

打包命令:
    pyinstaller --onefile --noconsole --collect-all pygame --hidden-import pygame snake.py
"""

import pygame
import sys
import os
import random


# ============================================================================
# 常量
# ============================================================================

GRID_COUNT   = 20                     # 每行/列格子数
CELL_SIZE    = 40                     # 每格像素
WINDOW_SIZE  = GRID_COUNT * CELL_SIZE # 800×800
FPS          = 60

INITIAL_SPEED    = 5.0                # 初始速度（格/秒）
SPEED_STEP       = 0.5                # 每次加速步长
MAX_SPEED        = 12.0                # 最大速度 = 初始 × 2
FOODS_PER_LEVEL  = 4                  # 每吃 N 个食物升速一次
SCORE_PER_FOOD   = 10                 # 每个食物得分

# 方向向量（x, y）
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)

# 游戏状态
(STATE_START,
 STATE_PLAYING,
 STATE_PAUSED,
 STATE_GAME_OVER) = range(4)


# ============================================================================
# 颜色主题（Catppuccin Mocha 暗色风格）
# ============================================================================

class C:
    BG           = (18,  18,  36 )
    GRID_LINE    = (28,  28,  52 )
    SNAKE_HEAD   = (100, 220, 100)
    SNAKE_BODY   = (60,  180, 60 )
    FOOD         = (255, 70,  70 )
    FOOD_HL      = (255, 140, 140)
    FOOD_STEM    = (100, 180, 70 )
    FOOD_LEAF    = (100, 200, 80 )
    TEXT         = (230, 230, 245)
    ACCENT       = (255, 200, 80 )
    SUBTEXT      = (150, 150, 170)
    OVERLAY      = (0,   0,   0,  180)


# ============================================================================
# 高分文件读写
# ============================================================================

def _exe_dir() -> str:
    """返回 exe（或 .py）所在目录。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _highscore_path() -> str:
    return os.path.join(_exe_dir(), 'highscore.txt')


def load_highscore() -> int:
    try:
        with open(_highscore_path(), 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_highscore(score: int) -> None:
    try:
        with open(_highscore_path(), 'w') as f:
            f.write(str(score))
    except OSError:
        pass


# ============================================================================
# 游戏对象
# ============================================================================

class Snake:
    """蛇：身体链表 + 方向控制 + 渲染。"""

    def __init__(self):
        self.reset()

    # ---------- 重置 ----------

    def reset(self) -> None:
        cx, cy = GRID_COUNT // 2, GRID_COUNT // 2
        self.body           = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction      = RIGHT
        self.next_direction = RIGHT
        self.grow_pending   = 0

    # ---------- 属性 ----------

    @property
    def head(self) -> tuple[int, int]:
        return self.body[0]

    # ---------- 控制 ----------

    def change_direction(self, new_dir: tuple[int, int]) -> None:
        """缓冲方向变更（禁止 180° 掉头）。"""
        opposite = (-self.direction[0], -self.direction[1])
        if new_dir != opposite:
            self.next_direction = new_dir

    # ---------- 移动 ----------

    def move(self) -> bool:
        """前进一步。返回 False 表示撞墙或撞到自己 → 游戏结束。"""
        self.direction = self.next_direction

        hx, hy = self.head
        dx, dy = self.direction
        nx, ny = hx + dx, hy + dy

        # 撞墙检测
        if not (0 <= nx < GRID_COUNT and 0 <= ny < GRID_COUNT):
            return False

        # 头撞身体（排除尾尖，因为尾尖即将移走）
        if (nx, ny) in self.body[:-1]:
            return False

        new_head = (nx, ny)

        self.body.insert(0, new_head)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()
        return True

    def grow(self, n: int = 1) -> None:
        self.grow_pending += n

    # ---------- 渲染 ----------

    def draw(self, surface: pygame.Surface) -> None:
        body_len = len(self.body)
        for i, (sx, sy) in enumerate(self.body):
            rect = pygame.Rect(sx * CELL_SIZE, sy * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if i == 0:
                pygame.draw.rect(surface, C.SNAKE_HEAD, rect, border_radius=7)
                self._draw_eyes(surface, sx, sy)
            else:
                ratio = i / body_len
                color = (
                    max(20, int(C.SNAKE_BODY[0] * (1 - ratio * 0.45))),
                    max(40, int(C.SNAKE_BODY[1] * (1 - ratio * 0.45))),
                    max(20, int(C.SNAKE_BODY[2] * (1 - ratio * 0.45))),
                )
                pygame.draw.rect(surface, color, rect, border_radius=5)

    def _draw_eyes(self, surface: pygame.Surface, sx: int, sy: int) -> None:
        px, py = sx * CELL_SIZE, sy * CELL_SIZE
        dx, dy = self.direction
        er = 4  # 眼白半径
        pr = 2  # 瞳孔半径

        if   dx ==  1:  e1, e2 = (px + 29, py + 10), (px + 29, py + 28)
        elif dx == -1:  e1, e2 = (px + 11, py + 10), (px + 11, py + 28)
        elif dy == -1:  e1, e2 = (px + 10, py + 11), (px + 28, py + 11)
        else:           e1, e2 = (px + 10, py + 29), (px + 28, py + 29)

        for ex, ey in (e1, e2):
            pygame.draw.circle(surface, (255, 255, 255), (ex, ey), er)
            pygame.draw.circle(surface, (0, 0, 0), (ex + 1, ey), pr)


class Food:
    """食物：随机生成 + 渲染（红色苹果风格）。"""

    def __init__(self):
        self.position = (0, 0)

    def spawn(self, snake_body: list[tuple[int, int]]) -> None:
        occupied = set(snake_body)
        available = [
            (x, y)
            for x in range(GRID_COUNT)
            for y in range(GRID_COUNT)
            if (x, y) not in occupied
        ]
        if available:
            self.position = random.choice(available)

    def draw(self, surface: pygame.Surface) -> None:
        fx, fy = self.position
        cx = fx * CELL_SIZE + CELL_SIZE // 2
        cy = fy * CELL_SIZE + CELL_SIZE // 2
        r = CELL_SIZE // 2 - 3

        # 身体
        pygame.draw.circle(surface, C.FOOD, (cx, cy), r)
        # 高光
        hl_x, hl_y = cx - r // 3, cy - r // 3
        pygame.draw.circle(surface, C.FOOD_HL, (hl_x, hl_y), r // 3)
        # 茎
        stem_top = cy - r
        pygame.draw.line(surface, C.FOOD_STEM, (cx, stem_top), (cx, stem_top - 7), 2)
        # 小叶
        leaf_rect = pygame.Rect(cx, stem_top - 12, 9, 7)
        pygame.draw.ellipse(surface, C.FOOD_LEAF, leaf_rect)


# ============================================================================
# 游戏主控
# ============================================================================

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("贪吃蛇 - 番茄钟版")

        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        self.clock  = pygame.time.Clock()

        # 加载中文字体（按优先级尝试多个系统字体，确保兼容不同 Windows 版本）
        self._font_name = self._find_chinese_font()
        self.font_large  = pygame.font.SysFont(self._font_name, 56, bold=True)
        self.font_medium = pygame.font.SysFont(self._font_name, 32, bold=True)
        self.font_small  = pygame.font.SysFont(self._font_name, 22)

        # 游戏对象
        self.snake = Snake()
        self.food  = Food()

        # 运行时状态
        self.state         = STATE_START
        self.score         = 0
        self.combo         = 0
        self.foods_eaten   = 0              # 本次游戏累计吃到的食物数
        self.elapsed       = 0.0            # 游戏计时（秒，不含暂停）
        self.high_score    = load_highscore()
        self.speed         = INITIAL_SPEED
        self.move_acc      = 0.0            # 移动累加器

        # 初始食物
        self.food.spawn(self.snake.body)

    @staticmethod
    def _find_chinese_font() -> str:
        """按优先级查找系统可用的中文字体名。"""
        candidates = [
            "microsoftyahei",   # 微软雅黑 (Win 7+)
            "simhei",           # 黑体
            "simsun",           # 宋体
            "fangsong",         # 仿宋
            "kaiti",            # 楷体
            "notosanscjk",      # 部分系统的 Noto Sans CJK
            "arialunicode",     # Arial Unicode MS
        ]
        available = {f.lower() for f in pygame.font.get_fonts()}
        for name in candidates:
            if name in available:
                return name
        return pygame.font.get_default_font()  # 兜底（会缺中文，但不崩溃）

    # ==================================================================
    # 主循环
    # ==================================================================

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._on_event(event)

            self._update(dt)
            self._draw()

    # ==================================================================
    # 事件分发
    # ==================================================================

    def _on_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        key = event.key

        # ESC 退出
        if key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

        # —— 开始画面：任意键进入游戏 ——
        if self.state == STATE_START:
            self._start_game()
            return

        # —— 游戏结束：仅 R 键有效 ——
        if self.state == STATE_GAME_OVER:
            if key == pygame.K_r:
                self._restart()
            return

        # —— 游戏中 ——
        if self.state == STATE_PLAYING:
            if key == pygame.K_UP:
                self.snake.change_direction(UP)
            elif key == pygame.K_DOWN:
                self.snake.change_direction(DOWN)
            elif key == pygame.K_LEFT:
                self.snake.change_direction(LEFT)
            elif key == pygame.K_RIGHT:
                self.snake.change_direction(RIGHT)
            elif key == pygame.K_p:
                self.state = STATE_PAUSED
            return

        # —— 暂停中 ——
        if self.state == STATE_PAUSED:
            if key == pygame.K_p:
                self.state = STATE_PLAYING
            return

    # ==================================================================
    # 更新逻辑
    # ==================================================================

    def _update(self, dt: float) -> None:
        if self.state != STATE_PLAYING:
            return

        # 累计游戏时间
        self.elapsed += dt

        # 移动累加器 → 帧率无关的精准移动
        self.move_acc += dt
        interval = 1.0 / self.speed

        while self.move_acc >= interval:
            self.move_acc -= interval
            if not self.snake.move():
                self._on_game_over()
                return
            if self.snake.head == self.food.position:
                self._on_eat()

    # ==================================================================
    # 游戏事件
    # ==================================================================

    def _start_game(self) -> None:
        """从开始画面进入游戏。"""
        self.state = STATE_PLAYING

    def _on_eat(self) -> None:
        """吃到食物。"""
        self.snake.grow()
        self.foods_eaten += 1
        self.score += SCORE_PER_FOOD
        self.combo += 1

        # 每吃 FOODS_PER_LEVEL 个升速一次
        self.speed = min(
            INITIAL_SPEED + (self.foods_eaten // FOODS_PER_LEVEL) * SPEED_STEP,
            MAX_SPEED,
        )

        self.food.spawn(self.snake.body)

    def _on_game_over(self) -> None:
        """撞到自己 → 游戏结束。"""
        self.state = STATE_GAME_OVER
        self.combo = 0

        # 更新最高分
        if self.score > self.high_score:
            self.high_score = self.score
            save_highscore(self.high_score)

    def _restart(self) -> None:
        """重置所有状态，重新开始。"""
        self.snake.reset()
        self.food.spawn(self.snake.body)
        self.state       = STATE_PLAYING
        self.score       = 0
        self.combo       = 0
        self.foods_eaten = 0
        self.elapsed     = 0.0
        self.speed       = INITIAL_SPEED
        self.move_acc    = 0.0

    # ==================================================================
    # 渲染管线
    # ==================================================================

    def _draw(self) -> None:
        self.screen.fill(C.BG)

        # 网格线
        for i in range(GRID_COUNT + 1):
            pos = i * CELL_SIZE
            pygame.draw.line(self.screen, C.GRID_LINE, (pos, 0), (pos, WINDOW_SIZE))
            pygame.draw.line(self.screen, C.GRID_LINE, (0, pos), (WINDOW_SIZE, pos))

        # 食物 & 蛇
        self.food.draw(self.screen)
        self.snake.draw(self.screen)

        # 状态覆盖层
        if   self.state == STATE_START:     self._draw_overlay_start()
        elif self.state == STATE_PAUSED:    self._draw_overlay_paused()
        elif self.state == STATE_GAME_OVER: self._draw_overlay_gameover()

        pygame.display.flip()

    # ==================================================================
    # 覆盖层画面
    # ==================================================================

    def _draw_overlay_start(self) -> None:
        ov = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        ov.fill(C.OVERLAY)
        self.screen.blit(ov, (0, 0))

        t1 = self.font_large.render("🐍 贪吃蛇", True, C.ACCENT)
        r1 = t1.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 40))
        self.screen.blit(t1, r1)

        t2 = self.font_medium.render("按任意键开始", True, C.TEXT)
        r2 = t2.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 + 30))
        self.screen.blit(t2, r2)

    def _draw_overlay_paused(self) -> None:
        ov = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        ov.fill(C.OVERLAY)
        self.screen.blit(ov, (0, 0))

        t1 = self.font_large.render("⏸  已暂停", True, C.TEXT)
        r1 = t1.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 20))
        self.screen.blit(t1, r1)

        t2 = self.font_small.render("按 P 键恢复", True, C.SUBTEXT)
        r2 = t2.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 + 30))
        self.screen.blit(t2, r2)

    def _draw_overlay_gameover(self) -> None:
        ov = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        ov.fill(C.OVERLAY)
        self.screen.blit(ov, (0, 0))

        t1 = self.font_large.render("Game Over !", True, C.FOOD)
        r1 = t1.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 70))
        self.screen.blit(t1, r1)

        stats = (
            f"得分：{self.score}，连击：{self.combo}，用时：{int(self.elapsed)} 秒"
        )
        t2 = self.font_medium.render(stats, True, C.TEXT)
        r2 = t2.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 10))
        self.screen.blit(t2, r2)

        t3 = self.font_small.render("按 R 键重玩", True, C.ACCENT)
        r3 = t3.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 + 40))
        self.screen.blit(t3, r3)


# ============================================================================
# 入口
# ============================================================================

def main():
    Game().run()


if __name__ == "__main__":
    main()
