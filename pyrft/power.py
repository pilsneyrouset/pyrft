"""
Functions to simulate and test when the null is not true everywhere
"""
import pyrft as pr
import numpy as np
import sys
sys.path.insert(0, 'C:\\Users\\12SDa\\davenpor\\davenpor\\Other_Toolboxes\\sanssouci.python')
import sanssouci as sa
from sanssouci.post_hoc_bounds import _compute_hommel_value
from sklearn.utils import check_random_state
from scipy.stats import norm

def random_signal_locations(lat_data, categ, C, pi0, scale = 1, rng = check_random_state(101)):
    """ A function which generates random data with randomly located non-zero 
    contrasts

    Parameters
    -----------------
    lat_data: an object of class field
        giving the data with which to add the signal to
    categ: numpy.nd array,
        of shape (nsubj, 1) each entry identifying a category 
    C: numpy.nd array
        of shape (ncontrasts, nparams)
        contrast matrix
    pi0: a float 
        between 0 and 1 giving the proportion of the hypotheses that are truly null
    scale: float,
        giving the amount (scale of) the signal which to add. Default is 1.
    rng: random number generator

    Returns
    -----------------
    lat_data: an object of class field,
        which consists of the noise plus the added signal

    Examples
    -----------------
    dim = (25,25); nsubj = 300; fwhm = 4
    lat_data = pr.statnoise(dim, nsubj, fwhm)
    C = np.array([[1,-1,0],[0,1,-1]])
    n_groups = C.shape[1]
    rng = check_random_state(101)
    categ = rng.choice(n_groups, nsubj, replace = True)
    f = random_signal_locations(lat_data, categ, C, 0.5)
    subjects_with_1s = np.where(categ==1)[0]
    plt.imshow(np.mean(f.field[...,subjects_with_1s],2))
    subjects_with_2s = np.where(categ==2)[0]
    plt.imshow(np.mean(f.field[...,subjects_with_2s],2))
    """
    # Compute important constants
    dim = lat_data.masksize
    n_contrasts = C.shape[0]
    
    # Compute derived constants
    nvox = np.prod(dim) # compute the number of voxels
    m = nvox*n_contrasts # obtain the number of voxel-contrasts
    ntrue = int(np.round(pi0 * m)) # calculate the closest integer to make the 
                                #proportion of true null hypotheses equal to pi0
    
    # Initialize the true signal vector
    signal_entries = np.zeros(m)
    signal_entries[ntrue:] = 1
    
    if isinstance(dim, int):
        signal = pr.make_field(np.zeros((dim,n_contrasts)))
    else:
        signal = pr.make_field(np.zeros(dim + (n_contrasts,)))
            
    # Generate the signal by random shuffling the original signal
    # (if the proportion of signal is non-zero)
    if pi0 < 1:
        shuffle_idx = rng.choice(m, m, replace = False)
        shuffled_signal = signal_entries[shuffle_idx]
        spatial_signal2add = np.zeros(dim)
        for j in np.arange(n_contrasts):
            contrast_signal = shuffled_signal[j*nvox:(j+1)*nvox]
            signal.field[..., j] = contrast_signal.reshape(dim)
            spatial_signal2add += signal.field[..., j]
            subjects_with_this_contrast = np.where(categ==(j+1))[0]

            # Add the signal to the field
            for k in np.arange(len(subjects_with_this_contrast)):
                lat_data.field[..., subjects_with_this_contrast[k]] += scale*spatial_signal2add
    
    return lat_data, signal

def bootpower(dim, nsubj, contrast_matrix, fwhm = 0, design = 0, n_bootstraps = 100, niters = 1000, pi0 = 1, simtype = 1, alpha = 0.1, template = 'linear', replace = True, ):
    """ bootpower generates non-null simulations and calculates the proportion
    of the true alternatives that are identified

    Parameters
    -----------------
    dim:
    nsubj:
    contrast_matrix:
    fwhm:
    design:
    n_bootstraps:
    niters:
    pi0:
    alpha:
    template:
    replace:
    simtype:
        
    Returns
    -----------------
    
    Examples
    -----------------
    % Calculate the power using the bootstrap method
    dim = (25,25); nsubj = 10; C = np.array([[1,-1,0],[0,1,-1]]);
    power = pr.bootpower(dim, nsubj, C, 4, 0, 100, 1000, 0.8)
    
    % Calculate the power using ARI
    dim = (25,25); nsubj = 10; C = np.array([[1,-1,0],[0,1,-1]]);
    power = pr.bootpower(dim, nsubj, C, 4, 0, 100, 1000, 0.8, -1)
    """
    # Obtain ordered randomness
    rng = check_random_state(101)
    
    # If the proportion of null hypotheses has been set to 1, stop and return nothing
    if pi0 == 1:
        print('Power equals zero if pi0 = 1')
        return

    # If the design input is a matrix take this to be the design matrix
    # of the covariates (otherwise a random design is generated - see below)
    if not isinstance(design, int):
        design_2use = design

    # Obtain the inverse template function (allowing for direct input as well!)
    if isinstance(template, str):
        t_func, t_inv = pr.t_ref(template)
    else:
        # Allow the inverse function to be an input
        t_inv = template

    if len(contrast_matrix.shape) == 1:
        n_contrasts = 1
        n_groups = 1
    else:
        n_contrasts = contrast_matrix.shape[0]
        n_groups = contrast_matrix.shape[1]
        
    # Initialize the true signal vector
    nvox = np.prod(dim)
    m = nvox*n_contrasts
    ntrue = int(np.round(pi0 * m))
    nfalse = m - ntrue
    
    # Initialize the vector to store the power
    power = np.zeros(5)
    
     # Calculate TDP ratio for each bootstrap iteration
    for i in np.arange(niters):
        # Keep track of the progress.
        pr.modul(i,1)

        # Generate the data (i.e. generate stationary random fields)
        lat_data = pr.statnoise(dim,nsubj,fwhm)

        if isinstance(design, int):
            # Generate a random category vector with choices given by the design matrix
            categ = rng.choice(n_groups, nsubj, replace = True)

            # Ensure that all categories are present in the category vector
            while len(np.unique(categ)) < n_groups:
                print('had rep error')
                categ = rng.choice(n_groups, nsubj, replace = True)

            # Generate the corresponding design matrix
            design_2use = pr.group_design(categ)
        
        # Add random signal to the data
        lat_data, signal = random_signal_locations(lat_data, categ, contrast_matrix, pi0, rng = rng)
                    
        # Convert the signal to boolean
        signal.field = signal.field == 0

        if simtype > -1:
            # Run the bootstrap algorithm
            if simtype == 1:
                # Implement the bootstrap algorithm on the generated data
                minp_perm, orig_pvalues, pivotal_stats, _ = pr.boot_contrasts(lat_data, design_2use, contrast_matrix, n_bootstraps, t_inv, replace)
            else:
                pr.perm_contrasts(lat_data, design_2use, contrast_matrix, n_bootstraps, t_inv)
                
            # Calculate the lambda alpha level quantile for JER control
            lambda_quant = np.quantile(pivotal_stats, alpha)
        
        if pi0 < 1:
            # Calulate the template family
            if simtype > -1:
                tfamilyeval = t_func(lambda_quant, m, m)
            else:
                # Calculate the p-values
                orig_tstats, _ = pr.constrast_tstats_noerrorchecking(lat_data, design_2use, contrast_matrix)
                n_params = design_2use.shape[1]
                orig_pvalues = pr.tstat2pval(orig_tstats, nsubj - n_params)
                
                if simtype == -1:
                    # Run ARI
                    # Calculate the zstats from the pvalues (need for input into _compute_hommel_value)
                    zstats = norm.ppf(np.ravel(orig_pvalues.field))
                    hommel = _compute_hommel_value(zstats, alpha)
                    tfamilyeval = sa.linear_template(alpha, hommel, hommel)
                elif simtype == -2:
                    # Run Simes
                    tfamilyeval = sa.linear_template(alpha, m, m)
                
            # Update the power calculation
            power = pr.BNRpowercalculation_update(power, tfamilyeval, orig_pvalues, signal, m, nfalse);
            
    # Calculate the power (when the data is non-null) by averaging over all simulations
    if pi0 < 1:
        power = power/niters

    return power

def BNRpowercalculation_update(power, thr, orig_pvalues, signal, m, nfalse):
    # a) R = N_m
    all_pvalues = np.ravel(orig_pvalues.field)
    max_FP_bound = sa.max_fp(np.sort(all_pvalues), thr)
    min_TP_bound = m - max_FP_bound
    power[0] += min_TP_bound/nfalse
    
    # b) R_b denotes the rejection set that considers the voxel-contrasts
    # whose p-value is less than 0.05
    
    # Calculate the rejection set
    R_b = orig_pvalues.field < 0.05
    
    # Calculate the number of rejections of non-null hypotheses
    number_of_non_nulls = np.sum(R_b*signal.field > 0)
    
    # If there is at least 1 non-null rejection, record the TDP bound
    if number_of_non_nulls > 0.5:
        pval_set = np.sort(np.ravel(orig_pvalues.field[R_b]))
        npcount = len(pval_set)
        max_FP_bound_b = sa.max_fp(pval_set, thr)
        min_TP_bound_b = npcount - max_FP_bound_b
        power[1] += min_TP_bound_b/npcount
        
    # b) R_b denotes the rejection set that considers the voxel-contrasts
    # whose p-value is less than 0.05
    
    # Calculate the rejection set
    R_b = orig_pvalues.field < 0.1
    
    # Calculate the number of rejection of non-null hypotheses
    number_of_non_nulls = np.sum(R_b*signal.field > 0)
    
    # If there is at least 1 non-null rejection, record the TDP bound
    if number_of_non_nulls > 0.5:
        pval_set = np.sort(np.ravel(orig_pvalues.field[R_b]))
        npcount = len(pval_set)
        max_FP_bound_b = sa.max_fp(pval_set, thr)
        min_TP_bound_b = npcount - max_FP_bound_b
        power[2] += min_TP_bound_b/npcount
        
    # c) BH rejection set 0.05
    R_c, _, _ = pr.fdr_bh( all_pvalues, alpha = 0.05)
    number_of_non_nulls = np.sum(R_c*np.ravel(signal.field) > 0)
    
    # If there is at least 1 non-null rejection, record the TDP bound
    if number_of_non_nulls > 0.5:
        R_c_pvalues = all_pvalues[R_c]
        npcount = len(R_c_pvalues)
        max_FP_bound_c = sa.max_fp(np.sort(R_c_pvalues), thr)
        min_TP_bound_c = npcount - max_FP_bound_c
        power[3] += min_TP_bound_c/npcount
        
    # c) BH rejection set 0.1
    R_c, _, _ = pr.fdr_bh( all_pvalues, alpha = 0.1)
    number_of_non_nulls = np.sum(R_c*np.ravel(signal.field) > 0)
    
    # If there is at least 1 non-null rejection, record the TDP bound
    if number_of_non_nulls > 0.5:
        R_c_pvalues = all_pvalues[R_c]
        npcount = len(R_c_pvalues)
        max_FP_bound_c = sa.max_fp(np.sort(R_c_pvalues), thr)
        min_TP_bound_c = npcount - max_FP_bound_c
        power[4] += min_TP_bound_c/npcount
        
    return power
