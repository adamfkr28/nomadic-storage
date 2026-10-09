import os
import time
import math

class Visualizer:
    def __init__(self, nodes, lokasi_shard, node_mati_ids=None):
        self.nodes = nodes
        self.lokasi_shard = lokasi_shard
        self.node_mati_ids = node_mati_ids or []
        self.width = 70
        self.height = 22

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def get_node_positions(self):
        """Atur posisi node dalam formasi lingkaran."""
        positions = {}
        n = len(self.nodes)
        for i, node in enumerate(self.nodes):
            angle = (2 * math.pi * i) / n
            x = int(self.width / 2 + 24 * math.cos(angle))
            y = int(self.height / 2 + 8 * math.sin(angle))
            positions[node.node_id] = (x, y)
        return positions

    def render(self, fase, keterangan=""):
        self.clear()
        positions = self.get_node_positions()

        # Bikin grid kosong
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]

        # Layer 1: Gambar garis antar node yang punya shard sama
        for shard_id, node_ids in self.lokasi_shard.items():
            for i in range(len(node_ids)):
                for j in range(i + 1, len(node_ids)):
                    nid1, nid2 = node_ids[i], node_ids[j]
                    if nid1 in positions and nid2 in positions:
                        x1, y1 = positions[nid1]
                        x2, y2 = positions[nid2]
                        self.draw_line(grid, x1, y1, x2, y2, ".")

        # Layer 2: Gambar node (simbol dulu)
        for node in self.nodes:
            nid = node.node_id
            if nid in positions:
                x, y = positions[nid]
                if nid in self.node_mati_ids:
                    simbol = "X"
                else:
                    simbol = "O"
                if 0 <= x < self.width and 0 <= y < self.height:
                    grid[y][x] = simbol

        # Layer 3: Gambar label (di samping simbol, gak nimpa)
        for node in self.nodes:
            nid = node.node_id
            if nid in positions:
                x, y = positions[nid]
                label = f"[{nid}]"

                # Coba taruh label di kiri simbol
                start_x = x - len(label) - 1
                if start_x < 0:
                    # Kalau gak cukup di kiri, taruh di kanan
                    start_x = x + 2

                for k, ch in enumerate(label):
                    px = start_x + k
                    if 0 <= px < self.width and 0 <= y < self.height:
                        if grid[y][px] == " " or grid[y][px] == ".":
                            grid[y][px] = ch

        # Print header
        print("=" * self.width)
        print(f"  NOMADIC STORAGE - LIVE MAP  |  Fase: {fase}")
        print("=" * self.width)

        # Print grid
        for row in grid:
            print("".join(row))

        # Print footer
        print("=" * self.width)

        # Status
        node_hidup = [n for n in self.nodes if n.node_id not in self.node_mati_ids]
        shard_tersedia = sum(
            1 for nids in self.lokasi_shard.values()
            if any(nid not in self.node_mati_ids for nid in nids)
        )
        print(f"  Node hidup     : {len(node_hidup)}/{len(self.nodes)}")
        print(f"  Shard tersedia : {shard_tersedia}/{len(self.lokasi_shard) if self.lokasi_shard else 0}")
        if keterangan:
            print(f"  Status         : {keterangan}")
        print("=" * self.width)

    def draw_line(self, grid, x1, y1, x2, y2, char="."):
        """Gambar garis lurus antar 2 titik (Bresenham)."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            if 0 <= x1 < self.width and 0 <= y1 < self.height:
                if grid[y1][x1] == " ":
                    grid[y1][x1] = char
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy