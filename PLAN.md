# Plan de trabajo — AutoBrower

Proyecto Python que captura y reproduce acciones del ratón **a nivel de sistema
operativo**, agnóstico al navegador. Soporta múltiples perfiles de grabación
para distintos contextos (Chrome, Brave, Firefox, o cualquier aplicación).

---

## Fase 0 — Estructura del proyecto

- [ ] Inicializar estructura de directorios:
  ```
  autobrower/
  ├── autobrower/
  │   ├── __init__.py
  │   ├── config.py        # Carga de .env y constantes
  │   ├── recorder.py       # Grabación de eventos del ratón (OS-level)
  │   ├── player.py         # Reproducción en bucle (OS-level)
  │   └── cli.py            # Punto de entrada (CLI)
  ├── profiles/             # Directorio donde se guardan los perfiles
  ├── .env.example
  ├── requirements.txt
  └── PLAN.md
  ```
- [ ] Crear `.env.example` con las variables de configuración
- [ ] Crear `requirements.txt` con dependencias

## Fase 1 — Configuración (config.py)

- [ ] Cargar variables desde `.env`:
  - `SAMPLE_INTERVAL` — Intervalo de muestreo en segundos (por defecto `0.16`)
  - `PROFILES_DIR` — Directorio de perfiles (por defecto `./profiles`)
- [ ] Función para resolver la ruta de un perfil por nombre

## Fase 2 — Grabación de eventos del ratón (recorder.py)

- [ ] Usar `pynput.mouse.Listener` para capturar eventos a nivel de OS:
  - `move` → registrar posición `(x, y)`
  - `click` → registrar `(x, y, button, pressed)`
  - `scroll` → registrar `(x, y, dx, dy)`
- [ ] Cada evento se almacena con timestamp relativo al inicio de la grabación
- [ ] Formato de evento:
  ```json
  {
    "t": 0.163,
    "type": "move|click|scroll",
    "x": 512,
    "y": 340,
    "button": "left|right|middle",
    "pressed": true,
    "dx": 0,
    "dy": -3
  }
  ```
- [ ] Muestreo de `move`: solo registrar un `move` cada `SAMPLE_INTERVAL`
  para evitar miles de eventos por segundo (los clicks y scrolls se registran
  siempre, sin throttle)
- [ ] Al finalizar (Ctrl+C), guardar en `profiles/<nombre>.json`

## Fase 3 — Reproducción en bucle (player.py)

- [ ] Cargar perfil desde `profiles/<nombre>.json`
- [ ] Para cada evento, usar `pyautogui` para ejecutar la acción a nivel de OS:
  - `move` → `pyautogui.moveTo(x, y)`
  - `click` → `pyautogui.click(x, y, button=...)`  (solo en `pressed=true`)
  - `scroll` → `pyautogui.scroll(dy, x, y)`
- [ ] Respetar los deltas de tiempo entre eventos (`time.sleep(delta)`)
- [ ] Bucle infinito: al terminar la secuencia, reiniciar desde el primer evento
- [ ] Mecanismo de parada segura: Ctrl+C o hotkey configurable

## Fase 4 — CLI (cli.py)

- [ ] Subcomando `record <perfil>`:
  - Inicia grabación y la guarda como `profiles/<perfil>.json`
  - Flag `--interval` / `-i` para override de `SAMPLE_INTERVAL`
- [ ] Subcomando `play <perfil>`:
  - Reproduce en bucle el perfil indicado
  - Flag `--no-loop` para una sola ejecución
  - Flag `--speed` para multiplicador de velocidad (por defecto `1.0`)
- [ ] Subcomando `list`:
  - Muestra los perfiles disponibles con metadatos (duración, nº eventos)
- [ ] Subcomando `delete <perfil>`:
  - Elimina un perfil

## Fase 5 — Testing y pulido

- [ ] Tests unitarios para `config.py`
- [ ] Tests para serialización/deserialización de perfiles
- [ ] Test de reproducción con mock de pyautogui
- [ ] README.md (se deja para el final)

---

## Dependencias principales

| Paquete | Uso |
|---------|-----|
| `pynput` | Captura de eventos de ratón a nivel de OS (listener) |
| `pyautogui` | Reproducción de acciones de ratón a nivel de OS |
| `python-dotenv` | Carga de `.env` |

## Notas técnicas

- **OS-level, no CDP**: Al operar a nivel de sistema operativo, el programa es
  completamente agnóstico al navegador. Funciona con Chrome, Brave, Firefox, o
  cualquier otra aplicación.
- **pynput para grabar, pyautogui para reproducir**: `pynput` ofrece listeners
  no intrusivos para captura. `pyautogui` proporciona control directo del
  cursor para reproducción.
- **Perfiles**: Cada grabación se guarda como un archivo JSON independiente.
  Se pueden tener múltiples perfiles (ej: `chrome-login`, `brave-scroll`,
  `firefox-test`) y ejecutar el que se necesite.
- **Throttle de movimiento**: Solo se aplica a `move`. Los `click` y `scroll`
  se registran siempre para no perder acciones.
- **Precisión temporal**: `SAMPLE_INTERVAL=0.16s` ≈ 6 muestras/s de movimiento.
  Suficiente para reproducir trayectorias suaves.
