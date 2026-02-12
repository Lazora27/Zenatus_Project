# Zenatus Backtester Configuration

The system is controlled by `/opt/Zenatus_Backtester/config/config.yaml`.
You can also override the config path using the environment variable `ZENATUS_CONFIG_PATH`.

## Paths (`paths` section)
These define where the system looks for data, scripts, and logs.

| Key | Description | Default |
| :--- | :--- | :--- |
| `base` | Root directory of the project | `/opt/Zenatus_Backtester` |
| `documentation` | Root for logs and results | `/opt/Zenatus_Dokumentation` |
| `data` | Path to historical CSV data | `/opt/Zenatus_Backtester/99_Historic_Data` |
| `strategies` | Path to Python strategy files | `.../Strategy/Full_595/All_Strategys` |

## Backtest Parameters (`backtest` section)
Global settings for the backtest engine.

| Key | Description | Default |
| :--- | :--- | :--- |
| `timeframe` | Default timeframe to run | `1h` |
| `timeout_sec` | Max runtime per strategy (seconds) | `900` |
| `inactivity_sec` | Watchdog kill timer (no output) | `30` |
| `max_workers` | Parallel processes for Quicktest | `4` |
| `initial_capital` | Starting account balance | `10000.0` |

## Logging (`logging` section)
Controls the output format and verbosity.

| Key | Description | Default |
| :--- | :--- | :--- |
| `level` | Log level (INFO, DEBUG, ERROR) | `INFO` |
| `json_format` | Use structured JSON logs | `true` |
| `file_name` | Main log file name | `zenatus_pipeline.log` |

## Docker
When running in Docker, paths are mapped to `/app/...`.
See `docker-compose.yml` for volume mappings.
