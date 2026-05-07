# Practica P4 - Guia de ejecucion y entrega

Esta carpeta `respuestas/` contiene los archivos que puedes subir a la maquina Linux del laboratorio para ejecutar la practica y obtener tiempos:

- `Lab4map.c` y `Lab4rec.c`: programas originales del enunciado.
- `Lab4mapB.c` y `Lab4recB.c`: versiones optimizadas para E4 usando distributiva/asociativa.
- `SLURM_P4_original.sh`: ejecucion remota de originales en SLURM.
- `SLURM_P4_optimized.sh`: ejecucion remota de versiones B en SLURM.
- `run_local_original.sh`: ejecucion local interactiva de originales.
- `run_local_optimized.sh`: ejecucion local interactiva de versiones B.
- `parse_perf_results.py`: parser para convertir salidas `perf stat` en tablas Markdown con tiempo, IPC y ciclos/iteracion.

## 1. Que pide la practica

La practica tiene cuatro bloques:

- E1: usar RVCAT con los JSON `recB-AVX`, `recC-AVX` y `recC.O3-AVX`, comparar con la tabla E1 y explicar cadenas recurrentes.
- E2: ejecutar `Lab4map.c` y `Lab4rec.c`, remoto por SLURM y local en Alder Lake, completar tabla de rendimiento y analizar ASM.
- E3: explicar si cada ejecucion esta limitada por latencia/dependencias o por throughput/capacidad de ejecucion.
- E4: crear versiones optimizadas `Lab4mapB.c` y `Lab4recB.c`, ejecutarlas igual que E2, calcular mejora y explicar por que cambia el rendimiento.

## 2. Subir archivos a la maquina del laboratorio

Desde tu PC, estando en `C:\Users\pierr\Downloads\ac`, sube la carpeta a tu cuenta del laboratorio. Cambia `USUARIO` por tu usuario real y el host si usas otro login:

```bash
scp -r respuestas USUARIO@aolin-login.uab.es:~/P4
```

En la maquina Linux:

```bash
cd ~/P4/respuestas
chmod +x *.sh parse_perf_results.py
ls -l
```

Si ya estas dentro del laboratorio y tienes acceso directo a `/home/alumnos/ac/alumnos/LAB4`, tambien puedes comparar con los ficheros oficiales:

```bash
ls -l /home/alumnos/ac/alumnos/LAB4
```

## 3. Comprobar colas SLURM

Ejecuta:

```bash
sinfo
sinfo -p xeon.q -N
squeue
```

Para E2.Q3 apunta:

- nodos definidos en `xeon.q`: salen en `sinfo -p xeon.q -N`.
- nodo usado realmente: sale en la primera linea del `OUT.P4.txt`, porque el script ejecuta `hostname`.
- modelo de CPU: sale en `lscpu`, campo `Nombre del modelo` o `Model name`.

En el `OUT.P4.txt` publicado el nodo fue:

- host: `aolin-cpu-1.uab.cat`
- CPU: `Intel(R) Xeon(R) CPU E5-2603 v2 @ 1.80GHz`
- microarquitectura usada en la practica: Sandy Bridge

## 4. Ejecutar programas originales en remoto

Desde `~/P4/respuestas`:

```bash
sbatch -p xeon.q -o OUT.P4.original.txt --exclusive SLURM_P4_original.sh
squeue
```

Cuando termine:

```bash
cat OUT.P4.original.txt
ls -lh *.perf
python3 parse_perf_results.py OUT.P4.original.txt
```

Para ver el perfil y el ensamblador:

```bash
perf report -i L4map.Of.remote.perf
perf report -i L4rec.Of.remote.perf
perf report -i L4map.Of.remote.perf --stdio > report_L4map_remote.txt
perf report -i L4rec.Of.remote.perf --stdio > report_L4rec_remote.txt
perf annotate -i L4map.Of.remote.perf --stdio --symbol=func > asm_L4map_remote.txt
perf annotate -i L4rec.Of.remote.perf --stdio --symbol=func > asm_L4rec_remote.txt
```

Resultado remoto publicado para los originales, por si necesitas comprobar:

| Programa | Nodo | Time | Cycles | Instructions | IPC | Cycles/asm iteration |
|---|---|---:|---:|---:|---:|---:|
| Lab4map | Sandy Bridge remoto | 4.3617 s | 7.7607 G | 21.3686 G | 2.75 | 6.21 |
| Lab4rec | Sandy Bridge remoto | 10.6513 s | 18.9658 G | 13.0034 G | 0.69 | 18.97 |

Calculo usado:

- `Lab4map`: `X=2500`, `REP=4000000`, fuente = `10G` iteraciones. El bucle ASM esta vectorizado con 8 lanes, por tanto iteraciones ASM = `10G / 8`; `7.760G / 1.25G = 6.21 cycles/iteration`.
- `Lab4rec`: `X=2500`, `REP=400000`, fuente = `1G` iteraciones. No se vectoriza por recurrencia, por tanto `18.966G / 1G = 18.97 cycles/iteration`.

## 5. Ejecutar programas originales en local

En el nodo local/login Alder Lake:

```bash
./run_local_original.sh > OUT.P4.local.original.txt 2>&1
python3 parse_perf_results.py OUT.P4.local.original.txt
```

Guarda tambien:

```bash
perf report -i L4map.Of.local.perf --stdio > report_L4map_local.txt
perf report -i L4rec.Of.local.perf --stdio > report_L4rec_local.txt
perf annotate -i L4map.Of.local.perf --stdio --symbol=func > asm_L4map_local.txt
perf annotate -i L4rec.Of.local.perf --stdio --symbol=func > asm_L4rec_local.txt
```

Con estos datos completas E2.Q4 para:

- `Lab4map` remoto Sandy Bridge.
- `Lab4map` local Alder Lake.
- `Lab4rec` remoto Sandy Bridge.
- `Lab4rec` local Alder Lake.

## 6. Ejecutar versiones optimizadas B

Las versiones B aplican:

```text
(L1*A + L2*B) * (L3*A + L4*B) * L5
= K1*A*A + K2*A*B + K3*B*B

K1 = L1*L3*L5
K2 = (L1*L4 + L2*L3)*L5
K3 = L2*L4*L5
```

Remoto por SLURM:

```bash
sbatch -p xeon.q -o OUT.P4.optimized.txt --exclusive SLURM_P4_optimized.sh
squeue
```

Cuando termine:

```bash
cat OUT.P4.optimized.txt
python3 parse_perf_results.py OUT.P4.optimized.txt
perf report -i L4mapB.Of.remote.perf --stdio > report_L4mapB_remote.txt
perf report -i L4recB.Of.remote.perf --stdio > report_L4recB_remote.txt
perf annotate -i L4mapB.Of.remote.perf --stdio --symbol=func > asm_L4mapB_remote.txt
perf annotate -i L4recB.Of.remote.perf --stdio --symbol=func > asm_L4recB_remote.txt
```

Local:

```bash
./run_local_optimized.sh > OUT.P4.local.optimized.txt 2>&1
python3 parse_perf_results.py OUT.P4.local.optimized.txt
perf report -i L4mapB.Of.local.perf --stdio > report_L4mapB_local.txt
perf report -i L4recB.Of.local.perf --stdio > report_L4recB_local.txt
perf annotate -i L4mapB.Of.local.perf --stdio --symbol=func > asm_L4mapB_local.txt
perf annotate -i L4recB.Of.local.perf --stdio --symbol=func > asm_L4recB_local.txt
```

Para calcular mejora:

```text
speedup_time = Time_original / Time_B
speedup_cycles_iter = CyclesPerIter_original / CyclesPerIter_B
```

## 7. Como contestar E1

Usa RVCAT con:

- `AlderLake.pdf`: configuracion de procesador Alder Lake.
- `recB-AVX.pdf`
- `recC-AVX.pdf`
- `recC.O3-AVX.pdf`

Puntos que deben aparecer en la respuesta:

- En `recB`, `recC` y `recC.O3` cada iteracion del bucle simulado corresponde a dos iteraciones del bucle fuente porque se ha hecho un unroll de 2 (`i += 2`). Por eso la tabla E1 muestra `Cycles/Iter` e `Instr/Iter` divididos entre 2 respecto a RVCAT.
- `recB-AVX`: cadena recurrente principal: `t0` entra en `t0 = t5 * t0 - t1`, el resultado se usa como entrada de la segunda iteracion desenrollada, vuelve a `t0 = t5 * t0 - t1`, se guarda `V[i+2]` y ese valor alimenta la siguiente iteracion del bucle. El limite viene de esa cadena de FMA recurrente.
- `recC-AVX`: la transformacion intenta calcular directamente `V[i+2]` a partir de `Vprev`, pero la version `-Ofast` genera una cadena donde `V[i+1]` sigue en el camino critico: `t3 -> t2 = t2*t3 -> t0 = ... + t2 -> t0 = t0*t1 -> t4 = ... + t0 -> t3 = t4`.
- `recC.O3-AVX`: el compilador conserva mejor la forma algebraica propuesta; la cadena recurrente queda mas corta: `Vprev -> Vprev = Vprev*t3 + C2 -> siguiente iteracion`. Ademas almacena `V[i+1:i+2]` con una operacion vectorial.
- Papel del programador: propone una forma algebraicamente equivalente y con mas paralelismo explicito.
- Papel del compilador: decide instrucciones concretas, uso de FMA, unroll, stores vectoriales y scheduling; `-Ofast` puede reordenar flotantes y `-O3` es mas conservador, lo que aqui cambia el ASM y el rendimiento.

## 8. Como contestar E2

E2.Q1:

- `funcMap`: patron map, cada iteracion calcula `C[x]` de forma independiente. En C fuente: 6 multiplicaciones FP, 2 sumas FP, 2 loads (`A[x]`, `B[x]`) y 1 store (`C[x]`) por iteracion escalar. No hay cadena recurrente de datos FP entre iteraciones; solo control del bucle.
- `funcRec`: patron recurrente/stencil temporal de primer orden, porque `B[x+1]` depende de `B[x]`. En C fuente: 6 multiplicaciones FP, 2 sumas FP, 2 loads (`A[x]`, `B[x]`) y 1 store (`B[x+1]`). Hay cadena recurrente FP a traves de `B[x] -> B[x+1] -> B[x+2]`.

E2.Q2:

- Linea `hostname`: imprime el nodo donde se ejecuta el job.
- Linea `lscpu`: imprime arquitectura, modelo de CPU, caches, nucleos y flags.
- Compilador: `module add gcc/13.2.1`; compilacion con `gcc -Ofast -march=native`.
- Metricas medidas por `perf stat -e instructions,cycles,task-clock`: instrucciones retiradas, ciclos y tiempo de CPU. Con ellas calculas IPC = `instructions/cycles`.
- `perf record` genera perfiles `.perf` para inspeccionar donde se gastan los ciclos y ver ensamblador.

E2.Q5:

- Compara tus `asm_*.txt` con las figuras E2.1-E2.4 del enunciado.
- Para `Lab4map`, el compilador vectoriza porque no hay dependencias entre iteraciones. Sandy Bridge procesa 8 floats con mas uops/shuffles; Alder Lake usa AVX/FMA mas compacto.
- Para `Lab4rec`, el compilador no puede vectorizar el bucle principal porque `B[x+1]` depende de `B[x]`. En Alder Lake aparecen FMA escalares que reducen numero de instrucciones frente a Sandy Bridge.

## 9. Como contestar E3

Usa la tabla E3.1 del enunciado:

- Sandy Bridge: dispatch 4 uops/ciclo; LOAD 5; FPmul 5; FPadd 3; Vshuffle P5; no FMA.
- Alder Lake: dispatch 6 uops/ciclo; LOAD 4; FPmul/FMA 4; FPadd 3; mas puertos disponibles.

Metodo para cada programa y CPU:

1. Cuenta uops por iteracion ASM usando las descripciones abstractas del enunciado o tus `asm_*.txt`.
2. Calcula limite de dispatch: `uops_iter / dispatch_width`.
3. Calcula limites por puerto o grupos de puertos relevantes. Ejemplo dado: `Lab4map.remote` tiene 19 uops e impone al menos `19/4 = 4.75 cycles/iter` por dispatch.
4. Calcula la cadena recurrente de dependencias. En `Lab4map` casi solo existe la cadena de control del bucle; en `Lab4rec` la cadena FP por `B[x]` suele dominar.
5. Compara el maximo teorico con tu `Cycles/asm iteration` real.

Conclusion esperada:

- `Lab4map`: normalmente throughput-bound, porque las iteraciones son independientes y el limite viene de dispatch/puertos.
- `Lab4rec`: normalmente latency-bound, porque el valor `B[x+1]` alimenta la siguiente iteracion y forma una cadena recurrente larga.

## 10. Como contestar E4

Para `Lab4mapB`:

- La transformacion reduce/profundiza distinto el grafo de dependencias y da mas oportunidades al compilador para usar FMA y paralelizar subexpresiones.
- Sigue siendo vectorizable porque cada `C[x]` es independiente.
- El checksum puede cambiar ligeramente por reordenacion de operaciones FP; el enunciado lo permite.

Para `Lab4recB`:

- La recurrencia no desaparece, pero se acorta la cadena critica algebraica.
- En el codigo entregado se mantiene `bx` en registro para evitar recargar `B[x]` desde memoria en cada iteracion.
- Debes explicar la cadena recurrente nueva como `bx -> (K3*bx + K2*ax) -> nuevo bx -> siguiente iteracion`.

Tabla a rellenar con `parse_perf_results.py`:

| Program | Computer | Time | CycleCount | InstrCount | IPC | Cycles/Iteration | Speedup |
|---|---|---:|---:|---:|---:|---:|---:|
| Lab4mapB | Remote Sandy Bridge | | | | | | |
| Lab4mapB | Local Alder Lake | | | | | | |
| Lab4recB | Remote Sandy Bridge | | | | | | |
| Lab4recB | Local Alder Lake | | | | | | |

## 11. Archivos que conviene descargar al final

Despues de ejecutar todo, guarda estos archivos para poder redactar la entrega:

- `OUT.P4.original.txt`
- `OUT.P4.local.original.txt`
- `OUT.P4.optimized.txt`
- `OUT.P4.local.optimized.txt`
- `report_*.txt`
- `asm_*.txt`
- los cuatro `.c`
- opcionalmente los `.perf` si quieres volver a abrir `perf report` en la VM

Ejemplo desde tu PC:

```bash
scp -r USUARIO@aolin-login.uab.es:~/P4/respuestas ~/P4_resultados
```

