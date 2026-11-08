from io import BytesIO
from threading import Lock

import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from database.models import WeightEntry


_chart_lock = Lock()


def build_weight_chart(
    entries: list[WeightEntry],
    period_label: str,
) -> bytes:
    if not entries:
        raise ValueError("Нет измерений для графика.")

    # Matplotlib не должен строить несколько графиков одновременно.
    with _chart_lock:
        figure = Figure(figsize=(9, 5), layout="constrained")
        FigureCanvasAgg(figure)
        axes = figure.subplots()

        dates = [entry.recorded_at for entry in entries]
        weights = [entry.weight for entry in entries]

        axes.plot(
            dates,
            weights,
            marker="o",
            color="#2878B5",
            linewidth=2,
        )

        axes.set_title(f"Изменение веса — {period_label}")
        axes.set_xlabel("Дата и время (UTC)")
        axes.set_ylabel("Вес, кг")
        axes.grid(alpha=0.3)

        locator = mdates.AutoDateLocator()
        axes.xaxis.set_major_locator(locator)
        axes.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(locator)
        )

        if len(entries) == 1:
            axes.annotate(
                f"{weights[0]:g} кг",
                (dates[0], weights[0]),
                xytext=(10, 10),
                textcoords="offset points",
            )

        with BytesIO() as buffer:
            figure.savefig(buffer, format="png", dpi=140)
            return buffer.getvalue()