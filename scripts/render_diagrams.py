from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "diagrams" / "exports"
FONT_REGULAR = Path("C:/Windows/Fonts/arial.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")

NAVY = "#174A72"
BLUE = "#2D6A96"
PALE = "#EAF2F8"
PALE_GREEN = "#E8F5EE"
PALE_ORANGE = "#FFF2DE"
PALE_PURPLE = "#F0EAF8"
PANEL = "#F7FAFC"
TEXT = "#17212B"
MUTED = "#566573"
BORDER = "#9AAEBF"
WHITE = "#FFFFFF"
RED = "#A33A3A"
LIGHT_LINE = "#D8E1E8"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int
    title: str
    lines: tuple[str, ...] = ()
    fill: str = WHITE

    @property
    def left(self) -> tuple[int, int]:
        return self.x, self.y + self.h // 2

    @property
    def right(self) -> tuple[int, int]:
        return self.x + self.w, self.y + self.h // 2

    @property
    def top(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y

    @property
    def bottom(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h


def canvas(width: int, height: int, title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)
    draw.text((70, 38), title, fill=NAVY, font=font(52, True))
    draw.text((72, 105), subtitle, fill=MUTED, font=font(25))
    draw.line((70, 148, width - 70, 148), fill=LIGHT_LINE, width=3)
    return image, draw


def draw_panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, fill: str = PANEL) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=24, fill=fill, outline=LIGHT_LINE, width=3)
    draw.text((x + 24, y + 16), title, fill=NAVY, font=font(27, True))


def draw_box(draw: ImageDraw.ImageDraw, box: Box, title_size: int = 25, body_size: int = 19) -> None:
    draw.rounded_rectangle(
        (box.x, box.y, box.x + box.w, box.y + box.h),
        radius=16,
        fill=box.fill,
        outline=BORDER,
        width=3,
    )
    draw.rounded_rectangle((box.x, box.y, box.x + box.w, box.y + 52), radius=16, fill=NAVY)
    draw.rectangle((box.x, box.y + 34, box.x + box.w, box.y + 52), fill=NAVY)
    draw.text((box.x + 16, box.y + 11), box.title, fill=WHITE, font=font(title_size, True))
    y = box.y + 67
    for line in box.lines:
        draw.text((box.x + 16, y), line, fill=TEXT, font=font(body_size))
        y += body_size + 9


def dashed_segment(draw: ImageDraw.ImageDraw, a: tuple[int, int], b: tuple[int, int], color: str, width: int) -> None:
    length = math.dist(a, b)
    if length == 0:
        return
    dash, gap = 18, 12
    dx, dy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    cursor = 0.0
    while cursor < length:
        end = min(cursor + dash, length)
        p1 = (round(a[0] + dx * cursor), round(a[1] + dy * cursor))
        p2 = (round(a[0] + dx * end), round(a[1] + dy * end))
        draw.line((*p1, *p2), fill=color, width=width)
        cursor += dash + gap


def orthogonal_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    label: str = "",
    label_pos: tuple[int, int] | None = None,
    dashed: bool = False,
    color: str = BLUE,
    width: int = 4,
) -> None:
    for a, b in zip(points, points[1:]):
        if dashed:
            dashed_segment(draw, a, b, color, width)
        else:
            draw.line((*a, *b), fill=color, width=width)
    a, b = points[-2], points[-1]
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    for offset in (2.55, -2.55):
        p = (b[0] + int(18 * math.cos(angle + offset)), b[1] + int(18 * math.sin(angle + offset)))
        draw.line((*b, *p), fill=color, width=width)
    if label:
        lx, ly = label_pos or points[len(points) // 2]
        bbox = draw.textbbox((0, 0), label, font=font(18, True))
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rounded_rectangle((lx - 8, ly - 5, lx + tw + 8, ly + th + 5), radius=7, fill=WHITE, outline=LIGHT_LINE)
        draw.text((lx, ly), label, fill=MUTED, font=font(18, True))


def draw_legend(draw: ImageDraw.ImageDraw, items: list[tuple[str, str]], x: int, y: int) -> None:
    cursor = x
    for color, label in items:
        draw.rounded_rectangle((cursor, y, cursor + 34, y + 24), radius=6, fill=color, outline=BORDER, width=2)
        draw.text((cursor + 45, y - 1), label, fill=MUTED, font=font(20, True))
        cursor += 45 + draw.textlength(label, font=font(20, True)) + 55


def save(image: Image.Image, name: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT / name, format="PNG", optimize=True)


def render_architecture() -> None:
    image, draw = canvas(3000, 1850, "Arquitetura do LoadForge", "Leitura em três faixas: acesso, ciclo adaptativo e persistência")
    draw_panel(draw, 790, 205, 1530, 1270, "Monólito modular FastAPI")
    draw_panel(draw, 2380, 380, 540, 470, "Ambiente autorizado", PALE_GREEN)
    boxes = {
        "user": Box(70, 505, 300, 185, "Usuário", ("QA", "Visualizador"), PALE),
        "ui": Box(430, 505, 330, 185, "Frontend", ("React planejado", "Protótipo Figma"), PALE),
        "api": Box(865, 505, 350, 220, "API REST", ("FastAPI", "validação", "autorização"), PALE_GREEN),
        "executor": Box(1450, 505, 390, 220, "Orquestrador", ("cenário", "motor assíncrono", "parada segura"), PALE),
        "target": Box(2460, 505, 390, 220, "Alvo autorizado", ("aplicação própria", "limites registrados", "HTTP controlado"), PALE_GREEN),
        "control": Box(900, 885, 390, 220, "Controle híbrido", ("fixo", "fallback por regras", "IA + regras"), PALE_ORANGE),
        "ai": Box(1390, 885, 390, 220, "IA local", ("FeatureBuilder", "RiskPredictor", "risco em 10 s"), PALE_PURPLE),
        "metrics": Box(1880, 885, 390, 220, "Métricas", ("janelas de 2 s", "throughput e p95", "erros CPU memória"), PALE),
        "registry": Box(865, 1190, 350, 190, "Cadastros", ("projetos", "endpoints", "autorizações"), PALE),
        "artifact": Box(1390, 1190, 390, 190, "Artefato do modelo", ("joblib versionado", "métricas de validação"), PALE_PURPLE),
        "reports": Box(1880, 1190, 390, 190, "Relatórios", ("histórico", "comparação", "explicabilidade"), PALE),
        "db": Box(1110, 1530, 870, 190, "Persistência PostgreSQL 16", ("repositórios SQLAlchemy • migrations Alembic • histórico reproduzível",), PALE_GREEN),
    }
    orthogonal_arrow(draw, [boxes["user"].right, boxes["ui"].left], "HTTPS", (375, 555))
    orthogonal_arrow(draw, [boxes["ui"].right, (810, 597), (810, 615), boxes["api"].left], "REST JSON", (770, 555))
    orthogonal_arrow(draw, [boxes["api"].right, boxes["executor"].left], "comando validado", (1230, 555))
    orthogonal_arrow(draw, [boxes["executor"].right, boxes["target"].left], "requisições", (2050, 555))
    orthogonal_arrow(draw, [boxes["target"].bottom, (2655, 995), boxes["metrics"].right], "respostas", (2400, 905))
    orthogonal_arrow(draw, [boxes["metrics"].left, boxes["ai"].right], "características", (1790, 935))
    orthogonal_arrow(draw, [boxes["ai"].left, boxes["control"].right], "risco", (1310, 935))
    orthogonal_arrow(draw, [boxes["control"].top, (1095, 805), (1645, 805), boxes["executor"].bottom], "nova concorrência", (1270, 770))
    orthogonal_arrow(draw, [boxes["api"].bottom, (830, 725), (830, 1285), boxes["registry"].left], "mantém", (785, 1030))
    orthogonal_arrow(draw, [boxes["ai"].bottom, boxes["artifact"].top], "carrega", (1600, 1128))
    orthogonal_arrow(draw, [boxes["metrics"].bottom, boxes["reports"].top], "consolida", (2075, 1128))
    orthogonal_arrow(draw, [boxes["registry"].bottom, (1040, 1450), (1320, 1450), (1320, 1530)], "persiste", (1080, 1415))
    orthogonal_arrow(draw, [boxes["reports"].bottom, (2075, 1450), (1760, 1450), (1760, 1530)], "consulta", (1830, 1415))
    for box in boxes.values():
        draw_box(draw, box, 24, 19)
    draw_legend(draw, [(PALE, "aplicação"), (PALE_ORANGE, "otimização"), (PALE_PURPLE, "IA local"), (PALE_GREEN, "segurança e dados")], 80, 1770)
    draw.text((2030, 1770), "MVP sem API externa de IA, GPU, Redis, Celery ou microserviços.", fill=RED, font=font(22, True))
    save(image, "architecture.png")


def render_classes() -> None:
    image, draw = canvas(3200, 2350, "Diagrama de Classes", "Domínio persistido acima; serviços, IA e controle abaixo")
    draw_panel(draw, 50, 190, 3100, 920, "1. Entidades do domínio")
    draw_panel(draw, 50, 1160, 3100, 1050, "2. Serviços e contratos")
    boxes = {
        "user": Box(80, 300, 500, 230, "User", ("id: UUID", "email: string", "role: UserRole"), PALE),
        "project": Box(690, 300, 500, 230, "Project", ("id: UUID", "owner_id: UUID", "name: string"), PALE),
        "endpoint": Box(1300, 300, 500, 230, "Endpoint", ("id: UUID", "base_url: string", "authorization_confirmed: bool"), PALE),
        "scenario": Box(1910, 300, 500, 230, "TestScenario", ("duration_seconds: int", "max_concurrency: int", "strategy: ControlStrategy"), PALE),
        "execution": Box(2520, 300, 500, 230, "TestExecution", ("status: ExecutionStatus", "+start()", "+cancel(reason)"), PALE),
        "model": Box(80, 720, 500, 230, "ModelVersion", ("version: string", "algorithm: string", "status: ModelStatus"), PALE_PURPLE),
        "decision": Box(690, 720, 500, 230, "ControlDecision", ("metric_window_id: UUID", "action: ControlAction", "next_concurrency: int"), PALE_ORANGE),
        "prediction": Box(1300, 720, 500, 230, "RiskPrediction", ("model_version_id: UUID", "risk_probability: float", "inference_latency_ms: int"), PALE_PURPLE),
        "metric": Box(1910, 720, 500, 230, "MetricWindow", ("throughput_rps: float", "latency_p95_ms: float", "error_rate: float"), PALE),
        "report": Box(2520, 720, 500, 230, "ExecutionReport", ("total_requests: int", "average_throughput_rps: float", "final_error_rate: float"), PALE),
        "coordinator": Box(1340, 1270, 520, 220, "ExecutionCoordinator", ("+run(execution)", "+apply(decision)"), PALE_GREEN),
        "aggregator": Box(300, 1610, 500, 220, "MetricsAggregator", ("+aggregate(observations)", "-> MetricWindow"), PALE_GREEN),
        "risk_iface": Box(1050, 1610, 500, 220, "RiskPredictor interface", ("+predict_risk(features)", "-> RiskPredictionResult"), PALE_GREEN),
        "control_iface": Box(1800, 1610, 500, 220, "ConcurrencyController interface", ("+decide(input)", "-> ControlDecisionResult"), PALE_GREEN),
        "sklearn": Box(1050, 1940, 500, 210, "SklearnRiskPredictor", ("modelo local", "+predict_risk(features)"), PALE_PURPLE),
        "rules": Box(1800, 1940, 500, 210, "RulesController", ("fallback determinístico", "+decide(input)"), PALE_ORANGE),
        "adaptive": Box(2480, 1940, 500, 210, "AdaptiveLoadController", ("combina risco e métricas", "+decide(input)"), PALE_ORANGE),
    }
    for a, b, label, pos in (
        ("user", "project", "1 possui N", (590, 370)),
        ("project", "endpoint", "1 contém N", (1200, 370)),
        ("endpoint", "scenario", "1 configura N", (1810, 370)),
        ("scenario", "execution", "1 origina N", (2420, 370)),
    ):
        orthogonal_arrow(draw, [boxes[a].right, boxes[b].left], label, pos)
    orthogonal_arrow(draw, [boxes["execution"].bottom, (2770, 630), (2160, 630), boxes["metric"].top], "1 registra N", (2230, 595))
    orthogonal_arrow(draw, [boxes["execution"].bottom, boxes["report"].top], "0..1 relatório", (2800, 600))
    orthogonal_arrow(draw, [boxes["metric"].left, boxes["prediction"].right], "0..1 previsão", (1810, 785))
    orthogonal_arrow(draw, [boxes["prediction"].left, boxes["decision"].right], "subsidia", (1200, 785))
    orthogonal_arrow(draw, [boxes["model"].bottom, (330, 1035), (1550, 1035), boxes["prediction"].bottom], "gera", (910, 1000))
    orthogonal_arrow(draw, [boxes["coordinator"].bottom, (1600, 1540), (550, 1540), boxes["aggregator"].top], "usa", (800, 1505))
    orthogonal_arrow(draw, [boxes["coordinator"].bottom, (1600, 1540), (1300, 1540), boxes["risk_iface"].top], "usa", (1420, 1505))
    orthogonal_arrow(draw, [boxes["coordinator"].bottom, (1600, 1540), (2050, 1540), boxes["control_iface"].top], "usa", (1880, 1505))
    orthogonal_arrow(draw, [boxes["sklearn"].top, boxes["risk_iface"].bottom], "implementa", (1570, 1860), dashed=True)
    orthogonal_arrow(draw, [boxes["rules"].top, boxes["control_iface"].bottom], "implementa", (2320, 1860), dashed=True)
    orthogonal_arrow(draw, [boxes["adaptive"].top, (2730, 1880), (2050, 1880), boxes["control_iface"].bottom], "implementa", (2490, 1845), dashed=True)
    for box in boxes.values():
        draw_box(draw, box, 23, 18)
    draw.text((80, 2260), "Leitura: relações principais são desenhadas; referências secundárias aparecem como atributos UUID para evitar cruzamentos.", fill=MUTED, font=font(22, True))
    save(image, "classes.png")


def entity_box(title: str, lines: tuple[str, ...], fill: str, x: int, y: int, h: int = 300) -> Box:
    return Box(x, y, 420, h, title, lines, fill)


def render_entity_diagram(relational: bool) -> None:
    filename = "relational-model.png" if relational else "mer.png"
    title = "Modelo Relacional" if relational else "Modelo Entidade-Relacionamento"
    subtitle = "Chaves e referências explícitas; somente o caminho principal recebe linhas" if relational else "Cadeia principal da esquerda para a direita; extensões abaixo da entidade de origem"
    image, draw = canvas(3400, 1720, title, subtitle)
    if relational:
        specs = {
            "users": ("users", ("PK id", "UK email", "role", "created_at"), PALE),
            "projects": ("projects", ("PK id", "FK owner_id -> users.id", "name", "description"), PALE),
            "endpoints": ("endpoints", ("PK id", "FK project_id -> projects.id", "base_url", "authorization_confirmed"), PALE),
            "scenario": ("test_scenarios", ("PK id", "FK project_id -> projects.id", "FK endpoint_id -> endpoints.id", "FK created_by -> users.id", "strategy e limites"), PALE),
            "execution": ("test_executions", ("PK id", "FK scenario_id -> test_scenarios.id", "FK initiated_by -> users.id", "FK model_version_id -> model_versions.id", "status e strategy"), PALE),
            "metric": ("metric_windows", ("PK id", "FK execution_id -> test_executions.id", "UK execution_id + sequence", "throughput p95 error CPU"), PALE),
            "report": ("execution_reports", ("PK id", "FK UK execution_id -> test_executions.id", "totals e throughput", "p95 error summary"), PALE),
            "decision": ("control_decisions", ("PK id", "FK UK metric_window_id -> metric_windows.id", "FK UK risk_prediction_id -> risk_predictions.id", "action concurrency reason"), PALE_ORANGE),
            "model": ("model_versions", ("PK id", "UK version", "algorithm e status", "precision recall F1"), PALE_PURPLE),
            "prediction": ("risk_predictions", ("PK id", "FK UK metric_window_id -> metric_windows.id", "FK model_version_id -> model_versions.id", "probability e latency"), PALE_PURPLE),
        }
    else:
        specs = {
            "users": ("USER", ("id", "email único", "papel"), PALE),
            "projects": ("PROJECT", ("id", "owner", "nome"), PALE),
            "endpoints": ("ENDPOINT", ("id", "projeto", "alvo autorizado"), PALE),
            "scenario": ("TEST SCENARIO", ("id", "projeto e endpoint", "estratégia e limites"), PALE),
            "execution": ("TEST EXECUTION", ("id", "cenário e iniciador", "modelo opcional", "status"), PALE),
            "metric": ("METRIC WINDOW", ("id", "execução e sequência", "throughput p95 erro CPU"), PALE),
            "report": ("EXECUTION REPORT", ("id", "uma execução", "resumo consolidado"), PALE),
            "decision": ("CONTROL DECISION", ("id", "uma janela", "previsão opcional", "ação e concorrência"), PALE_ORANGE),
            "model": ("MODEL VERSION", ("id", "versão única", "algoritmo e métricas"), PALE_PURPLE),
            "prediction": ("RISK PREDICTION", ("id", "uma janela", "uma versão do modelo", "probabilidade"), PALE_PURPLE),
        }
    x_positions = [50, 520, 990, 1460, 1930, 2400]
    boxes = {
        "users": entity_box(*specs["users"], x_positions[0], 350),
        "projects": entity_box(*specs["projects"], x_positions[1], 350),
        "endpoints": entity_box(*specs["endpoints"], x_positions[2], 350),
        "scenario": entity_box(*specs["scenario"], x_positions[3], 350, h=330),
        "execution": entity_box(*specs["execution"], x_positions[4], 350, h=330),
        "metric": entity_box(*specs["metric"], x_positions[5], 350, h=330),
        "report": entity_box(*specs["report"], x_positions[4], 970),
        "decision": entity_box(*specs["decision"], x_positions[5], 970, h=330),
        "model": entity_box(*specs["model"], 2870, 970),
        "prediction": entity_box(*specs["prediction"], 2870, 350, h=330),
    }
    draw.rounded_rectangle((45, 205, 1860, 280), radius=14, fill=PALE, outline=BORDER, width=2)
    draw.text((75, 223), "CADASTRO E AUTORIZAÇÃO", fill=NAVY, font=font(25, True))
    draw.rounded_rectangle((1925, 205, 2815, 280), radius=14, fill=PALE_GREEN, outline=BORDER, width=2)
    draw.text((1955, 223), "EXECUÇÃO E MÉTRICAS", fill=NAVY, font=font(25, True))
    draw.rounded_rectangle((2865, 205, 3335, 280), radius=14, fill=PALE_PURPLE, outline=BORDER, width=2)
    draw.text((2895, 223), "IA E CONTROLE", fill=NAVY, font=font(25, True))
    labels = ["0..N", "0..N", "0..N", "0..N", "0..N", "0..1"]
    chain = ["users", "projects", "endpoints", "scenario", "execution", "metric", "prediction"]
    for idx, (a, b) in enumerate(zip(chain, chain[1:])):
        orthogonal_arrow(draw, [boxes[a].right, boxes[b].left], labels[idx], (boxes[a].x + boxes[a].w + 10, 430))
    orthogonal_arrow(draw, [boxes["execution"].bottom, boxes["report"].top], "0..1", (2170, 820))
    orthogonal_arrow(draw, [boxes["metric"].bottom, boxes["decision"].top], "0..1", (2630, 820))
    orthogonal_arrow(draw, [boxes["model"].top, boxes["prediction"].bottom], "0..N", (3120, 820))
    orthogonal_arrow(draw, [boxes["prediction"].bottom, (3080, 850), (2760, 850), boxes["decision"].top], "0..1", (2830, 810), dashed=True)
    for box in boxes.values():
        draw_box(draw, box, 22, 17 if relational else 19)
    draw.text((70, 1510), "Rótulo: quantidade possível no destino para cada registro de origem. Linha tracejada: vínculo opcional.", fill=MUTED, font=font(21, True))
    if relational:
        draw.text((70, 1560), "As demais relações são mostradas dentro das tabelas como FK -> tabela.id; isso mantém o diagrama completo sem linhas sobrepostas.", fill=TEXT, font=font(21))
        draw.text((70, 1605), "Fonte executável: migration Alembic. Representação SQL equivalente: database/schema.sql.", fill=TEXT, font=font(21))
    else:
        draw.text((70, 1560), "Relações secundárias de autoria, projeto e versão do modelo permanecem descritas nos atributos das entidades.", fill=TEXT, font=font(21))
    save(image, filename)


def main() -> None:
    render_architecture()
    render_classes()
    render_entity_diagram(relational=False)
    render_entity_diagram(relational=True)


if __name__ == "__main__":
    main()
