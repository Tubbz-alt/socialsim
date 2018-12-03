from scipy.stats import entropy, ks_2samp, spearmanr, pearsonr
from sklearn.metrics import r2_score
from scipy.spatial.distance import euclidean
import statsmodels.api as sm
import fastdtw as fdtw
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
from scipy.stats import iqr


def check_data_types(ground_truth, simulation):
    """
    Convert ground truth and simulation measurements to arrays if they are DataFrames

    Inputs: Ground truth and simulation data as output by the meeasurement code
    Outputs: Ground truth and simulation data in array format
    """

    if isinstance(ground_truth, pd.DataFrame):
        ground_truth = ground_truth['value']
    if isinstance(simulation, pd.DataFrame):
        simulation = simulation['value']

    ground_truth = np.array(ground_truth)
    simulation = np.array(simulation)

    return ground_truth, simulation


def get_hist_bins(ground_truth, simulation, method='auto'):
    """
    Calculate bins for combined ground truth and simulation data sets to
    use consistent bins for distributional comparisons

    Inputs:
    ground_truth: Ground truth measurement
    simulation: Simulation measurement
    method: Method of bin calculation corresponding the np.histogram bin argument


    Outputs:
    Bin edges

    """

    all_data = np.concatenate([ground_truth, simulation])

    _, bins = np.histogram(all_data, bins=method)

    return (bins)


def absolute_difference(ground_truth, simulation):
    """
    Absolute difference between ground truth simulation measurement
    Meant for scalar valued measurements
    """

    try:
        return np.abs(float(simulation) - float(ground_truth))
    except TypeError:
        print('Input should be two scalar, numerics')
        return None


def absolute_percentage_error(ground_truth, simulation):
    """
    Absolute percentage error between ground truth simulation measurement
    Meant for scalar valued measurements
    """

    try:
        if ground_truth==0:
            return np.inf
        return (np.abs(float(simulation) - float(ground_truth)))/float(ground_truth)*100.
    except TypeError:
        print('Input should be two scalar, numerics')
        return None


def kl_divergence(ground_truth, simulation, discrete=False):
    """
    KL Divergence between the ground truth and simulation data
    Meant for distributional measurements

    Inputs:
    ground_truth: Ground truth measurement
    simulation: Simulation measurement
    discrete: Whether the distribution is over discrete values (e.g. days of the week) (True) or numeric values (False)

    """

    if simulation is None:
        return None

    # if data is numeric, compute histogram
    if not discrete:

        ground_truth, simulation = check_data_types(ground_truth, simulation)

        bins = get_hist_bins(ground_truth, simulation,method='doane')

        ground_truth = np.histogram(ground_truth, bins=bins)[0]
        simulation = np.histogram(simulation, bins=bins)[0]

    else:

        df = ground_truth.merge(simulation,
                                on=[c for c in ground_truth.columns if c != 'value'],
                                suffixes=('_gt', '_sim'),
                                how='outer').fillna(0)

        ground_truth = df['value_gt'].values.astype(float)
        simulation = df['value_sim'].values.astype(float)
        ground_truth = ground_truth / ground_truth.sum()
        simulation = simulation / simulation.sum()

    if len(ground_truth) == len(simulation):
        return entropy(ground_truth, simulation)
    else:
        print('Two distributions must have same length')
        return None


def kl_divergence_smoothed(ground_truth, simulation, alpha=0.01, discrete=False):
    """
    Smoothed version of the KL divergence which smooths the simulation output to prevent
    infinities in the KL divergence output

    Additional input:
    alpha - smoothing parameter
    """

    # if data is numeric, compute histogram
    if not discrete:

        ground_truth, simulation = check_data_types(ground_truth, simulation)

        bins = get_hist_bins(ground_truth, simulation)

        ground_truth = np.histogram(ground_truth, bins=bins)[0]
        simulation = np.histogram(simulation, bins=bins)[0]
        smoothed_simulation = (1 - alpha) * simulation + alpha * (np.ones(simulation.shape))

    else:

        df = ground_truth.merge(simulation,
                                on=[c for c in ground_truth.columns if c != 'value'],
                                suffixes=('_gt', '_sim'),
                                how='outer').fillna(0)

        ground_truth = df['value_gt'].values.astype(float)
        simulation = df['value_sim'].values.astype(float)
        ground_truth = ground_truth / ground_truth.sum()
        simulation = simulation / simulation.sum()

    if len(ground_truth) == len(simulation):
        return entropy(ground_truth, smoothed_simulation)
    else:
        print('Two distributions must have same length')
        return None


def dtw(ground_truth, simulation):
    """
    Dynamic Time Warping implemenation
    """


    df = join_dfs(ground_truth,simulation,join='outer',fill_value=0.0)

    try:
        ground_truth = df['value_gt'].values
        simulation = df['value_sim'].values
    except:
        ground_truth = np.array(ground_truth)
        simulation = np.array(simulation)


    if len(simulation) > 0:
        dist = fdtw.dtw(ground_truth.tolist(), simulation, dist=euclidean)[0]
    else:
        dist = None

    return dist


def fast_dtw(ground_truth, simulation):
    """
    Fast Dynamic Time Warping implemenation
    """

    try:
        ground_truth = ground_truth['value'].values
        simulation = simulation['value'].values
    except:
        ground_truth = np.array(ground_truth)
        simulation = np.array(simulation)


    dist = fdtw.fastdtw(ground_truth, simulation, dist=euclidean)[0]
    return dist


def js_divergence(ground_truth, simulation, discrete=False, base=2.0):
    """
    Jensen-Shannon Divergence implemenation
    A symmetric variant on KL Divergence which also avoids infinite outputs

    Inputs:
    ground_truth - ground truth measurement
    simulation - simulation measurement
    base - the logarithmic base to use
    """


    if simulation is None or len(simulation) == 0 or ground_truth is None or len(ground_truth) == 0:
        return None

    if not discrete:


        ground_truth, simulation = check_data_types(ground_truth, simulation)

        try:
            ground_truth = ground_truth[np.isfinite(ground_truth)]
            simulation = simulation[np.isfinite(simulation)]
        except TypeError:
            return None

        bins = get_hist_bins(ground_truth, simulation,method='doane')

        ground_truth = np.histogram(ground_truth, bins=bins)[0].astype(float)
        simulation = np.histogram(simulation, bins=bins)[0].astype(float)

    else:

        try:
            ground_truth = ground_truth[np.isfinite(ground_truth.value)]
            simulation = simulation[np.isfinite(simulation.value)]
        except TypeError:
            return None

        df = ground_truth.merge(simulation,
                                on=[c for c in ground_truth.columns if c != 'value'],
                                suffixes=('_gt', '_sim'),
                                how='outer').fillna(0)

        ground_truth = df['value_gt'].values.astype(float)
        simulation = df['value_sim'].values.astype(float)
    
        
    ground_truth = ground_truth / ground_truth.sum()
    simulation = simulation / simulation.sum()


    if len(ground_truth) == len(simulation):
        m = 1. / 2 * (ground_truth + simulation)
        return entropy(ground_truth, m, base=base) / 2. + entropy(simulation, m, base=base) / 2.
    else:
        print('Two distributions must have same length')
        return None


def rbo_for_te(ground_truth,simulation,idx,wt,ct):

    ground_truth = ground_truth[idx]
    
    if len(simulation) == 0:
        return 0.0

    simulation = simulation[idx]
    
    metric = 0.0
    count = 0

    for grp in ground_truth.keys():


        ent_gt = ['-'.join(list(tups[0])) if len(tups[0]) == 2 else tups[0] for tups in ground_truth[grp]]
        if (len(ent_gt) < ct):
            continue

        ent_sm = []
        if (grp in simulation):
            count += 1
            ent_sm = ['-'.join(list(tups[0])) if len(tups[0]) == 2 else tups[0] for tups in simulation[grp]]
            metric += rbo_score(ent_gt,ent_sm,wt)

    if (count > 0):
        metric = metric/float(count)

    return metric


def rbo_score(ground_truth, simulation, p=0.95):
    """
    Rank biased overlap (RBO) implementation
    http://codalism.com/research/papers/wmz10_tois.pdf
    A ranked list comparison metric which allows non-overlapping lists

    Inputs:
    ground_truth - ground truth data
    simulation - simulation data
    p - RBO parameter ranging from 0 to 1 that determines how much to overweight the the upper portion of the list
        p = 0 means only the first element is considered
        p = 1 means all ranks are weighted equally
    """


    if simulation is None:
        return None

    #try:
    #    ground_truth = ground_truth.index.tolist()
    #    simulation = simulation.index.tolist()
    #except:
    #    ''

    if len(ground_truth.columns) == 2:

        entity = [c for c in ground_truth.columns if c != 'value'][0]

        ground_truth = ground_truth[entity].tolist()
        simulation = simulation[entity].tolist()
    else:
        ground_truth = ground_truth.index.tolist()
        simulation = simulation.index.tolist()

    sl, ll = sorted([(len(ground_truth), ground_truth), (len(simulation), simulation)])
    s, S = sl
    l, L = ll
    if s == 0: return 0


    # Calculate the overlaps at ranks 1 through s
    # (the shorter of the two lists)

    x_d = {}
    rbo_score = 0.0

    for i in range(1, s + 1):
        x = L[:i]
        y = S[:i]

        x_d[i] = len(set(x).intersection(set(y)))


    for i in range(1,s+1):
        rbo_score += (float(x_d[i])/float(i)) * pow(p, (i-1))


    rbo_score = rbo_score * (1 - p)

    return rbo_score

# Weight given to the top d ranks for a given p
def rbo_weight(d, p):
    sum1 = 0.0
    for i in range(1, d):
        sum1 += np.power(p, i) / float(i)

    wt = 1.0 - np.power(p, (d - 1)) + (((1 - p) / p) * d) * (np.log(1 / (1 - p)) - sum1)

    return wt


def rmse(ground_truth, simulation, join='inner', fill_value=0, relative=False):
    """
    Root mean squared error

    Inputs:
    ground_truth - ground truth measurement (data frame) with measurement in the "value" column
    simulation - simulation measurement (data frame) with measurement in the "value" column
    join - type of join to perform between ground truth and simulation
    fill_value - fill value for non-overlapping joins
    """

    if simulation is None or ground_truth is None:
        return None
    
    if type(ground_truth) is list:
	    ground_truth = np.nan_to_num(ground_truth)
	    simulation = np.nan_to_num(simulation)
	    return np.sqrt(((np.asarray(ground_truth) - np.asarray(simulation)) ** 2).mean())

    df = join_dfs(ground_truth,simulation,join=join,fill_value=fill_value)

    if len(df.index) > 0:
        if not relative:
            return np.sqrt(((df["value_sim"] - df["value_gt"]) ** 2).mean())
        else:
            return np.sqrt(((df["value_sim"] - df["value_gt"]) ** 2).mean()) / iqr(df['value_gt'].values)
    else:
        return None




def r2(ground_truth, simulation, join='inner', fill_value=0):
    """
    R-squared value between ground truth and simulation

    Inputs:
    ground_truth - ground truth measurement (data frame) with measurement in the "value" column
    simulation - simulation measurement (data frame) with measurement in the "value" column
    join - type of join to perform between ground truth and simulation
    fill_value - fill value for non-overlapping joins
    """

    if simulation is None or ground_truth is None:
        return None
    
    if len(simulation) == 0 or len(ground_truth) == 0:
        return None

    if type(ground_truth) is list:
    	ground_truth = np.nan_to_num(ground_truth)
    	simulation = np.nan_to_num(simulation)
        
        ground_truth = ground_truth[np.isfinite(ground_truth)]
        simulation = simulation[np.isfinite(simulation)]

    	return np.sqrt(((np.asarray(ground_truth) - np.asarray(simulation)) ** 2).mean())

    ground_truth = ground_truth[np.isfinite(ground_truth.value)]
    simulation = simulation[np.isfinite(simulation.value)] 

    df = join_dfs(ground_truth,simulation,join=join,fill_value=fill_value).fillna(0)

    if df.empty:
        return None
    else:
        return r2_score(df["value_gt"],df["value_sim"])


def pearson(ground_truth, simulation, join='inner', fill_value=0):
    """
    Pearson correlation coefficient between simulation and ground truth

    Inputs:
    ground_truth - ground truth measurement (data frame) with measurement in the "value" column
    simulation - simulation measurement (data frame) with measurement in the "value" column
    join - type of join to perform between ground truth and simulation
    fill_value - fill value for non-overlapping joins
    """

    df = join_dfs(ground_truth,simulation,join=join,fill_value=fill_value)

    if len(df.index) > 0:
        return pearsonr(df["value_gt"],df["value_sim"])
    else:
        return None


def ks_test(ground_truth, simulation):
    """
    Kolmogorov-Smirnov test
    Meant for measurements which are continous or numeric distributions
    """

    if simulation is None or len(simulation) == 0:
        return None

    ground_truth, simulation = check_data_types(ground_truth,simulation)

    try:
        return ks_2samp(ground_truth,simulation).statistic
    except:
        return None


def join_dfs(ground_truth,simulation,join='inner',fill_value=0):

    """
    Join the simulation and ground truth data frames

    Inputs:
    ground_truth - Ground truth measurement data frame with measurement in the "value" column
    simulation - Simulation measurement data frame with measurement in the "value" column
    join - Join method (inner, outer, left, right)
    fill_value - Value for filling NAs or method for filling in NAs (e.g. "ffill" for forward fill)
    """

    df = ground_truth.merge(simulation,
                            on = [c for c in ground_truth.columns if c != 'value'],
                            suffixes = ('_gt','_sim'),
                            how=join)
    df = df.sort_values([c for c in ground_truth.columns if c != 'value'])

    try:
        float(fill_value)
        df = df.fillna(fill_value)
    except ValueError:
        df = df.fillna(method=fill_value)

    return(df)



def get_metric_scores(ground_truth, simulation, measurement, metric, measurement_kwargs={}, metric_kwargs={}):
    """
    Function to combine measurement and metric computations

    :param ground_truth: pandas dataframe of ground truth
    :param simulation: pandas dataframe of simulation
    :param measurement: measurement function
    :param metric: metric function
    :return: metric computation for measurements calculated from gold and simulation

    """
    print("Calculating {} for {}".format(metric.__name__, measurement.__name__))
    measurement_on_gt = measurement(ground_truth, **measurement_kwargs)
    measurement_on_sim = measurement(simulation, **measurement_kwargs)
    return measurement_on_gt, measurement_on_sim, metric(measurement_on_gt, measurement_on_sim, **metric_kwargs)


def main():
    df = pd.read_csv('data/small_subset.csv')
    df = df.reset_index()

    df1 = df.sample(frac=0.6, replace=False)
    df2 = df.sample(frac=0.6, replace=False)

    print(df1)

    ground_truth = df1.copy()
    simulation = df2.copy()

    print("Absolute difference")
    gt, sim, metric = get_metric_scores(ground_truth, simulation, getGiniCoef, absolute_difference)
    print('Gini:', gt, sim, metric)

    ground_truth = df1.copy()
    simulation = df2.copy()

    print('KS test')
    gt, sim, metric = get_metric_scores(ground_truth, simulation, getUserPopularity, ks_test,
                                        measurement_kwargs={'k': 1000})
    print('User Popularity', metric)

    ground_truth = df1.copy()
    simulation = df2.copy()

    print('JS divergence')
    gt, sim, metric = get_metric_scores(ground_truth, simulation, getUserPopularity, js_divergence,
                                        measurement_kwargs={'k': 1000})
    print('User Popularity', metric)

    ground_truth = df1.copy()
    simulation = df2.copy()

    print("RMSE")
    gt, sim, metric = get_metric_scores(ground_truth, simulation, getUserPopularity, rmse,
                                        measurement_kwargs={'k': 1000}, metric_kwargs={'join': 'inner'})

    ground_truth = df1.copy()
    simulation = df2.copy()

    print("R2")
    gt, sim, metric = get_metric_scores(ground_truth, simulation, getUserPopularity, r2,
                                        measurement_kwargs={'k': 1000}, metric_kwargs={'join': 'inner'})
    print(metric)

    ground_truth = df1.copy()
    simulation = df2.copy()

    print("Pearson")
    gt, sim, metric = get_metric_scores(ground_truth, simulation, getUserPopularity, pearson,
                                        measurement_kwargs={'k': 1000}, metric_kwargs={'join': 'inner'})
    print(metric)

    ground_truth = df1.copy()
    simulation = df2.copy()

    # RBO test
    list1 = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    list2 = ['0', '1', '3', '2', '6', '5', '9', '7']

    print('RBO')
    print(rbo_score(list1, list2, p=0.9))

    gt, sim, metric = get_metric_scores(ground_truth, simulation, getUserPopularity, rbo_score,
                                        measurement_kwargs={'k': 1000}, metric_kwargs={'p': 0.9})
    print(metric)

    ground_truth = df1.copy()
    simulation = df2.copy()

    # DTW tests
    x = np.array([0, 1, 1, 2, 4, 2, 1, 3, 2, 0, 0, 0])
    y = np.array([0, 1, 1, 2, 3, 2, 1, 2, 0])
    z = np.array([0, 0, 0, 0, 1, 1, 2, 4, 2, 1, 3, 2, 0])

    print("Using Fast-DTW")
    distxy = fast_dtw(x, y);
    distxz = fast_dtw(x, z);
    distyz = fast_dtw(y, z)
    print("dist(x,y) = ", distxy, " dist(x,z) = ", distxz, " dist(y,z) = ", distyz)

    print("Using DTW")
    distxy = dtw(x, y);
    distxz = dtw(x, z);
    distyz = dtw(y, z)
    print("dist(x,y) = ", distxy, " dist(x,z) = ", distxz, " dist(y,z) = ", distyz)


if __name__ == "__main__":
    main()
