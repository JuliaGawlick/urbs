import os
import pyomo.environ
from pyomo.opt.base import SolverFactory
from datetime import datetime, date
from .model import create_model
from .report import *
from .plot import *
from .input import *
from .validation import *
from .saveload import *


def prepare_result_directory(result_name):
    """ create a time stamped directory within the result folder.

    Args:
        result_name: user specified result name

    Returns:
        a subfolder in the result folder 
    
    """
    # timestamp for result directory
    now = datetime.now().strftime('%Y%m%dT%H%M')

    # create result directory if not existent
    result_dir = os.path.join('result', '{}-{}'.format(result_name, now))
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    return result_dir


def setup_solver(optim, logfile='solver.log'):
    """ """
    if optim.name == 'gurobi':
        # reference with list of option names
        # http://www.gurobi.com/documentation/5.6/reference-manual/parameters
        optim.set_options("logfile={}".format(logfile))
        # optim.set_options("timelimit=7200")  # seconds
        # optim.set_options("mipgap=5e-4")  # default = 1e-4
    elif optim.name == 'glpk':
        # reference with list of options
        # execute 'glpsol --help'
        optim.set_options("log={}".format(logfile))
        # optim.set_options("tmlim=7200")  # seconds
        # optim.set_options("mipgap=.0005")
    elif optim.name == 'cplex':
        optim.set_options("log={}".format(logfile))
    else:
        print("Warning from setup_solver: no options set for solver "
              "'{}'!".format(optim.name))
    return optim


def run_scenario(input_files, Solver, timesteps, scenario, result_dir, dt,
                 objective, plot_tuples=None,  plot_sites_name=None,
                 plot_periods=None, report_tuples=None,
                 report_sites_name=None):
    """ run an urbs model for given input, time steps and scenario

    Args:
        - input_files: filenames of input Excel spreadsheets
        - Solver: the user specified solver
        - timesteps: a list of timesteps, e.g. range(0,8761)
        - scenario: a scenario function that modifies the input data dict
        - result_dir: directory name for result spreadsheet and plots
        - dt: length of each time step (unit: hours)
        - objective: objective function chosen (either "cost" or "CO2")
        - plot_tuples: (optional) list of plot tuples (c.f. urbs.result_figures)
        - plot_sites_name: (optional) dict of names for sites in plot_tuples
        - plot_periods: (optional) dict of plot periods
          (c.f. urbs.result_figures)
        - report_tuples: (optional) list of (sit, com) tuples
          (c.f. urbs.report)
        - report_sites_name: (optional) dict of names for sites in
          report_tuples

    Returns:
        the urbs model instance
    """

    # sets a modeled year for non-intertemporal problems
    # (necessary for consitency)
    year = date.today().year

    # scenario name, read and modify data for scenario
    sce = scenario.__name__
    data = read_input(input_files, year)
    data = scenario(data)
    validate_input(data)
    validate_dc_objective(data, objective)

    # create model
    prob = create_model(data, dt, timesteps, objective)
    # prob_filename = os.path.join(result_dir, 'model.lp')
    # prob.write(prob_filename, io_options={'symbolic_solver_labels':True})

    # refresh time stamp string and create filename for logfile
    log_filename = os.path.join(result_dir, '{}.log').format(sce)

    # solve model and read results
    optim = SolverFactory(Solver)  # cplex, glpk, gurobi, ...
    optim = setup_solver(optim, logfile=log_filename)
    result = optim.solve(prob, tee=True)
    assert str(result.solver.termination_condition) == 'optimal'

    # save problem solution (and input data) to HDF5 file
    save(prob, os.path.join(result_dir, '{}.h5'.format(sce)))

    # write report to spreadsheet
    report(
        prob,
        os.path.join(result_dir, '{}.xlsx').format(sce),
        report_tuples=report_tuples,
        report_sites_name=report_sites_name)

    # result plots
    result_figures(
        prob,
        os.path.join(result_dir, '{}'.format(sce)),
        timesteps,
        plot_title_prefix=sce.replace('_', ' '),
        plot_tuples=plot_tuples,
        plot_sites_name=plot_sites_name,
        periods=plot_periods,
        figure_size=(24, 9))

    return prob


##comments:
## input_files can be a list but then additional mode for urbs = myopic necessary. Otherwise intertemporal mode is initialized which also affects the read in of data (no inst-cap anymore)
##report in excel and plotting is deleted for now
def run_scenario_myopic(input_files, Solver, timesteps, scenario, result_dir, dt,
                 objective, plot_tuples=None,  plot_sites_name=None,
                 plot_periods=None, report_tuples=None,
                 report_sites_name=None):
    """ run an urbs model for given input, time steps and scenario

    Args:
        - input_files: filenames of input Excel spreadsheets
        - Solver: the user specified solver
        - timesteps: a list of timesteps, e.g. range(0,8761)
        - scenario: a scenario function that modifies the input data dict
        - result_dir: directory name for result spreadsheet and plots
        - dt: length of each time step (unit: hours)
        - objective: objective function chosen (either "cost" or "CO2")
        - plot_tuples: (optional) list of plot tuples (c.f. urbs.result_figures)
        - plot_sites_name: (optional) dict of names for sites in plot_tuples
        - plot_periods: (optional) dict of plot periods
          (c.f. urbs.result_figures)
        - report_tuples: (optional) list of (sit, com) tuples
          (c.f. urbs.report)
        - report_sites_name: (optional) dict of names for sites in
          report_tuples

    Returns:
        the urbs model instance
    """

    # sets a modeled year for non-intertemporal problems
    # (necessary for consitency)
    year = date.today().year

    # scenario name, read and modify data for scenario
    sce = scenario.__name__
    glob_input = os.path.join(input_files, '*.xlsx')
    input_files = sorted(glob.glob(glob_input))
    for i in range(0,len(input_files)):

        data = read_input(input_files[i], year)
        data = scenario(data)
        validate_input(data)
        #validate_dc_objective(data, objective)

        if i == 0:
            pass
        else: data=myopic_update(data,prob)

        # create model
        prob = create_model(data, dt, timesteps, objective)
        # prob_filename = os.path.join(result_dir, 'model.lp')
        # prob.write(prob_filename, io_options={'symbolic_solver_labels':True})

        # refresh time stamp string and create filename for logfile
        log_filename = os.path.join(result_dir, '{}.log').format(sce)

        # solve model and read results
        optim = SolverFactory(Solver)  # cplex, glpk, gurobi, ...
        optim = setup_solver(optim, logfile=log_filename)
        result = optim.solve(prob, tee=True)
        assert str(result.solver.termination_condition) == 'optimal'

        # save problem solution (and input data) to HDF5 file
        save(prob, os.path.join(result_dir, '{}'+str(data['global_prop'].index.levels[0][0])+'.h5').format(sce))

        report(
            prob,
            os.path.join(result_dir, '{}'+str(data['global_prop'].index.levels[0][0])+'.xlsx').format(sce),
            report_tuples=report_tuples,
            report_sites_name=report_sites_name)


    return prob


def myopic_update(data,prob):

    # set inst cap for processes to results from previous stf
    pro = data['process']
    indexlist = pro.index.to_list()
    previous_stf = prob._result["cap_pro"].index.levels[0].to_list()
    for indextuple in indexlist:
        indexstf = indextuple[0]
        indexsit = indextuple[1]
        indexprocess = indextuple[2]
        #import pdb;pdb.set_trace()
        pro.loc[(indextuple),'inst-cap'] = prob._result["cap_pro"].loc[(previous_stf,indexsit,indexprocess)].iloc[0]
        #pro.loc[(indextuple),'lifetime'] = indexstf - previous_stf

    # set inst cap for storages to results from previous stf
    sto = data['storage']
    indexlist = sto.index.to_list()
    previous_stf = prob._result["cap_sto_c"].index.levels[0].to_list()
    for indextuple in indexlist:
        indexsit = indextuple[1]
        indexstorage = indextuple[2]

        sto.loc[(indextuple),'inst-cap-c'] = prob._result["cap_sto_c"].loc[(previous_stf,indexsit,indexstorage)].iloc[0]
        sto.loc[(indextuple), 'inst-cap-p'] = prob._result["cap_sto_p"].loc[(previous_stf, indexsit, indexstorage)].iloc[0]


    # set inst cap for transmission to results from previous stf
    tra = data['transmission']
    indexlist = tra.index.to_list()
    previous_stf = prob._result["cap_tra"].index.levels[0].to_list()

    for indextuple in indexlist:
        indexsitin = indextuple[1]
        indexsitout = indextuple[2]
        indextransmission = indextuple[3]

        tra.loc[(indextuple),'inst-cap'] = prob._result["cap_tra"].loc[(previous_stf,indexsitin,indexsitout,indextransmission)].iloc[0]



    return data


