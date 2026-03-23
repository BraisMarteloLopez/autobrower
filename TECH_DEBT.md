# Deuda técnica — AutoBrower

## Bugs

### BUG-1: Crash si la grabación tiene 0 eventos
- **Archivo**: `cli.py:19`
- **Descripción**: `recorder.events[-1]['t']` lanza `IndexError` si el
  usuario pulsa Ctrl+C inmediatamente y no se registró ningún evento.
- **Fix**: Comprobar `len(recorder.events) > 0` antes de acceder.

### BUG-2: El primer evento move siempre se pierde
- **Archivo**: `recorder.py:17, 56`
- **Descripción**: `_last_move_time` se inicializa a `0.0` y `_start_time`
  también es `0.0` (o cercano), así que `elapsed - 0.0 ≈ 0.0 < 0.16` →
  el primer move se descarta siempre.
- **Fix**: Inicializar `_last_move_time = -interval` para que el primer
  move pase el throttle.

### BUG-3: `pyautogui.PAUSE = 0` como side-effect de import
- **Archivo**: `player.py:9`
- **Descripción**: Se ejecuta al importar el módulo, alterando estado global
  de pyautogui incluso si solo se importa para tests.
- **Fix**: Mover a dentro de `Player.play()` o `Player.__init__()`.

## Debilidades de diseño

### DEBT-1: `list_profiles()` carga el JSON completo
- **Archivo**: `config.py:20-36`
- **Descripción**: Para leer solo nombre/duración/event_count, carga todo el
  archivo incluyendo miles de eventos. Con grabaciones largas es ineficiente.
- **Fix**: Guardar metadatos en cabecera separada, o leer solo los primeros
  bytes del JSON.

### DEBT-2: Sin validación del nombre de perfil (path traversal)
- **Archivo**: `config.py:14-17`
- **Descripción**: `get_profile_path("../../etc/algo")` crearía archivos
  fuera de `PROFILES_DIR`.
- **Fix**: Validar que el nombre solo contiene caracteres seguros
  (`[a-zA-Z0-9_-]`) o resolver el path y verificar que está dentro de
  `PROFILES_DIR`.

### DEBT-3: Sobrescritura silenciosa de perfiles
- **Archivo**: `recorder.py:73-86`, `cli.py:9-19`
- **Descripción**: `record mi-perfil` sobrescribe sin avisar si ya existe.
- **Fix**: Comprobar existencia y pedir confirmación, o añadir flag `--force`.

### DEBT-4: `dx` de scroll se graba pero no se reproduce
- **Archivo**: `player.py:44-46`
- **Descripción**: Se registra `dx` (scroll horizontal) en la grabación pero
  `pyautogui.scroll()` solo acepta scroll vertical. El scroll horizontal se
  pierde silenciosamente.
- **Fix**: Usar `pyautogui.hscroll(dx)` en plataformas que lo soporten, o
  documentar la limitación.

### DEBT-5: Sin pausa entre ciclos de loop
- **Archivo**: `player.py:54-68`
- **Descripción**: Al terminar un ciclo y empezar el siguiente, el último
  evento del ciclo N y el primero del ciclo N+1 se ejecutan sin ningún delay.
- **Fix**: Añadir un delay configurable entre ciclos, o al menos respetar el
  delta del último evento al inicio del siguiente ciclo.

### DEBT-6: Tests de config usan `importlib.reload`
- **Archivo**: `tests/test_config.py`
- **Descripción**: Recargar el módulo para testear distintas configuraciones
  es frágil y puede causar interferencias si los tests se ejecutan en paralelo.
- **Fix**: Refactorizar config para exponer una función `load_config()` que
  retorne un objeto en vez de usar variables de módulo.
