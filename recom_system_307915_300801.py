# %% Import
import argparse
from os import close
import numpy as np
import pandas as pd
from tqdm import tqdm 
from sklearn.decomposition import NMF
from datetime import datetime as dt
from split_dataset import parse_arguments
from time import perf_counter as time

# %% Parse arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description = 'MKRW 2021 Projekt 1')
    parser.add_argument('--train', help = 'train file', default = 'data/ratings_train.csv')
    parser.add_argument('--test', help = 'test file', default = 'data/ratings_test.csv')
    parser.add_argument('--alg', help = '\'NMF (default)\' or \'SVD1\' or \'SVD2\' or \'SGD\'', default = 'NMF')
    parser.add_argument('--result_file', help = 'file where final RMSE will be saved', default = 'result.txt')
    args, unknown = parser.parse_known_args() # makes it possible to use inside interactive Python kernel
    return args

args = parse_arguments()
train = pd.read_csv(args.train, index_col = False)
test = pd.read_csv(args.test, index_col = False)

# %% Functions using ratings.csv data
def RMSE(Zp):
    ''' Root-mean-square error between matrix Zp and test matrix '''
    RMSE = 0
    for row in range(test.shape[0]):
        i = test.userId[row] - 1
        j = all_movies.index(test.movieId[row])
        k = test.rating[row]
        RMSE = RMSE + (Zp[i][j] - k)**2
    return np.sqrt(RMSE/test.shape[0])

def fill_matrix(Z):
    ''' Fills matrix Z with known entries from training data '''
    for row in tqdm(range(train.shape[0])):
        ''' Id userów są od 1 do 610 i jest ich 610 więc odejmujemy 1, a Id filmów
            jest dużo mniej niż ich max. więc zamiast id bierzemy jego numer w posortowanej liście '''
        i = train.userId[row] - 1
        j = all_movies.index(train.movieId[row])
        k = train.rating[row]
        Z[i][j] = k
    return

# %% Algorithms 
def approx_NMF(Z_, r = 10, **kwargs):
    ''' Nonnegative Matrix Factorization; Return approximated matrix and summary log string;
        Z_(nd.array) original matrix
        r (float) number of features '''
    model = NMF(n_components = r, init = 'random', random_state = 77)
    W = model.fit_transform(Z_)
    H = model.components_
    Z_approx = np.dot(W, H)
    RMSE1 = RMSE(Z_)
    RMSE2 = RMSE(Z_approx)
    percent = 100*(RMSE1 - RMSE2)/RMSE1
    log = f'NMF with r = {r} reduced RMSE by {percent:0.3f}.% from {RMSE1:0.3f} to {RMSE2:0.3f}'
    return Z_approx, log

def approx_SVD1(Z_, r = 5, **kwargs):
    ''' Singular Value Decomposition; Return approximated matrix and summary log string;
        Z_(nd.array) original matrix
        r (float) number of features'''
    U, S, VT = np.linalg.svd(Z_, full_matrices = False)
    S = np.diag(S)
    Z_approx = U[:,:r] @ S[0:r,:r] @ VT[:r,:]
    RMSE1 = RMSE(Z_)
    RMSE2 = RMSE(Z_approx)
    percent = 100*(RMSE1 - RMSE2)/RMSE1
    log = f'SVD1 with r = {r} reduced RMSE by {percent:0.3f}% from {RMSE1:0.3f} to {RMSE2:0.3f}'
    return Z_approx, log

def approx_SVD2(Z_, i = 10, r = 3, **kwargs):
    ''' SVD with iterations; Return approximated matrix and summary log string
        Z_(nd.array) original matrix
        r (float) number of features
        i (int) number of iterations'''
    Z_approx = np.copy(Z_)
    for j in tqdm(range(i)):
        Z_approx, log = approx_SVD1(Z_approx, r)
        if j != i-1: 
            Z_approx[entries] = filled_entries
    RMSE1 = RMSE(Z_)
    RMSE2 = RMSE(Z_approx)
    percent = 100*(RMSE1 - RMSE2)/RMSE1
    log = f'SVD2 with r = {r}, i = {i} reduced RMSE by {percent:0.3f}% from {RMSE1:0.3f} to {RMSE2:0.3f}'
    return Z_approx, log

def approx_SGD(n = 610, d = 9724, r = 5, l_rate = 0.01, bs = 225, **kwargs):
    ''' n,d: dimensions of train matrix '''
    x0 = np.full(r * (n + d), 0.825)
    vec = SGD(x0, batch_size = bs, l_rate = l_rate, n_epochs = 20)
    Z_approx = vec_to_mat(vec)
    RMSE2 = RMSE(Z_approx)
    log = f'SGD with r = {r}, alpha = {l_rate}, bs = {bs} result: {RMSE2:0.3f}'
    return Z_approx, log

def approx_NMF2_SVD2(Z_, r = 5, i = 5, **kwargs):
    Z_approx = np.copy(Z_)
    RMSE1 = RMSE(Z_)
    for j in tqdm(range(i)):
        Z_approx, log = approx_NMF(Z_approx, r)
        if j != i-1: 
            Z_approx[entries] = filled_entries
    Z_approx, log = approx_SVD2(Z_approx, i, r)
    RMSE2 = RMSE(Z_approx)
    percent = 100*(RMSE1 - RMSE2)/RMSE1
    log = f'NMF2_SVD2 with r = {r}, i = {i} reduced RMSE by {percent:0.3f}% from {RMSE1:0.3f} to {RMSE2:0.3f}'
    return Z_approx, log

def vec_to_mat(x, n = 610, r = 5, d = 9724):
    ''' Takes a vector of parameters x of the loss function f and converts it to matrix W @ H 
        n: ...
        r,d: shape of ... '''
    W = x[0 : n*r]
    W = W.reshape((n, r))
    H = x[n*r : r*(n+d)]
    H = H.reshape((r, d))
    return W @ H

def loss(x):
    ''' Loss function used by SGD (assumes that the matrix is approximated with product of W,H matrices) 
        x: vector of parameters (subsequent entries of W and H) '''
    WH = vec_to_mat(x)
    vec_wh = WH[entries]
    vec = (filled_entries - vec_wh)**2
    return np.sum(vec)

def der_loss(x, ks, h = 0.01):
    ''' Approximates the derivative of the loss function with respect to chosen parameters
        ks: order numbers of partials '''
    xp, xm = np.copy(x), np.copy(x)
    xp[ks] += h
    xm[ks] -= h
    return (loss(xp) - loss(xm))/(2*h)

def SGD(x0, der_loss = der_loss, batch_size = 255, l_rate = 0.01, n_epochs = 10):
    ''' Stochastic Gradient Descent; returns x that minimizes loss function '''
    N = len(x0)
    n_iter = N//batch_size
    indexes = np.arange(N)
    x = np.copy(x0)
    for _ in tqdm(range(n_epochs)):
        np.random.shuffle(indexes)
        for i in tqdm(range(n_iter)):
            ib = i*batch_size
            batch_ids = indexes[ib : ib + batch_size]
            grad = np.full(N, 0, dtype = np.float)
            grad[batch_ids] += der_loss(x, batch_ids)
            x = x - (l_rate/batch_size)*grad
    return x

# %% Setup
train_movies = train.movieId.unique()
test_movies = test.movieId.unique()
all_movies = sorted(np.concatenate((train_movies, test_movies[~ np.isin(test_movies, train_movies)])))
d = len(all_movies) # 9724
train_users = train.userId.unique()
test_users = test.userId.unique()
all_users = np.concatenate((train_users, test_users[~ np.isin(test_users, train_users)]))
n = len(all_users) # 610
avg_rating = np.mean(train.rating)
Z_zero = np.full((n,d), 0, dtype = np.float)
Z_nan = np.full((n,d), np.nan, dtype = np.float)
print('Reading training data ... ')
fill_matrix(Z_zero)
non_nan_train = np.argwhere(~np.isnan(Z_nan)) # list of pairs of indices
entries = Z_zero > 0
filled_entries = Z_zero[entries]
print('Creating the initial matrix ...')

# %% Create matrix Z_avg_user: fills matrix with an average rating of a user
user_avgs = np.array(train.groupby('userId')['rating'].mean())
Z_avg_user = np.repeat(user_avgs, d).reshape(n,d)

# %% Create matrix Z_avg_movie: fills matrix with an average rating of a movie and avg_rating for unrated movies
movie_avgs = train.groupby('movieId')['rating'].mean()
movie_row = np.repeat(avg_rating, d)
for id, rating in movie_avgs.iteritems(): movie_row[all_movies.index(id)] = rating
Z_avg_movie = np.array([movie_row]*n)

# %% Optimal weighted mean of Z_avg_user and Z_avg_movie
ps = np.arange(21)/20
best_loss = 1000000
best_p = 0
for p in ps:
    Z_avg_user_movie = p*Z_avg_user + (1-p)*Z_avg_movie
    new = np.sum((Z_avg_user_movie[entries] - filled_entries)**2)
    if new < best_loss: 
        best_loss = new
        best_p = p
p = best_p
Z_avg_user_movie = p*Z_avg_user + (1-p)*Z_avg_movie

# %% Fill matrices with training data
Z_avg_user[entries] = filled_entries
Z_avg_movie[entries] = filled_entries
Z_avg_user_movie[entries] = filled_entries

# %% Create matrix Z_close_users: fills matrix with mean ratings of the most similar users
def close_users(Z_, percent = 0.1):
    Z_close_users = np.full((n,d), 0)
    for i in tqdm(range(n)):
        user = Z_[i,]
        Z_user = (Z_ - user)**2
        distances = Z_user.sum(axis=1)
        q = np.quantile(distances, percent)
        indexes = distances <= q
        enum = np.arange(len(distances))
        indexes = enum[indexes]
        close_users = Z_[indexes]
        prediction = close_users.mean(axis=0)
        Z_close_users[i,] = prediction
    return Z_close_users

# Z_close_users = close_users(Z_avg_user)

def run_test(alg, mat_name = '_', **kwargs):
    ''' Run test on algorithm `alg` with parameters passed as keyword arguments; Returns obtained RMSE '''
    algs = {"NMF": approx_NMF,
    "SVD1": approx_SVD1,
    "SVD2": approx_SVD2,
    "SGD": approx_SGD, 
    "NMF2_SVD2": approx_NMF2_SVD2}
    print('Building a model ...')
    start = time()
    Z_approx, log = algs[alg](**kwargs)
    result = RMSE(Z_approx)
    stop = time()
    print(f'For matrix {mat_name} ' + log + f' (Total time: {stop - start})', file = open('results_log.txt', 'a')) # append mode
    return result

# %% Program
if __name__=='__main__':
    result = run_test(args.alg, Z_ = Z_avg_user_movie)
    with open(f'{args.result_file}', 'w') as f_out: 
        f_out.write(str(result))
    print('Finished.')