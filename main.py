# - Primeira chegada em t=2.0 (não consome aleatório)
# - Interchegadas ~ Uniforme[2,5]
# - Serviços ~ Uniforme[3,5]
# - Capacidade K conta (em serviço + em fila); se sistema_size == K, chegada é perdida
# - Parada: encerrar exatamente no evento cujo agendamento consumiu o 100000º aleatório

import heapq
import random
from dataclasses import dataclass

random.seed(42)  # para reprodutibilidade; pode trocar

@dataclass(order=True)
class Event:
    time: float
    kind: str        # 'arrival' ou 'departure'
    server_id: int = -1  # usado em 'departure'

def u(a, b, rng_count):
    """Uniforme[a,b]; incrementa o contador de aleatórios."""
    rng_count[0] += 1
    return a + (b - a) * random.random()

def simulate(c=1, K=5, ia=(2.0, 5.0), st=(3.0, 5.0), max_rng=100_000):
    # Estado
    t = 0.0
    system_size = 0              # total no sistema (fila + serviço)
    waiting = 0                  # apenas fila
    busy = [False] * c           # servidores ocupados
    fel = []                     # future event list (min-heap por tempo)
    lost = 0
    rng_count = [0]              # contador mutável de aleatórios
    state_time = [0.0] * (K + 1) # tempo acumulado por estado
    last_t = 0.0
    cutoff_time = None           # tempo do evento agendado com o 100000º aleatório

    def acum(to_time):
        nonlocal last_t
        dt = to_time - last_t
        if dt > 0:
            s = max(0, min(system_size, K))
            state_time[s] += dt
            last_t = to_time

    def sched_arrival(now):
        nonlocal cutoff_time
        if rng_count[0] >= max_rng:  # não agenda além do limite
            return
        ia_samp = u(ia[0], ia[1], rng_count)
        at = now + ia_samp
        heapq.heappush(fel, Event(at, 'arrival'))
        if rng_count[0] == max_rng:
            cutoff_time = at

    def sched_departure(now, sid):
        nonlocal cutoff_time
        if rng_count[0] >= max_rng:
            return
        st_samp = u(st[0], st[1], rng_count)
        dtm = now + st_samp
        heapq.heappush(fel, Event(dtm, 'departure', sid))
        if rng_count[0] == max_rng:
            cutoff_time = dtm

    # Primeira chegada em t=2.0 (não consome aleatório)
    heapq.heappush(fel, Event(2.0, 'arrival'))

    while fel:
        ev = heapq.heappop(fel)
        if cutoff_time is not None and ev.time > cutoff_time + 1e-12:
            break  # não processa eventos além do cutoff

        # avança o tempo e acumula tempo de estado
        acum(ev.time)
        t = ev.time

        if ev.kind == 'arrival':
            # Chegada com sistema cheio => perda
            if system_size >= K:
                lost += 1
                sched_arrival(t)
                continue

            # Aceita a chegada
            system_size += 1

            # Tenta iniciar serviço se houver servidor livre
            started = False
            for sid in range(c):
                if not busy[sid]:
                    busy[sid] = True
                    sched_departure(t, sid)
                    started = True
                    break
            if not started:
                waiting += 1

            # Agenda próxima chegada
            sched_arrival(t)

        else:  # 'departure'
            # Finaliza serviço no servidor ev.server_id
            if not busy[ev.server_id]:
                continue  # proteção
            system_size -= 1
            if waiting > 0:
                waiting -= 1
                # mesmo servidor pega próximo cliente
                sched_departure(t, ev.server_id)
            else:
                busy[ev.server_id] = False

    final_time = cutoff_time if cutoff_time is not None else t
    acum(final_time)  # garante acumular até o cutoff

    total = sum(state_time) if sum(state_time) > 0 else 1.0
    probs = [stt / total for stt in state_time]

    return {
        "c": c,
        "K": K,
        "global_time": final_time,
        "lost": lost,
        "rng_used": rng_count[0],
        "state_time": state_time,
        "state_prob": probs,
    }

# ---- Execução mínima pedida no enunciado ----
if __name__ == "__main__":
    res1 = simulate(c=1, K=5, ia=(2,5), st=(3,5), max_rng=100_000)  # G/G/1/5
    res2 = simulate(c=2, K=5, ia=(2,5), st=(3,5), max_rng=100_000)  # G/G/2/5

    def show(res, title):
        print(f"\n=== {title} ===")
        print(f"Servidores (c): {res['c']} | Capacidade (K): {res['K']}")
        print(f"Tempo global: {res['global_time']:.6f}")
        print(f"Perdas: {res['lost']}")
        print(f"Aleatórios usados: {res['rng_used']}")
        print("Estado  TempoAcum    Prob")
        for n, (tt, pp) in enumerate(zip(res["state_time"], res["state_prob"])):
            print(f"{n:>2}    {tt:>10.6f}  {pp:>8.6f}")

    show(res1, "G/G/1/5")
    show(res2, "G/G/2/5")