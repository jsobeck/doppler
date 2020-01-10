#!/usr/bin/env python

"""UTILS.PY - Utility functions

"""

from __future__ import print_function

__authors__ = 'David Nidever <dnidever@noao.edu>'
__version__ = '20180922'  # yyyymmdd                                                                                                                           

#import os
import numpy as np
import warnings
from scipy import sparse
from scipy.interpolate import interp1d
from dlnpyutils import utils as dln

# Ignore these warnings, it's a bug
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

cspeed = 2.99792458e5  # speed of light in km/s

# Convert wavelengths to pixels for a dispersion solution
def w2p(dispersion,w,extrapolate=True):
    """ dispersion is the wavelength array of the spectrum"""
    x = interp1d(dispersion,np.arange(len(dispersion)),kind='cubic',bounds_error=False,fill_value=(np.nan,np.nan),assume_sorted=False)(w)
    # Need to extrapolate
    if ((np.min(w)<np.min(dispersion)) | (np.max(w)>np.max(dispersion))) & (extrapolate is True):
        win = dispersion
        xin = np.arange(len(dispersion))
        si = np.argsort(win)
        win = win[si]
        xin = xin[si]
        npix = len(win)
        # At the beginning
        if (np.min(w)<np.min(dispersion)):
            coef1 = dln.poly_fit(win[0:10], xin[0:10], 2)
            bd1, nbd1 = dln.where(w < np.min(dispersion))
            x[bd1] = dln.poly(w[bd1],coef1)
        # At the end
        if (np.max(w)>np.max(dispersion)):
            coef2 = dln.poly_fit(win[npix-10:], xin[npix-10:], 2)
            bd2, nbd2 = dln.where(w > np.max(dispersion))
            x[bd2] = dln.poly(w[bd2],coef2)                
    return x


# Convert pixels to wavelength for a dispersion solution
def p2w(dispersion,x,extrapolate=True):
    """ dispersion is the wavelength array of the spectrum"""
    npix = len(dispersion)
    w = interp1d(np.arange(len(dispersion)),dispersion,kind='cubic',bounds_error=False,fill_value=(np.nan,np.nan),assume_sorted=False)(x)
    # Need to extrapolate
    if ((np.min(x)<0) | (np.max(x)>(npix-1))) & (extrapolate is True):
        xin = np.arange(npix)
        win = dispersion
        # At the beginning
        if (np.min(x)<0):
            coef1 = dln.poly_fit(xin[0:10], win[0:10], 2)
            bd1, nbd1 = dln.where(x < 0)
            w[bd1] = dln.poly(x[bd1],coef1)
        # At the end
        if (np.max(x)>(npix-1)):
            coef2 = dln.poly_fit(xin[npix-10:], win[npix-10:], 2)
            bd2, nbd2 = dln.where(x > (npix-1))
            w[bd2] = dln.poly(x[bd2],coef2)                
    return w


def sparsify(lsf):
    # sparsify
    # make a sparse matrix
    # from J.Bovy's lsf.py APOGEE code
    nx = lsf.shape[1]
    diagonals = []
    offsets = []
    for ii in range(nx):
        offset= nx//2-ii
        offsets.append(offset)
        if offset < 0:
            diagonals.append(lsf[:offset,ii])
        else:
            diagonals.append(lsf[offset:,ii])
    return sparse.diags(diagonals,offsets)

def convolve_sparse(spec,lsf):
    # convolution with matrices
    # from J.Bovy's lsf.py APOGEE code    
    # spec - [npix]
    # lsf - [npix,nlsf]
    npix,nlsf = lsf.shape
    lsf2 = sparsify(lsf)
    spec2 = np.reshape(spec,(1,npix))
    spec2 = sparse.csr_matrix(spec2) 
    out = lsf2.dot(spec2.T).T.toarray()
    out = np.reshape(out,len(spec))
    # The ends are messed up b/c not normalized
    hlf = nlsf//2
    for i in range(hlf+1):
        lsf1 = lsf[i,hlf-i:]
        lsf1 /= np.sum(lsf1)
        out[i] = np.sum(spec[0:len(lsf1)]*lsf1)
    for i in range(hlf+1):
        ii = npix-i-1
        lsf1 = lsf[ii,:hlf+1+i]
        lsf1 /= np.sum(lsf1)
        out[ii] = np.sum(spec[npix-len(lsf1):]*lsf1)
    return out


# Make logaritmic wavelength scale
def make_logwave_scale(wave,vel=1000.0):
    """ Make logarithmic wavelength scale for this observed wavelength scale."""

    # If the existing wavelength scale is logaritmic them use it, just extend
    # on either side
    vel = np.abs(vel)
    wave = np.float64(wave)
    nw = len(wave)
    wr = dln.minmax(wave)
    # extend wavelength range by +/-vel km/s
    wlo = wr[0]-vel/cspeed*wr[0]
    whi = wr[1]+vel/cspeed*wr[1]
    dwlog = np.median(dln.slope(np.log10(np.float64(wave))))
    
    nlo = np.int(np.ceil((np.log10(np.float64(wr[0]))-np.log10(np.float64(wlo)))/dwlog))    
    nhi = np.int(np.ceil((np.log10(np.float64(whi))-np.log10(np.float64(wr[1])))/dwlog))
    if vel==0.0:
        n = np.int((np.log10(np.float64(wr[1]))-np.log10(np.float64(wr[0])))/dwlog)
    else:
        n = np.int(np.ceil((np.log10(np.float64(wr[1]))-np.log10(np.float64(wr[0])))/dwlog))        
    nf = n+nlo+nhi

    fwave = 10**( (np.arange(nf)-nlo)*dwlog+np.log10(np.float64(wr[0])) )

    # Make sure the element that's associated with the first input wavelength is identical
    fwave -= fwave[nlo]-wave[0]
    
    # w=10**(w0log+i*dwlog)
    return fwave
    