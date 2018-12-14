"""
This script was generated by the train.py script in this repository:
https://github.com/ecohealthalliance/geoname-annotator-training
"""
import numpy as np
from numpy import array, int32


HIGH_CONFIDENCE_THRESHOLD = 0.5
GEONAME_SCORE_THRESHOLD = 0.11
base_classifier =\
{
    'multi_class': 'warn',
    'verbose': 0,
    'C': 1.0,
    'dual': False,
    'warm_start': False,
    'intercept_scaling': 1,
    'max_iter': 100,
    'random_state': None,
    'n_jobs': None,
    'intercept_': array([-9.28343916]),
    'fit_intercept': True,
    'classes_': array([False,  True]),
    'n_iter_': array([46], dtype=int32),
    'class_weight': None,
    'coef_': array([[
        # log_population
        0.34262552094358173,
        # name_count
        0.34084684504565244,
        # names_used
        1.8760592161283256,
        # multiple_spans
        0.42667954045606565,
        # span_length
        0.13772152678130364,
        # cannonical_name_used
        2.940636263595021,
        # loc_NE_portion
        1.1234447868729431,
        # noun_portion
        1.0109412123401722,
        # num_tokens
        -0.058910757761115005,
        # ambiguity
        -1.0635941967766,
        # PPL_feature_code
        0.0,
        # ADM_feature_code
        -0.567473372564782,
        # CONT_feature_code
        -1.882831379443239,
        # other_feature_code
        1.0499054778077563,
        # first_order
        0.8440389864769996,
        # close_locations
        0.0,
        # very_close_locations
        0.0,
        # base_score_margin
        0.0,
        # contained_locations
        0.0,
        # containing_locations
        0.0,
    ]]),
    'tol': 0.0001,
    'penalty': 'l1',
    'solver': 'warn',
}

contextual_classifier =\
{
    'multi_class': 'warn',
    'verbose': 0,
    'C': 1.0,
    'dual': False,
    'warm_start': False,
    'intercept_scaling': 1,
    'max_iter': 100,
    'random_state': None,
    'n_jobs': None,
    'intercept_': array([-8.840484]),
    'fit_intercept': True,
    'classes_': array([False,  True]),
    'n_iter_': array([48], dtype=int32),
    'class_weight': None,
    'coef_': array([[
        # log_population
        0.2939483940730553,
        # name_count
        0.2580094721076477,
        # names_used
        0.5029191676114552,
        # multiple_spans
        0.09977916646861679,
        # span_length
        0.11418661641029156,
        # cannonical_name_used
        2.155326844199699,
        # loc_NE_portion
        0.8623937844915512,
        # noun_portion
        0.9604347978115251,
        # num_tokens
        0.1937812183183358,
        # ambiguity
        -0.7964553990195704,
        # PPL_feature_code
        0.0,
        # ADM_feature_code
        -0.7748943387772271,
        # CONT_feature_code
        -1.9281915222896282,
        # other_feature_code
        0.7077227108933093,
        # first_order
        0.841264045454143,
        # close_locations
        0.22854094991329404,
        # very_close_locations
        0.5533668273177214,
        # base_score_margin
        2.3501013895182505,
        # contained_locations
        -0.12912768061046315,
        # containing_locations
        -0.07385016929934174,
    ]]),
    'tol': 0.0001,
    'penalty': 'l1',
    'solver': 'warn',
}

# Logistic regression code from scipy
def predict_proba(X, classifier):
    """Probability estimation for OvR logistic regression.
    Positive class probabilities are computed as
    1. / (1. + np.exp(-classifier.decision_function(X)));
    multiclass is handled by normalizing that over all classes.
    """
    prob = np.dot(X, classifier['coef_'].T) + classifier['intercept_']
    prob = prob.ravel() if prob.shape[1] == 1 else prob
    prob *= -1
    np.exp(prob, prob)
    prob += 1
    np.reciprocal(prob, prob)
    if prob.ndim == 1:
        return np.vstack([1 - prob, prob]).T
    else:
        # OvR normalization, like LibLinear's predict_probability
        prob /= prob.sum(axis=1).reshape((prob.shape[0], -1))
        return prob


def predict_proba_base(X):
    return predict_proba(X, base_classifier)


def predict_proba_contextual(X):
    return predict_proba(X, contextual_classifier)
