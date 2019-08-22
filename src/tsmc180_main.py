import argparse

from tech   import TSMC180              as tech     # Tecnologia que queremos usar
from paths  import inversor_chain_path  as path     # Path que estamos probando
from sims   import monte_carlo_sim      as mcs      # El código que hace la simulación Monte Carlo

def inverter_chain(num):
    return path.InversorChainPath(tech, num)

MCS_CHOICES =   {
                    'inverter_chain_5'  : (inverter_chain, 5),
                    #'FO4'               : (test2, None)
                }

def do_mcs(args):
    step_time   = args.step_time
    num_sims    = args.num_sims
    path        = args.path
    plot_result = args.plot_result

    put = MCS_CHOICES[path][0](MCS_CHOICES[path][1])
    mcs.do_monte_carlo_sim(tech, put, step_time, num_sims, plot_result)


# ====================
# Parseo de argumentos
# ====================

parser = argparse.ArgumentParser(description='Run tests / simulation using TSMC180 tech')
subparsers = parser.add_subparsers(title='Commands', metavar='CMD')

parserMCS = subparsers.add_parser('MCS', help='Monte Carlo Simulation')
parserMCS.add_argument('--step_time', metavar='TIME', type=float, default=1e-9,
                       help='Max time step for transient simulation (default: 1e-9)')
parserMCS.add_argument('--num_sims', type=int, default=10000,
                       help='Number of simulation to run (default: 10000)')
parserMCS.add_argument('-p', '--plot', dest='plot_result', action='store_true', default=False,
                       help='Plot the results of the transient sim of the best case')
parserMCS.add_argument('path', metavar='PATH', choices=MCS_CHOICES,
                       help='Path to simulate: (%(choices)s)')
parserMCS.set_defaults(func=do_mcs)

args = parser.parse_args()
args.func(args)
