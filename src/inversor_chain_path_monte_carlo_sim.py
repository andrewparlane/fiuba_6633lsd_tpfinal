import os
import sys

from tech   import TSMC180              as tech     # Tecnologia que queremos usar
from paths  import inversor_chain_path  as path     # Path que estamos probando
from sims   import monte_carlo_sim      as mcs      # El código que hace la simulación Monte Carlo

# ====================
# Parseo de argumentos
# ====================
if (len(sys.argv) != 2):
    print("Please provide step time between 1e-18 and 1e-9")
    exit()

step_time = float(sys.argv[1])
if (step_time < 1e-18 or step_time > 1e-9):
    print("Please provide step time between 1e-18 and 1e-9")
    exit()

NUM_INVERSORES = 5
put = path.InversorChainPath(tech, NUM_INVERSORES)

mcs.do_monte_carlo_sim(tech, put, step_time)
