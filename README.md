# New Haven Weather TUI

A compact terminal UI that shows live weather for New Haven, CT using the [Open-Meteo](https://open-meteo.com/) API.

## Prerequisites

- Python 3.10 or newer
- Internet connectivity for live weather requests
- (Optional) A virtual environment for dependency isolation

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

- Launch the interactive TUI (refresh with `r`, quit with `q`):

  ```bash
  python app.py
  ```

- Fetch a single snapshot without starting the UI:

  ```bash
  python app.py --once
  ```

## Notes

- Weather data is pulled from Open-Meteo without authentication; if the service is unreachable the UI will display an error in the status bar.
- The hourly forecast pane shows the next few available hours, capped at six entries to keep the layout compact.
