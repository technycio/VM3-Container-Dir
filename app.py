"""Terminal application that shows New Haven weather."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from typing import Optional

from rich.align import Align  # type: ignore[import-not-found]
from rich.panel import Panel  # type: ignore[import-not-found]
from rich.table import Table  # type: ignore[import-not-found]

from textual.app import App, ComposeResult  # type: ignore[import-not-found]
from textual.containers import Container, Horizontal  # type: ignore[import-not-found]
from textual.reactive import reactive  # type: ignore[import-not-found]
from textual.widgets import Footer, Header, Static  # type: ignore[import-not-found]

from weather_client import WeatherClient, WeatherReport


class StatusBar(Static):
    """Simple status widget."""

    DEFAULT_CSS = """
    StatusBar {
        background: $surface-darken-2;
        color: $text-muted;
        padding: 0 1;
        height: 3;
    }
    """


class CurrentWeatherPanel(Static):
    """Displays the current conditions."""

    def update_report(self, report: Optional[WeatherReport]) -> None:
        if not report:
            self.update("Waiting for weather data…")
            return

        content = Table.grid(padding=(0, 1))
        content.add_column(justify="left")
        content.add_column(justify="right")

        content.add_row("Temperature", f"{report.temperature_c:.1f}°C ({_c_to_f(report.temperature_c):.1f}°F)")
        content.add_row("Feels like", f"{report.feels_like_c:.1f}°C")
        content.add_row("Humidity", f"{report.humidity}%")
        content.add_row("Wind", f"{report.wind_speed_kph:.1f} km/h {_wind_direction_to_text(report.wind_direction_deg)}")

        body = Panel(
            Align.center(content, vertical="middle"),
            title=f"{report.location} — {report.summary}",
            border_style="bright_cyan",
        )
        self.update(body)


class HourlyForecastPanel(Static):
    """Displays the next few hours."""

    def update_report(self, report: Optional[WeatherReport]) -> None:
        if not report or not report.hourly:
            self.update("No forecast data available.")
            return

        table = Table(title="Next Hours", box=None, show_header=True, header_style="bold magenta")
        table.add_column("Time")
        table.add_column("Temp")
        table.add_column("Humidity")
        table.add_column("Conditions", justify="left")

        for hour in report.hourly:
            table.add_row(
                hour.time.strftime("%I:%M %p").lstrip("0"),
                f"{hour.temperature_c:.0f}°C / {_c_to_f(hour.temperature_c):.0f}°F",
                f"{hour.humidity}%",
                hour.summary,
            )

        self.update(Panel(table, border_style="bright_magenta"))


class WeatherApp(App[None]):
    """Main Textual application."""

    TITLE = "New Haven Weather"
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 4;
        background: linear-gradient(120deg, #001f3f, #003a70 40%, #0f4c81 100%);
        color: #e3f2fd;
    }

    Header {
        dock: top;
        background: transparent;
        color: #e3f2fd;
    }

    .body {
        padding: 2;
    }

    CurrentWeatherPanel, HourlyForecastPanel {
        width: 1fr;
        min-height: 12;
    }

    Footer {
        dock: bottom;
        background: transparent;
        color: $text-muted;
    }

    StatusBar {
        dock: bottom;
    }

    Horizontal {
        height: auto;
        gap: 2;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    weather_report: reactive[Optional[WeatherReport]] = reactive(None)
    _refreshing: reactive[bool] = reactive(False)

    def __init__(self, client: Optional[WeatherClient] = None) -> None:
        super().__init__()
        self.client = client or WeatherClient()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="body"):
            with Horizontal():
                self.current_panel = CurrentWeatherPanel()
                self.hourly_panel = HourlyForecastPanel()
                yield self.current_panel
                yield self.hourly_panel
        self.status = StatusBar("Starting…")
        yield self.status
        yield Footer()

    async def on_mount(self) -> None:
        await self.refresh_weather()

    async def action_refresh(self) -> None:
        await self.refresh_weather(force=True)

    async def refresh_weather(self, force: bool = False) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        self.status.update("Fetching latest weather…")
        try:
            report = await asyncio.to_thread(self.client.fetch_weather)
        except Exception as exc:  # pragma: no cover - visual feedback only
            self.status.update(f"Fetch failed: {exc}")
            self._refreshing = False
            return

        self.weather_report = report
        timestamp = report.fetched_at.strftime("%I:%M %p").lstrip("0")
        self.status.update(f"Updated at {timestamp}")
        self._refreshing = False

    def watch_weather_report(self, report: Optional[WeatherReport]) -> None:
        self.current_panel.update_report(report)
        self.hourly_panel.update_report(report)


def _c_to_f(celsius: float) -> float:
    return celsius * 9 / 5 + 32


def _wind_direction_to_text(degrees: int) -> str:
    directions = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    index = int((degrees % 360) / 22.5 + 0.5) % 16
    return directions[index]


def run_tui() -> None:
    app = WeatherApp()
    app.run()


def run_once() -> None:
    client = WeatherClient()
    report = client.fetch_weather()
    timestamp = report.fetched_at.strftime("%Y-%m-%d %H:%M")
    print(f"Weather for {report.location} at {timestamp}")
    print(f"{report.summary} | Temp {report.temperature_c:.1f}°C / {_c_to_f(report.temperature_c):.1f}°F")
    print(f"Feels like {report.feels_like_c:.1f}°C | Humidity {report.humidity}%")
    print(f"Wind {report.wind_speed_kph:.1f} km/h {_wind_direction_to_text(report.wind_direction_deg)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="New Haven weather TUI")
    parser.add_argument("--once", action="store_true", help="Fetch and print weather once, without the TUI")
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_tui()


if __name__ == "__main__":
    main()
