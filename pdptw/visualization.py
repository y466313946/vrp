from __future__ import annotations

from pathlib import Path

from pdptw.alns.state import ALNSResult, SolutionState
from pdptw.models import PDPTWInstance


def _draw_solution(
    ax,
    plt,
    instance: PDPTWInstance,
    solution: SolutionState,
    title: str,
    route_color_count: int | None = None,
) -> None:
    """把一个解画到指定坐标轴上。"""

    ax.clear()
    depot = instance.depot
    pickup_nodes = [node for node in instance.nodes if node.is_pickup]
    delivery_nodes = [node for node in instance.nodes if node.is_delivery]
    route_count = route_color_count or max(1, len(solution.routes))
    cmap = plt.get_cmap("tab20", route_count)

    for index, route in enumerate(solution.routes):
        if len(route.node_ids) < 2:
            continue
        color = cmap(index % cmap.N)
        x_coords = [instance.nodes_by_id[node_id].x for node_id in route.node_ids]
        y_coords = [instance.nodes_by_id[node_id].y for node_id in route.node_ids]
        ax.plot(
            x_coords,
            y_coords,
            marker="o",
            linewidth=1.8,
            markersize=4,
            color=color,
            alpha=0.9,
            label=f"Route {index + 1}",
        )

    ax.scatter(
        [node.x for node in pickup_nodes],
        [node.y for node in pickup_nodes],
        c="tab:blue",
        s=32,
        marker="^",
        label="Pickup",
        zorder=3,
    )
    ax.scatter(
        [node.x for node in delivery_nodes],
        [node.y for node in delivery_nodes],
        c="tab:orange",
        s=32,
        marker="s",
        label="Delivery",
        zorder=3,
    )
    ax.scatter([depot.x], [depot.y], c="red", s=120, marker="*", label="Depot", zorder=4)

    # 小规模实例时标注节点编号，避免图面过于拥挤。
    if instance.size <= 100:
        for node in instance.nodes:
            ax.text(node.x + 0.5, node.y + 0.5, str(node.node_id), fontsize=7, alpha=0.75)

    ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)
    ax.legend(loc="best")
    ax.set_aspect("equal", adjustable="box")


def plot_solution(
    instance: PDPTWInstance,
    solution: SolutionState,
    output_path: str | None = None,
    show: bool = True,
    title: str | None = None,
) -> None:
    """可视化给定解的车辆路径。"""

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Visualization requires matplotlib. Please install it with `pip install matplotlib`.") from exc

    fig, ax = plt.subplots(figsize=(10, 8))
    _draw_solution(ax, plt, instance, solution, title or f"ALNS Solution Visualization: {instance.name}")
    fig.tight_layout()

    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=200, bbox_inches="tight")
        print(f"plot_saved: {output}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_alns_result(
    instance: PDPTWInstance,
    result: ALNSResult,
    output_path: str | None = None,
    show: bool = True,
) -> None:
    """可视化 ALNS 求解结果中的最优解。"""

    plot_solution(instance, result.best_solution, output_path=output_path, show=show)


def animate_solution_snapshots(
    instance: PDPTWInstance,
    snapshots: list[SolutionState],
    output_path: str | None = None,
    show: bool = True,
    interval: int = 500,
) -> None:
    """把一组解快照保存或展示为动画。"""

    if not snapshots:
        raise ValueError("Animation requires at least one solution snapshot.")

    if output_path and Path(output_path).suffix.lower() == ".html":
        save_solution_snapshots_html(instance, snapshots, output_path, interval=interval)
        if not show:
            return

    try:
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation, PillowWriter
    except ImportError as exc:
        raise RuntimeError("Animation requires matplotlib. Please install it with `pip install matplotlib`.") from exc

    fig, ax = plt.subplots(figsize=(10, 8))
    route_color_count = max(1, max(len(snapshot.routes) for snapshot in snapshots))
    frame_count = len(snapshots)

    def update(frame_index: int) -> None:
        solution = snapshots[frame_index]
        _draw_solution(
            ax,
            plt,
            instance,
            solution,
            f"Initial Solution Construction: {instance.name} ({frame_index}/{frame_count - 1})",
            route_color_count=route_color_count,
        )
        fig.tight_layout()

    animation = FuncAnimation(fig, update, frames=frame_count, interval=interval, repeat=False)

    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fps = max(1, round(1000 / interval))
        if output.suffix.lower() == ".gif":
            animation.save(output, writer=PillowWriter(fps=fps))
        else:
            animation.save(output, fps=fps)
        print(f"animation_saved: {output}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def save_solution_snapshots_html(
    instance: PDPTWInstance,
    snapshots: list[SolutionState],
    output_path: str,
    interval: int = 500,
) -> None:
    """把解快照保存为可手动切换帧的 HTML。"""

    if not snapshots:
        raise ValueError("HTML playback requires at least one solution snapshot.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_build_snapshot_player_html(_snapshot_player_data(instance, snapshots), interval), encoding="utf-8")
    print(f"html_saved: {output}")


def _snapshot_player_data(instance: PDPTWInstance, snapshots: list[SolutionState]) -> dict[str, object]:
    """把解快照转换成浏览器端 SVG 播放器需要的结构化数据。"""

    colors = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
        "#393b79",
        "#637939",
        "#8c6d31",
        "#843c39",
        "#7b4173",
        "#3182bd",
        "#e6550d",
        "#31a354",
        "#756bb1",
        "#636363",
    ]

    nodes = []
    for node in instance.nodes:
        if node.is_depot:
            node_type = "depot"
        elif node.is_pickup:
            node_type = "pickup"
        else:
            node_type = "delivery"
        nodes.append(
            {
                "id": node.node_id,
                "x": node.x,
                "y": node.y,
                "type": node_type,
                "demand": node.demand,
                "readyTime": node.ready_time,
                "dueTime": node.due_time,
                "serviceTime": node.service_time,
                "pickupId": node.pickup_id,
                "deliveryId": node.delivery_id,
                "pairId": node.pair_id,
            }
        )

    frames = []
    for solution in snapshots:
        routes = []
        for route_index, route in enumerate(solution.routes):
            points = []
            for position, node_id in enumerate(route.node_ids):
                node = instance.nodes_by_id[node_id]
                arrival_time = route.arrival_times[position] if position < len(route.arrival_times) else None
                start_time = route.start_times[position] if position < len(route.start_times) else None
                load = route.loads[position] if position < len(route.loads) else None
                departure_time = None if start_time is None else start_time + node.service_time
                points.append(
                    {
                        "nodeId": node_id,
                        "x": node.x,
                        "y": node.y,
                        "routeIndex": route_index,
                        "position": position,
                        "arrivalTime": arrival_time,
                        "startTime": start_time,
                        "departureTime": departure_time,
                        "load": load,
                    }
                )
            routes.append(
                {
                    "index": route_index,
                    "color": colors[route_index % len(colors)],
                    "distance": route.distance,
                    "points": points,
                }
            )

        frames.append(
            {
                "routes": routes,
                "vehicleCount": solution.vehicle_count,
                "totalDistance": solution.total_distance,
                "unservedCount": len(solution.unserved_requests),
            }
        )

    return {
        "instanceName": instance.name,
        "nodes": nodes,
        "frames": frames,
    }


def _build_snapshot_player_html(player_data: dict[str, object], interval: int) -> str:
    """生成一个离线可打开的逐帧播放器页面。"""

    import json

    data_json = json.dumps(player_data)
    interval_json = json.dumps(interval)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Initial Solution Playback</title>
  <style>
    body {{
      margin: 0;
      padding: 24px;
      font-family: Arial, "Microsoft YaHei", sans-serif;
      background: #f6f7f9;
      color: #1f2328;
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 20px;
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
    }}
    h1 {{
      margin: 0 0 16px;
      font-size: 22px;
    }}
    .plot {{
      position: relative;
      width: 100%;
      max-height: 75vh;
      border: 1px solid #d0d7de;
      border-radius: 8px;
      background: #ffffff;
      overflow: hidden;
    }}
    svg {{
      display: block;
      width: 100%;
      height: 75vh;
      min-height: 560px;
    }}
    .axis-label {{
      fill: #57606a;
      font-size: 12px;
    }}
    .route-line {{
      fill: none;
      stroke-width: 2.4;
      stroke-linejoin: round;
      stroke-linecap: round;
      opacity: 0.9;
    }}
    .base-node {{
      stroke: #ffffff;
      stroke-width: 1.2;
      opacity: 0.55;
    }}
    .visit-node {{
      cursor: pointer;
      stroke: #1f2328;
      stroke-width: 1.5;
    }}
    .visit-node:hover {{
      stroke-width: 3;
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-top: 16px;
    }}
    button {{
      padding: 8px 14px;
      border: 1px solid #8c959f;
      border-radius: 6px;
      background: #ffffff;
      cursor: pointer;
    }}
    button:hover {{
      background: #f3f4f6;
    }}
    input[type="range"] {{
      flex: 1;
      min-width: 260px;
    }}
    .frame-label {{
      min-width: 120px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .summary {{
      margin-top: 10px;
      color: #57606a;
      font-size: 14px;
    }}
    .tooltip {{
      position: absolute;
      display: none;
      max-width: 280px;
      padding: 10px 12px;
      border: 1px solid #d0d7de;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.96);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
      font-size: 13px;
      line-height: 1.45;
      pointer-events: none;
      z-index: 10;
    }}
    .tooltip strong {{
      display: block;
      margin-bottom: 4px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Initial Solution Construction: <span id="instance"></span></h1>
    <div id="plot" class="plot">
      <svg id="svg" role="img" aria-label="solution frame"></svg>
      <div id="tooltip" class="tooltip"></div>
    </div>
    <div id="summary" class="summary"></div>
    <div class="controls">
      <button id="first">第一帧</button>
      <button id="prev">上一帧</button>
      <button id="play">播放</button>
      <button id="next">下一帧</button>
      <button id="last">最后一帧</button>
      <input id="slider" type="range" min="0" max="0" value="0">
      <span id="frameLabel" class="frame-label"></span>
    </div>
  </main>

  <script>
    const data = {data_json};
    const interval = {interval_json};
    const frames = data.frames;
    let index = 0;
    let timer = null;
    let pinnedTooltip = false;

    const plot = document.getElementById("plot");
    const svg = document.getElementById("svg");
    const tooltip = document.getElementById("tooltip");
    const summary = document.getElementById("summary");
    const slider = document.getElementById("slider");
    const frameLabel = document.getElementById("frameLabel");
    const playButton = document.getElementById("play");
    document.getElementById("instance").textContent = data.instanceName;
    slider.max = String(frames.length - 1);

    const width = 1000;
    const height = 760;
    const padding = 56;
    const xValues = data.nodes.map((node) => node.x);
    const yValues = data.nodes.map((node) => node.y);
    const minX = Math.min(...xValues);
    const maxX = Math.max(...xValues);
    const minY = Math.min(...yValues);
    const maxY = Math.max(...yValues);
    const xSpan = Math.max(1, maxX - minX);
    const ySpan = Math.max(1, maxY - minY);
    const nodeById = new Map(data.nodes.map((node) => [node.id, node]));

    svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);

    function sx(x) {{
      return padding + ((x - minX) / xSpan) * (width - padding * 2);
    }}

    function sy(y) {{
      return height - padding - ((y - minY) / ySpan) * (height - padding * 2);
    }}

    function round(value) {{
      return value === null || value === undefined ? "-" : Number(value).toFixed(2);
    }}

    function nodeTypeLabel(type) {{
      if (type === "depot") return "Depot";
      if (type === "pickup") return "Pickup";
      return "Delivery";
    }}

    function staticInfo(node) {{
      return [
        `<strong>节点 ${{node.id}} · ${{nodeTypeLabel(node.type)}}</strong>`,
        `坐标: (${{node.x}}, ${{node.y}})`,
        `需求量: ${{node.demand}}`,
        `时间窗: [${{node.readyTime}}, ${{node.dueTime}}]`,
        `服务时间: ${{node.serviceTime}}`,
        node.type === "pickup" ? `对应 delivery: ${{node.deliveryId}}` : "",
        node.type === "delivery" ? `对应 pickup: ${{node.pickupId}}` : "",
      ].filter(Boolean).join("<br>");
    }}

    function visitInfo(node, point, route) {{
      return [
        `<strong>节点 ${{node.id}} · ${{nodeTypeLabel(node.type)}}</strong>`,
        `车辆路径: Route ${{point.routeIndex + 1}}`,
        `路径位置: ${{point.position}}`,
        `坐标: (${{node.x}}, ${{node.y}})`,
        `需求量: ${{node.demand}}`,
        `载重: ${{point.load ?? "-"}}`,
        `时间窗: [${{node.readyTime}}, ${{node.dueTime}}]`,
        `到达时间: ${{round(point.arrivalTime)}}`,
        `开始服务: ${{round(point.startTime)}}`,
        `服务时间: ${{node.serviceTime}}`,
        `离开时间: ${{round(point.departureTime)}}`,
        `路径距离: ${{round(route.distance)}}`,
      ].join("<br>");
    }}

    function showTooltip(html, event) {{
      tooltip.innerHTML = html;
      tooltip.style.display = "block";
      moveTooltip(event);
    }}

    function moveTooltip(event) {{
      const rect = plot.getBoundingClientRect();
      const left = Math.min(event.clientX - rect.left + 14, rect.width - tooltip.offsetWidth - 8);
      const top = Math.min(event.clientY - rect.top + 14, rect.height - tooltip.offsetHeight - 8);
      tooltip.style.left = `${{Math.max(8, left)}}px`;
      tooltip.style.top = `${{Math.max(8, top)}}px`;
    }}

    function hideTooltip() {{
      if (!pinnedTooltip) {{
        tooltip.style.display = "none";
      }}
    }}

    function makeSvgElement(name, attributes) {{
      const element = document.createElementNS("http://www.w3.org/2000/svg", name);
      for (const [key, value] of Object.entries(attributes)) {{
        element.setAttribute(key, String(value));
      }}
      return element;
    }}

    function addTooltipEvents(element, html) {{
      element.addEventListener("mouseenter", (event) => {{
        pinnedTooltip = false;
        showTooltip(html, event);
      }});
      element.addEventListener("mousemove", moveTooltip);
      element.addEventListener("mouseleave", hideTooltip);
      element.addEventListener("click", (event) => {{
        pinnedTooltip = !pinnedTooltip;
        showTooltip(html, event);
      }});
    }}

    function addPoint(parent, node, cx, cy, fill, className, radius = 7) {{
      let element;
      if (node.type === "pickup") {{
        const points = `${{cx}},${{cy - radius}} ${{cx - radius}},${{cy + radius}} ${{cx + radius}},${{cy + radius}}`;
        element = makeSvgElement("polygon", {{ points, fill, class: className }});
      }} else if (node.type === "delivery") {{
        element = makeSvgElement("rect", {{
          x: cx - radius,
          y: cy - radius,
          width: radius * 2,
          height: radius * 2,
          fill,
          class: className,
        }});
      }} else {{
        element = makeSvgElement("circle", {{ cx, cy, r: radius + 3, fill, class: className }});
      }}
      parent.appendChild(element);
      return element;
    }}

    function render(nextIndex) {{
      index = Math.max(0, Math.min(frames.length - 1, nextIndex));
      const frame = frames[index];
      svg.replaceChildren();

      svg.appendChild(makeSvgElement("rect", {{ x: 0, y: 0, width, height, fill: "#ffffff" }}));
      svg.appendChild(makeSvgElement("line", {{
        x1: padding,
        y1: height - padding,
        x2: width - padding,
        y2: height - padding,
        stroke: "#d0d7de",
      }}));
      svg.appendChild(makeSvgElement("line", {{
        x1: padding,
        y1: padding,
        x2: padding,
        y2: height - padding,
        stroke: "#d0d7de",
      }}));

      for (const node of data.nodes) {{
        const fill = node.type === "depot" ? "#d62728" : node.type === "pickup" ? "#1f77b4" : "#ff7f0e";
        const element = addPoint(svg, node, sx(node.x), sy(node.y), fill, "base-node", 5);
        addTooltipEvents(element, staticInfo(node));
      }}

      for (const route of frame.routes) {{
        const pathPoints = route.points.map((point) => `${{sx(point.x)}},${{sy(point.y)}}`).join(" ");
        svg.appendChild(makeSvgElement("polyline", {{
          points: pathPoints,
          stroke: route.color,
          class: "route-line",
        }}));

        for (const point of route.points) {{
          const node = nodeById.get(point.nodeId);
          const element = addPoint(svg, node, sx(point.x), sy(point.y), route.color, "visit-node", 8);
          addTooltipEvents(element, visitInfo(node, point, route));
        }}
      }}

      slider.value = String(index);
      frameLabel.textContent = `${{index}} / ${{frames.length - 1}}`;
      summary.textContent = `车辆数: ${{frame.vehicleCount}} | 总距离: ${{round(frame.totalDistance)}} | 未服务请求: ${{frame.unservedCount}}`;
    }}

    function stop() {{
      if (timer !== null) {{
        clearInterval(timer);
        timer = null;
      }}
      playButton.textContent = "播放";
    }}

    function togglePlay() {{
      if (timer !== null) {{
        stop();
        return;
      }}
      playButton.textContent = "暂停";
      timer = setInterval(() => {{
        if (index >= frames.length - 1) {{
          stop();
          return;
        }}
        render(index + 1);
      }}, interval);
    }}

    document.getElementById("first").addEventListener("click", () => {{ stop(); render(0); }});
    document.getElementById("prev").addEventListener("click", () => {{ stop(); render(index - 1); }});
    document.getElementById("play").addEventListener("click", togglePlay);
    document.getElementById("next").addEventListener("click", () => {{ stop(); render(index + 1); }});
    document.getElementById("last").addEventListener("click", () => {{ stop(); render(frames.length - 1); }});
    slider.addEventListener("input", () => {{ stop(); render(Number(slider.value)); }});
    document.addEventListener("keydown", (event) => {{
      if (event.key === "ArrowLeft") {{ stop(); render(index - 1); }}
      if (event.key === "ArrowRight") {{ stop(); render(index + 1); }}
      if (event.key === "Escape") {{
        pinnedTooltip = false;
        tooltip.style.display = "none";
      }}
    }});

    render(0);
  </script>
</body>
</html>
"""
