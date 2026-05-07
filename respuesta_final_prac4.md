# P4 - Analisis de rendimiento e identificacion de bottlenecks

## Configuracion usada

Todas las compilaciones se han hecho cargando el modulo de GCC 13:

```bash
module purge
module add gcc/13.2.1
which gcc
gcc --version
```

La version cargada fue:

```text
/opt/rh/gcc-toolset-13/root/usr/bin/gcc
gcc (GCC) 13.3.1
```

La ejecucion remota se hizo con SLURM en:

```text
aolin-cpu-1.uab.cat
Intel(R) Xeon(R) CPU E5-2603 v2 @ 1.80GHz
Microarquitectura: Sandy Bridge
```

La ejecucion local se hizo en:

```text
aolin-login.uab.cat
12th Gen Intel(R) Core(TM) i5-12400
Microarquitectura: Alder Lake
```

Nota: la ejecucion local de la practica no significa PowerShell/Windows. Segun el enunciado, la ejecucion local es en el procesador local al que estamos conectados (`aolin-login`, `aolin-login-bak` o un `aolin-xx`). Por tanto, haberla lanzado desde MobaXterm por SSH sobre `aolin-login.uab.cat` es correcto.

## E1. Algoritmo recurrente `rec`

En `recB-AVX`, `recC-AVX` y `recC.O3-AVX`, el bucle esta desenrollado con factor 2 (`i += 2`). Por eso cada iteracion simulada en RVCAT equivale a dos iteraciones del bucle fuente. La tabla E1 divide `Cycles/Iter` e `Instr/Iter` entre 2 respecto a lo que muestra el simulador.

En `recB`, la cadena recurrente principal es:

```text
t0 anterior -> t0 = t5 * t0 - t1 -> t0 segunda iteracion desenrollada
             -> t0 = t5 * t0 - t1 -> t0 siguiente iteracion del bucle
```

El rendimiento queda limitado por la latencia de las FMA dependientes.

En `recC`, el programador reescribe la expresion para calcular dos pasos de la recurrencia a la vez:

```c
Vp2   = T1*Vprev + C1;
Vprev = (T2*T1)*Vprev + (T2*C1 + C2);
```

La cadena recurrente pasa por `Vprev`, pero es mas corta que en la version original. En `recC.O3-AVX`, el compilador conserva mejor esta forma algebraica y la cadena critica queda reducida a:

```text
Vprev anterior -> Vprev = Vprev * t3 + C2 -> Vprev siguiente
```

El papel del programador es proponer una transformacion algebraica que exponga mas paralelismo. El papel del compilador es traducirla a instrucciones reales, elegir FMA, registros, stores vectoriales y scheduling. Por eso `-Ofast` y `-O3` pueden generar ensambladores y rendimientos distintos.

## E2. Lab4map y Lab4rec

### E2.Q1

`funcMap` tiene patron tipo map: cada iteracion calcula `C[x]` de forma independiente.

Por iteracion escalar del codigo fuente:

```text
6 multiplicaciones FP
2 sumas FP
2 loads: A[x], B[x]
1 store: C[x]
```

No hay cadena recurrente de datos entre iteraciones, solo dependencia de control del bucle. Por eso el compilador puede vectorizar.

`funcRec` tiene patron recurrente:

```text
B[x] -> calculo de B[x+1] -> B[x+1] usado en la siguiente iteracion
```

Por iteracion escalar tambien hay:

```text
6 multiplicaciones FP
2 sumas FP
2 loads: A[x], B[x]
1 store: B[x+1]
```

La dependencia `B[x] -> B[x+1]` impide vectorizar el bucle principal como en `Lab4map`.

### E2.Q2

En el script SLURM:

```bash
hostname
lscpu
module add gcc/13.2.1
gcc -Ofast -march=native ...
perf stat -e instructions,cycles,task-clock ...
perf record ...
```

`hostname` identifica el nodo donde se ejecuta el job. `lscpu` muestra el modelo de CPU y sus caracteristicas. Se usa GCC 13 con `-Ofast -march=native`. `perf stat` mide instrucciones, ciclos y tiempo de CPU; de ahi se calcula:

```text
IPC = Instructions / Cycles
```

`perf record` genera perfiles para analizar donde se concentran los ciclos.

### E2.Q3

El job remoto se ejecuto en:

```text
aolin-cpu-1.uab.cat
```

El procesador fue:

```text
Intel(R) Xeon(R) CPU E5-2603 v2 @ 1.80GHz
```

Segun el enunciado, esta maquina corresponde a Sandy Bridge.

### E2.Q4

Resultados finales con GCC 13:

| Program | Computer | Time | CycleCount | InstrCount | IPC | Cycles/Iteration |
|---|---|---:|---:|---:|---:|---:|
| Lab4map, X=2.5K REP=4M | Remote Sandy Bridge | 4.3485 s | 7.738 G | 21.369 G | 2.76 | 6.19 |
| Lab4map, X=2.5K REP=4M | Local Alder Lake | 0.9031 s | 3.883 G | 12.617 G | 3.25 | 3.11 |
| Lab4rec, X=2.5K REP=400K | Remote Sandy Bridge | 10.6513 s | 18.966 G | 13.003 G | 0.69 | 18.97 |
| Lab4rec, X=2.5K REP=400K | Local Alder Lake | 4.0097 s | 17.258 G | 11.003 G | 0.64 | 17.26 |

Calculo de ciclos por iteracion:

```text
Lab4map:
X * REP = 2500 * 4000000 = 10,000,000,000 iteraciones fuente
El bucle ASM usa 8 lanes SIMD.
Iteraciones ASM = 10,000,000,000 / 8

Lab4rec:
X * REP = 2500 * 400000 = 1,000,000,000 iteraciones
No se vectoriza, asi que iteraciones ASM = iteraciones fuente.
```

### E2.Q5

En `Lab4map`, el compilador vectoriza porque las iteraciones son independientes. En Sandy Bridge el ASM usa AVX con instrucciones como:

```asm
vmovups
vinsertf128
vmulps
vaddps
vextractf128
add rax, 0x20
```

El incremento `0x20 = 32` bytes indica 8 floats por iteracion. En Alder Lake el codigo es mas compacto:

```asm
vbroadcastss
vmulps
vfmadd231ps
vmovups
add rdx, 0x20
```

Esto confirma que `Lab4map` es vectorizado y procesa 8 elementos por iteracion ASM.

En `Lab4rec`, el ASM es escalar:

```asm
vmovss
vmulss
vaddss / vfmadd...ss
vmovss
add rax, 0x4
```

El incremento `0x4 = 4` bytes indica 1 float por iteracion. La razon es la recurrencia `B[x] -> B[x+1]`, que obliga a esperar el resultado anterior antes de avanzar.

## E3. Bottlenecks

`Lab4map` es principalmente throughput-bound. No hay dependencia recurrente de datos entre iteraciones, asi que el limite viene de dispatch, puertos de ejecucion, loads/stores y operaciones vectoriales. Esto se ve en los resultados:

```text
Lab4map remoto Sandy Bridge: 6.19 cycles/iteration
Lab4map local Alder Lake:   3.11 cycles/iteration
```

Alder Lake reduce mucho los ciclos por iteracion porque tiene mas capacidad de ejecucion, mas puertos utiles y FMA mas eficiente.

`Lab4rec` es principalmente latency-bound. La cadena recurrente es:

```text
B[x] -> calculo FP -> B[x+1] -> siguiente iteracion
```

Los resultados lo muestran:

```text
Lab4rec remoto Sandy Bridge: 18.97 cycles/iteration
Lab4rec local Alder Lake:   17.26 cycles/iteration
```

Aunque Alder Lake es mas rapido en tiempo real, la mejora en ciclos por iteracion es pequena comparada con `Lab4map`, porque la dependencia recurrente limita el paralelismo.

## E4. Versiones optimizadas

La expresion original es:

```text
(L1*A + L2*B) * (L3*A + L4*B) * L5
```

Aplicando distributiva:

```text
K1*A*A + K2*A*B + K3*B*B
```

donde:

```text
K1 = L1*L3*L5
K2 = (L1*L4 + L2*L3)*L5
K3 = L2*L4*L5
```

### E4.Q1

Resultados finales con GCC 13:

| Program | Computer | Time | CycleCount | InstrCount | IPC | Cycles/Iteration | Speedup |
|---|---|---:|---:|---:|---:|---:|---:|
| Lab4mapB, X=2.5K REP=4M | Remote Sandy Bridge | 3.9968 s | 7.116 G | 20.097 G | 2.82 | 5.69 | 1.09 |
| Lab4mapB, X=2.5K REP=4M | Local Alder Lake | 0.7441 s | 3.144 G | 12.597 G | 4.01 | 2.52 | 1.21 |
| Lab4recB, X=2.5K REP=400K | Remote Sandy Bridge | 8.9561 s | 15.957 G | 12.003 G | 0.75 | 15.96 | 1.19 |
| Lab4recB, X=2.5K REP=400K | Local Alder Lake | 1.8767 s | 8.047 G | 10.003 G | 1.24 | 8.05 | 2.14 |

La mejora se calcula como:

```text
Speedup = Time_original / Time_optimized
```

En `Lab4mapB`, la mejora es moderada porque el programa original ya era vectorizable. La transformacion reduce algo el trabajo y permite mejor uso de FMA, especialmente en Alder Lake.

En `Lab4recB`, la mejora es mayor porque, aunque la recurrencia no desaparece, se acorta la cadena critica. En Alder Lake el compilador genera un cuerpo escalar muy compacto con FMA:

```asm
vmovss
vmulss
vfmadd231ss
vmulss
vfmadd132ss
vmovss
```

La cadena recurrente optimizada es mas corta:

```text
B[x] -> FMA/FMA -> B[x+1]
```

Por eso `Lab4recB` local baja de `17.26` a `8.05 cycles/iteration`, con un speedup aproximado de `2.14x`.

