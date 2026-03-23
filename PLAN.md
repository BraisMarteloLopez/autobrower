# Plan de trabajo — AutoBrower

Proyecto Python que usa el modo depuración de Brave (Chrome DevTools Protocol)
para grabar y reproducir acciones del ratón en el navegador.

---

## Fase 0 — Estructura del proyecto

- [ ] Inicializar estructura de directorios:
  ```
  autobrower/
  ├── autobrower/
  │   ├── __init__.py
  │   ├── config.py        # Carga de .env y constantes
  │   ├── cdp_connection.py # Conexión CDP a Brave
  │   ├── recorder.py       # Grabación de eventos del ratón
  │   ├── player.py         # Reproducción en bucle
  │   └── cli.py            # Punto de entrada (CLI)
  ├── .env.example
  ├── requirements.txt
  ├── pyproject.toml
  └── PLAN.md
  ```
- [ ] Crear `.env.example` con las variables de configuración
- [ ] Crear `requirements.txt` / `pyproject.toml` con dependencias

## Fase 1 — Configuración y conexión CDP

- [ ] **config.py** — Cargar variables desde `.env`:
  - `BRAVE_PATH` — Ruta al ejecutable de Brave
  - `CDP_PORT` — Puerto para depuración remota (por defecto `9222`)
  - `SAMPLE_INTERVAL` — Intervalo de muestreo en segundos (por defecto `0.16`)
  - `RECORDING_FILE` — Ruta del archivo donde guardar la grabación (por defecto `recording.json`)
- [ ] **cdp_connection.py** — Lanzar Brave en modo depuración y conectar:
  - Lanzar Brave con `--remote-debugging-port=CDP_PORT`
  - Conectar vía websocket al endpoint CDP (`/json/version`)
  - Exponer métodos para enviar comandos CDP y recibir eventos

## Fase 2 — Grabación de eventos del ratón (recorder.py)

- [ ] Inyectar JavaScript en la página activa vía `Runtime.evaluate` para:
  - Escuchar `mousemove`, `mousedown`, `mouseup`, `click`, `dblclick`, `scroll`
  - Almacenar cada evento con: `{timestamp, type, x, y, button, scrollDelta}`
  - Exponer una función JS que devuelva los eventos acumulados
- [ ] Desde Python, cada `SAMPLE_INTERVAL` segundos:
  - Llamar a la función JS inyectada para recoger los eventos pendientes
  - Acumular en una lista local
- [ ] Al finalizar (Ctrl+C o señal), guardar la lista completa en `RECORDING_FILE` como JSON

## Fase 3 — Reproducción en bucle (player.py)

- [ ] Cargar `RECORDING_FILE`
- [ ] Para cada evento, usar CDP para simular la acción:
  - `Input.dispatchMouseEvent` con `type`, coordenadas, `button`, `timestamp` relativo
- [ ] Respetar los deltas de tiempo entre eventos (sleep con el delta)
- [ ] Al terminar la secuencia, reiniciar desde el principio (bucle infinito)
- [ ] Permitir interrumpir con Ctrl+C

## Fase 4 — CLI (cli.py)

- [ ] Subcomando `record` — Inicia grabación hasta Ctrl+C
- [ ] Subcomando `play` — Reproduce en bucle la grabación
- [ ] Flags opcionales:
  - `--interval` / `-i` para override de `SAMPLE_INTERVAL`
  - `--file` / `-f` para override de `RECORDING_FILE`
  - `--loop` / `--no-loop` para controlar la repetición

## Fase 5 — Testing y pulido

- [ ] Tests unitarios para `config.py` (carga de .env)
- [ ] Tests para serialización/deserialización de grabaciones
- [ ] Test de integración básico (mock de CDP)
- [ ] README.md (se deja para el final)

---

## Dependencias principales

| Paquete | Uso |
|---------|-----|
| `websockets` | Comunicación CDP vía WebSocket |
| `python-dotenv` | Carga de `.env` |
| `asyncio` | Manejo asíncrono de la conexión CDP |

## Notas técnicas

- **CDP vs Selenium/Playwright**: Usamos CDP directamente para tener control
  total sobre los eventos de input sin capas intermedias.
- **Inyección JS**: Necesaria porque CDP no tiene un evento nativo de "mouse
  position changed" — los eventos de input solo permiten *despachar*, no
  *escuchar*. La escucha se hace en JS dentro de la página.
- **Precisión temporal**: `SAMPLE_INTERVAL=0.16s` ≈ 6 muestras/segundo. Es
  suficiente para reproducir movimientos suaves del ratón.
