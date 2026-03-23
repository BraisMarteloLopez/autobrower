# Plan de trabajo — AutoBrower

Proyecto Python que captura y reproduce acciones del ratón **a nivel de sistema
operativo**, agnóstico al navegador. Soporta múltiples perfiles de grabación
para distintos contextos (Chrome, Brave, Firefox, o cualquier aplicación).

---

## Fase 0 — Estructura y scaffolding

### 0.1 — Crear árbol de directorios
```
autobrower/
├── autobrower/
│   ├── __init__.py
│   ├── config.py
│   ├── recorder.py
│   ├── player.py
│   └── cli.py
├── profiles/
│   └── .gitkeep
├── .env.example
├── requirements.txt
└── PLAN.md
```

### 0.2 — requirements.txt
```
pynput>=1.7
pyautogui>=0.9
python-dotenv>=1.0
```

### 0.3 — .env.example
```env
SAMPLE_INTERVAL=0.16
PROFILES_DIR=./profiles
```

---

## Fase 1 — config.py

### 1.1 — Cargar .env
- Llamar a `load_dotenv()` al importar el módulo
- Definir constantes con valores por defecto:
  - `SAMPLE_INTERVAL: float` → `float(os.getenv("SAMPLE_INTERVAL", "0.16"))`
  - `PROFILES_DIR: str` → `os.getenv("PROFILES_DIR", "./profiles")`

### 1.2 — Helper de rutas de perfil
- `get_profile_path(name: str) -> Path`
  - Retorna `PROFILES_DIR / f"{name}.json"`
  - Crea `PROFILES_DIR` si no existe (`mkdir -p`)

### 1.3 — Helper de listado
- `list_profiles() -> list[dict]`
  - Escanea `PROFILES_DIR/*.json`
  - Para cada archivo, lee solo los metadatos (primeros campos del JSON)
  - Retorna lista de `{name, created, duration, event_count}`

---

## Fase 2 — recorder.py

### 2.1 — Estructura de datos del evento
- Definir dataclass o TypedDict `MouseEvent`:
  ```python
  {
    "t": float,        # segundos desde inicio
    "type": str,        # "move" | "click" | "scroll"
    "x": int,
    "y": int,
    "button": str|None, # "left" | "right" | "middle" | None
    "pressed": bool|None,
    "dx": int|None,
    "dy": int|None
  }
  ```

### 2.2 — Clase Recorder
- `__init__(self, interval: float)`:
  - `self.events: list[dict] = []`
  - `self.interval = interval`
  - `self.start_time: float = 0`
  - `self.last_move_time: float = 0`

- **Callbacks de pynput:**
  - `_on_move(self, x, y)`:
    - Calcular `now - start_time` → `t`
    - Si `t - last_move_time < interval` → descartar (throttle)
    - Si no → append evento `move`, actualizar `last_move_time`
  - `_on_click(self, x, y, button, pressed)`:
    - Siempre registrar (sin throttle)
    - `button` → convertir `pynput.mouse.Button` a string
  - `_on_scroll(self, x, y, dx, dy)`:
    - Siempre registrar (sin throttle)

### 2.3 — Método start/stop
- `start(self)`:
  - `self.start_time = time.monotonic()`
  - Crear `pynput.mouse.Listener` con los 3 callbacks
  - Iniciar listener (es un thread)
  - Bloquear en `listener.join()` (se interrumpe con Ctrl+C)
- `stop(self)`:
  - Detener el listener

### 2.4 — Método save
- `save(self, profile_name: str)`:
  - Construir documento JSON:
    ```json
    {
      "name": "chrome-login",
      "created": "2026-03-23T10:30:00",
      "duration": 45.2,
      "event_count": 1230,
      "events": [...]
    }
    ```
  - Escribir en `get_profile_path(profile_name)`

---

## Fase 3 — player.py

### 3.1 — Carga de perfil
- `load_profile(name: str) -> dict`:
  - Leer JSON desde `get_profile_path(name)`
  - Validar que existe y tiene el formato esperado
  - Retornar el documento completo

### 3.2 — Clase Player
- `__init__(self, profile: dict, speed: float = 1.0, loop: bool = True)`:
  - `self.events = profile["events"]`
  - `self.speed = speed`
  - `self.loop = loop`
  - `self.running = False`

### 3.3 — Ejecución de un evento
- `_dispatch(self, event: dict)`:
  - Según `event["type"]`:
    - `"move"` → `pyautogui.moveTo(x, y, duration=0)`
    - `"click"` y `pressed=True` → `pyautogui.mouseDown(x, y, button=...)`
    - `"click"` y `pressed=False` → `pyautogui.mouseUp(x, y, button=...)`
    - `"scroll"` → `pyautogui.scroll(dy, x, y)`

### 3.4 — Bucle de reproducción
- `play(self)`:
  - `self.running = True`
  - `pyautogui.FAILSAFE = True` (mover ratón a esquina superior-izq para abortar)
  - Bucle:
    - Iterar `events` por pares `(current, next)`
    - Ejecutar `_dispatch(current)`
    - Calcular `delta = (next.t - current.t) / speed`
    - `time.sleep(delta)`
    - Al final de la lista: si `self.loop` → reiniciar, si no → parar
  - Capturar `KeyboardInterrupt` para parada limpia

---

## Fase 4 — cli.py

### 4.1 — Configurar argparse
- Parser principal: `autobrower`
- Subparsers: `record`, `play`, `list`, `delete`

### 4.2 — Subcomando `record`
```
autobrower record <perfil> [--interval 0.16]
```
- Instanciar `Recorder(interval=...)`
- Imprimir mensaje "Grabando... Ctrl+C para detener"
- `recorder.start()` (bloquea hasta Ctrl+C)
- `recorder.save(perfil)`
- Imprimir resumen: duración, nº eventos

### 4.3 — Subcomando `play`
```
autobrower play <perfil> [--speed 1.0] [--no-loop]
```
- `load_profile(perfil)`
- Instanciar `Player(profile, speed, loop)`
- Imprimir mensaje "Reproduciendo... Ctrl+C o esquina sup-izq para detener"
- `player.play()`

### 4.4 — Subcomando `list`
```
autobrower list
```
- `list_profiles()`
- Imprimir tabla: nombre, fecha, duración, nº eventos

### 4.5 — Subcomando `delete`
```
autobrower delete <perfil>
```
- Confirmar con el usuario (input y/n)
- Eliminar archivo

### 4.6 — Entry point
- `if __name__ == "__main__"` en `cli.py`
- También registrar en `pyproject.toml` si se añade más adelante

---

## Fase 5 — Testing

### 5.1 — Tests de config
- Verificar valores por defecto
- Verificar override desde .env
- Verificar creación de directorio de perfiles

### 5.2 — Tests de recorder
- Mock de `pynput.mouse.Listener`
- Verificar throttle de moves
- Verificar que clicks y scrolls no se throttlean
- Verificar formato del JSON de salida

### 5.3 — Tests de player
- Mock de `pyautogui`
- Verificar que cada tipo de evento llama a la función correcta
- Verificar cálculo de deltas con speed multiplier
- Verificar que loop reinicia la secuencia

### 5.4 — Tests de CLI
- Verificar parsing de argumentos
- Verificar subcomandos con mocks

---

## Orden de implementación

```
Fase 0 (scaffolding)
  └→ Fase 1 (config)
       └→ Fase 2 (recorder)    ← primera funcionalidad usable: grabar
            └→ Fase 3 (player) ← segunda funcionalidad usable: reproducir
                 └→ Fase 4 (CLI) ← todo integrado
                      └→ Fase 5 (tests)
```

Cada fase es un commit independiente. Al final de la Fase 2 ya se puede
probar la grabación manualmente. Al final de la Fase 3 el producto mínimo
está completo.

---

## Dependencias

| Paquete | Uso |
|---------|-----|
| `pynput` | Listener de ratón a nivel de OS |
| `pyautogui` | Control de ratón a nivel de OS |
| `python-dotenv` | Carga de `.env` |

## Notas técnicas

- **pynput para grabar, pyautogui para reproducir**: `pynput` tiene listeners
  pasivos (no intrusivos). `pyautogui` tiene control activo del cursor.
- **Throttle solo en move**: Los clicks y scrolls son discretos y escasos,
  los moves pueden generar cientos de eventos por segundo.
- **pyautogui.FAILSAFE**: Mover el ratón a (0,0) aborta la ejecución.
  Seguridad extra ante bucle infinito.
- **time.monotonic()**: Para timestamps, no `time.time()`, evita problemas
  con ajustes de reloj del sistema.
