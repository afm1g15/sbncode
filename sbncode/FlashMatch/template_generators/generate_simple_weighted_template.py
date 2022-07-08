#! /usr/bin/env python
######################################################################
#
# Name: generate_simple_weighted_template.py
#
# Purpose: Create templates
#
# Created: February-2020  Iker Loïc de Icaza Astiz (icaza@fnal.gov)
#
# Usage:
#
# generate_simple_weighted_template.py (--sbnd | --icarus) file
#
# Options:
#
# [-h|--help] - Print help message.
# (--sbnd or --icarus) to select for which experiment generate metrics
# Arguments:
#
# file  ... - Input file.
#
######################################################################

import sys
import os
import string
import argparse
import numpy as np
from time import sleep
from array import array

from ROOT import TStyle, TCanvas, TColor, TGraph, TGraphErrors
from ROOT import TH1D, TH2D, TProfile, TFile, TF1
from ROOT import gROOT
import ROOT

try:
    # import project_utilities
    import larbatch_posix
    import fhicl
except ImportError:
    print("Failed to import 'larbatch_posix' or 'fhicl' modules")
    print("Setup 'fhiclpy' first:\n\tsetup fhiclpy vV_VV_VV -q QQQ:QQQQ")
    exit(1)


class dotDict(dict):
    def __getattr__(self,val):
        return self[val]


def sig_fig_round(number, digits=3):
    power = "{:e}".format(number).split('e')[1]
    return round(number, -(int(power) - digits))

# Globally turn off root warnings.
# Don't let root see our command line options.
myargv = sys.argv
sys.argv = myargv[0:1]
if 'TERM' in os.environ:
    del os.environ['TERM']
ROOT.gErrorIgnoreLevel = ROOT.kError
sys.argv = myargv

# TODO: work out the best values for these
ROOT.gStyle.SetStatX(0.4)
ROOT.gStyle.SetStatY(0.88)
ROOT.gStyle.SetStatW(0.15)
# ROOT.gStyle.SetStatH(0.2)
ROOT.gStyle.SetOptStat(1111)
ROOT.gStyle.SetOptFit(1111)

detector = "experiment"
# # Print help
# def help():

#     filename = sys.argv[0]
#     file = open(filename)

#     doprint = False

#     for line in file.readlines():
#         if line[2:9] == 'stat.py':
#             doprint = True
#         elif line[0:6] == '######' and doprint:
#             doprint = False
#         if doprint:
#             if len(line) > 2:
#                 print(line[2:], end=' ')
#             else:
#                 print()



def hypo_flashx_from_H2(flash_rr, rr_h2, flash_ratio, ratio_h2):
    rr_hypoX, rr_hypoXWgt = x_estimate_and_rms(flash_rr, rr_h2);
    ratio_hypoX, ratio_hypoXWgt = x_estimate_and_rms(flash_ratio, ratio_h2);

    sum_weights = rr_hypoXWgt + ratio_hypoXWgt
    hypo_x = (rr_hypoX*rr_hypoXWgt + ratio_hypoX*ratio_hypoXWgt) / sum_weights
    hypo_x_err = np.sqrt(sum_weights) / sum_weights
    # return (hypo_x, hypo_x_err, rr_hypoX, ratio_hypoX)
    return hypo_x


def x_estimate_and_rms(metric_value, metric_h2):
    kMinEntriesInProjection = 100
    fXBinWidth = 5.
    bin_ = metric_h2.GetYaxis().FindBin(metric_value);
    bins = metric_h2.GetNbinsY();
    metric_hypoX = -1.;
    metric_hypoXWgt = 0.;
    bin_buff = 0;
    while 0 < bin_-bin_buff or bin_+bin_buff <= bins :
        low_bin = bin_-bin_buff if 0 < bin_-bin_buff else 0
        high_bin = bin_+bin_buff if bin_+bin_buff <= bins else -1
        metric_px = metric_h2.ProjectionX("metric_px", low_bin, high_bin);
        if metric_px.GetEntries() > kMinEntriesInProjection :
            metric_hypoX = metric_px.GetRandom();
            metric_rmsX = metric_px.GetRMS();
            if metric_rmsX < fXBinWidth: # something went wrong
                print(f"{metric_h2.GetName()} projected on metric_value: {metric_value}, "
                      f"bin: {bin_}, bin_buff: {bin_buff}; has {metric_px.GetEntries()} entries.")
                print(f"  metric_hypoX: {metric_hypoX}, metric_rmsX: {metric_rmsX}")
                return (-1., 0.); # no estimate
            metric_hypoXWgt = 1/(metric_rmsX*metric_rmsX);
            return (metric_hypoX, metric_hypoXWgt);
        bin_buff += 1;
    return (-1., 0.); # no estimate


def quality_checks(e):
    if e.slices != 1: return False
    if e.true_nus != 1: return False
    if e.mcT0 < 0. or 1.6 < e.mcT0 : return False # TODO: unhardcode
    if e.charge_x < 0.: return False
    return True


def polinomial_correction(skew, hypo_x, pol_coefs, skew_high_limit=10.):
    # TODO: maybe some other condition to prevent corrections?
    if np.abs(skew) > skew_high_limit or np.isnan(hypo_x):
        return 0.
    correction = 0.
    exponent = 1.
    for coef in pol_coefs:
        correction += coef * exponent
        exponent *= hypo_x
    return correction * skew


def parameters_correction_fitter(nuslice_tree, var, profile_bins,
                                 dist_to_anode_low, dist_to_anode_up,
                                 skew_high_limit=10., skew_low_limit=0.05):
    fit_prof = TProfile(f"fit_prof_{var}", "", profile_bins,
                        dist_to_anode_low, dist_to_anode_up)
    draw_expression = (f"((flash_{var}b-charge_{var})/{var}_skew):new_hypo_x"
                       f">>fit_prof_{var}")
    draw_filters = (f"abs({var}_skew)>{skew_low_limit} && "
                    f"abs({var}_skew)<{skew_high_limit} && "
                    f"true_nus==1 && slices==1 && "
                    f"0.<mcT0 && mcT0<1.6")
    draw_option = "prof" # TODO: maybe better to use "profs"
    print(draw_expression, draw_filters, draw_option)
    can = TCanvas("can")
    nuslice_tree.Draw(draw_expression, draw_filters, draw_option)
    fit_result = fit_prof.Fit("pol2", "S")
    fit_prof.Write()
    fit_result.Print("V")
    can.Print(f"{var}_correction_fit.pdf")
    params = []
    for p in fit_result.Parameters():
        params.append(sig_fig_round(p, 3))
    print("The fitted and rounded correction parameters for ", var, " are: ", params)
    print("Please update the fcl files with these values")
    return params


def generator(nuslice_tree, rootfile, pset):
    drift_distance = pset.DriftDistance
    x_bins = pset.XBins
    xbin_width = drift_distance/x_bins
    half_bin_width = xbin_width/2.

    xvals = np.arange(half_bin_width, drift_distance, xbin_width)
    xerrs = np.array([half_bin_width] * len(xvals))
    dist_to_anode_bins = x_bins
    dist_to_anode_low = 0.
    dist_to_anode_up = drift_distance
    if detector == "sbnd":
        x_gl_low = -215
        x_gl_up = 215
    elif detector == "icarus":
        if pset.Cryostat == 0:
            x_gl_low = -380
            x_gl_up = -50
        if pset.Cryostat == 1:
            x_gl_low = 380
            x_gl_up = 50

    profile_bins = x_bins
    profile_option = 's'  # errors are the standard deviation

    dy_spreads = [None] * x_bins
    dy_means = [None] * x_bins
    dy_h2 = TH2D("dy_h2", "#Delta y",
                 dist_to_anode_bins, dist_to_anode_low, dist_to_anode_up,
                 pset.dy_bins, pset.dy_low, pset.dy_up)
    dy_h2.GetXaxis().SetTitle("distance from anode (cm)")
    dy_h2.GetYaxis().SetTitle("y_flash - y_TPC (cm)")
    dy_prof = TProfile("dy_prof", "Profile of dy_spreads in #Delta y",
                       profile_bins, dist_to_anode_low, dist_to_anode_up,
                       pset.dy_low*2, pset.dy_up*2, profile_option)
    dy_prof.GetXaxis().SetTitle("distance from anode (cm)")
    dy_prof.GetYaxis().SetTitle("y_flash - y_TPC (cm)")
    dy_h1 = TH1D("dy_h1", "",
                 profile_bins, dist_to_anode_low, dist_to_anode_up)
    dy_h1.GetXaxis().SetTitle("distance from anode (cm)")
    dy_h1.GetYaxis().SetTitle("y_flash - y_TPC (cm)")

    dz_spreads = [None] * x_bins
    dz_means = [None] * x_bins
    dz_h2 = TH2D("dz_h2", "#Delta z",
                 dist_to_anode_bins, dist_to_anode_low, dist_to_anode_up,
                 pset.dz_bins, pset.dz_low, pset.dz_up)
    dz_h2.GetXaxis().SetTitle("distance from anode (cm)")
    dz_h2.GetYaxis().SetTitle("z_flash - z_TPC (cm)")
    dz_prof = TProfile("dz_prof", "Profile of dz_spreads in #Delta z",
                       profile_bins, dist_to_anode_low, dist_to_anode_up,
                       pset.dz_low*2.5, pset.dz_up*2.5, profile_option)
    dz_prof.GetXaxis().SetTitle("distance from anode (cm)")
    dz_prof.GetYaxis().SetTitle("z_flash - z_TPC (cm)")
    dz_h1 = TH1D("dz_h1", "",
                 profile_bins, dist_to_anode_low, dist_to_anode_up)
    dz_h1.GetXaxis().SetTitle("distance from anode (cm)")
    dz_h1.GetYaxis().SetTitle("z_flash - z_TPC (cm)")

    rr_spreads = [None] * x_bins
    rr_means = [None] * x_bins
    rr_h2 = TH2D("rr_h2", "PE Spread",
                 dist_to_anode_bins, dist_to_anode_low, dist_to_anode_up,
                 pset.rr_bins, pset.rr_low, pset.rr_up)
    rr_h2.GetXaxis().SetTitle("distance from anode (cm)")
    rr_h2.GetYaxis().SetTitle("spread (cm)")
    rr_prof = TProfile("rr_prof", "Profile of PE Spread",
                       profile_bins, dist_to_anode_low, dist_to_anode_up,
                       pset.rr_low, pset.rr_up, profile_option)
    rr_prof.GetXaxis().SetTitle("distance from anode (cm)")
    rr_prof.GetYaxis().SetTitle("spread (cm)")
    rr_h1 = TH1D("rr_h1", "",
                 profile_bins, dist_to_anode_low, dist_to_anode_up)
    rr_h1.GetXaxis().SetTitle("distance from anode (cm)")
    rr_h1.GetYaxis().SetTitle("spread (cm)")

    ratio_spreads = [None] * x_bins
    ratio_means = [None] * x_bins
    ratio_h2 = TH2D("ratio_h2", "PE Ratio",
                    dist_to_anode_bins, dist_to_anode_low, dist_to_anode_up,
                    pset.ratio_bins, pset.ratio_low, pset.ratio_up)
    ratio_h2.GetXaxis().SetTitle("distance from anode (cm)")
    ratio_h2.GetYaxis().SetTitle("ratio")
    ratio_prof = TProfile("ratio_prof", "Profile of PE Ratio",
                          profile_bins, dist_to_anode_low, dist_to_anode_up,
                          pset.ratio_low, pset.ratio_up, profile_option)
    ratio_prof.GetXaxis().SetTitle("distance from anode (cm)")
    ratio_prof.GetYaxis().SetTitle("ratio")
    ratio_h1 = TH1D("ratio_h1", "",
                    profile_bins, dist_to_anode_low, dist_to_anode_up)
    ratio_h1.GetXaxis().SetTitle("distance from anode (cm)")
    ratio_h1.GetYaxis().SetTitle("ratio")

    slope_spreads = [None] * x_bins
    slope_means = [None] * x_bins
    slope_h2 = TH2D("slope_h2", "Z/Y Slope",
                    dist_to_anode_bins, dist_to_anode_low, dist_to_anode_up,
                    pset.slope_bins, pset.slope_low, pset.slope_up)
    slope_h2.GetXaxis().SetTitle("distance from anode (cm)")
    slope_h2.GetYaxis().SetTitle("slope")
    slope_prof = TProfile("slope_prof", "Profile of Z/Y Slope",
                          profile_bins, dist_to_anode_low, dist_to_anode_up,
                          pset.slope_low, pset.slope_up, profile_option)
    slope_prof.GetXaxis().SetTitle("distance from anode (cm)")
    slope_prof.GetYaxis().SetTitle("slope")
    slope_h1 = TH1D("slope_h1", "",
                    profile_bins, dist_to_anode_low, dist_to_anode_up)
    slope_h1.GetXaxis().SetTitle("distance from anode (cm)")
    slope_h1.GetYaxis().SetTitle("slope")

    petoq_spreads = [None] * x_bins
    petoq_means = [None] * x_bins
    petoq_h2 = TH2D("petoq_h2", "PE to Q Ratio",
                    dist_to_anode_bins, dist_to_anode_low, dist_to_anode_up,
                    pset.petoq_bins, pset.petoq_low, pset.petoq_up)
    petoq_h2.GetXaxis().SetTitle("distance from anode (cm)")
    petoq_h2.GetYaxis().SetTitle("petoq")
    petoq_prof = TProfile("petoq_prof", "Profile of PE to Q Ratio",
                          profile_bins, dist_to_anode_low, dist_to_anode_up,
                          pset.petoq_low, pset.petoq_up, profile_option)
    petoq_prof.GetXaxis().SetTitle("distance from anode (cm)")
    petoq_prof.GetYaxis().SetTitle("petoq")
    petoq_h1 = TH1D("petoq_h1", "",
                    profile_bins, dist_to_anode_low, dist_to_anode_up)
    petoq_h1.GetXaxis().SetTitle("distance from anode (cm)")
    petoq_h1.GetYaxis().SetTitle("petoq")

    unfolded_score_scatter = TH2D("unfolded_score_scatter", "Scatter plot of match scores",
                                  2*dist_to_anode_bins, x_gl_low, x_gl_up,
                                  pset.score_hist_bins, pset.score_hist_low, pset.score_hist_up*(3./5.))
    unfolded_score_scatter.GetXaxis().SetTitle("X global (cm)")
    unfolded_score_scatter.GetYaxis().SetTitle("match score (arbitrary)")
    oldunfolded_score_scatter = TH2D("oldunfolded_score_scatter", "Scatter plot of match scores, old metrics",
                                     2*dist_to_anode_bins, x_gl_low, x_gl_up,
                                     pset.score_hist_bins, pset.score_hist_low, pset.score_hist_up*(3./5.))
    oldunfolded_score_scatter.GetXaxis().SetTitle("X global (cm)")
    oldunfolded_score_scatter.GetYaxis().SetTitle("match score (arbitrary)")
    match_score_scatter = TH2D("match_score_scatter", "Scatter plot of match scores",
                               dist_to_anode_bins, dist_to_anode_low, dist_to_anode_up,
                               pset.score_hist_bins, pset.score_hist_low, pset.score_hist_up*(3./5.))
    match_score_scatter.GetXaxis().SetTitle("distance from anode (cm)")
    match_score_scatter.GetYaxis().SetTitle("match score (arbitrary)")
    match_score_h1 = TH1D("match_score", "Match Score",
                          pset.score_hist_bins, pset.score_hist_low, pset.score_hist_up)
    match_score_h1.GetXaxis().SetTitle("match score (arbitrary)")

    metrics_filename = 'fm_metrics_' + detector + '.root'
    hfile = gROOT.FindObject(metrics_filename)
    if hfile:
        hfile.Close()
    hfile = TFile(metrics_filename, 'RECREATE',
                  'Simple flash matching metrics for ' + detector.upper())

    # fill rr_h2 and ratio_h2 first
    for e in nuslice_tree:
        if not quality_checks(e): continue
        qX = e.charge_x
        rr_h2.Fill(qX, e.flash_rr)
        rr_prof.Fill(qX, e.flash_rr)
        ratio_h2.Fill(qX, e.flash_ratio)
        ratio_prof.Fill(qX, e.flash_ratio)
    # store the new hypothesis of the flash x position hypo_x
    new_hypo_x = array('d',[0])
    new_hypo_x_branch = nuslice_tree.Branch("new_hypo_x", new_hypo_x, "new_hypo_x/D");
    for e in nuslice_tree:
        new_hypo_x[0] = hypo_flashx_from_H2(e.flash_rr, rr_h2,
                                            e.flash_ratio, ratio_h2)
        new_hypo_x_branch.Fill()
    y_pol_coefs = parameters_correction_fitter(nuslice_tree, "y", profile_bins,
                                               dist_to_anode_low, dist_to_anode_up,
                                               pset.SkewLimitY)
    z_pol_coefs = parameters_correction_fitter(nuslice_tree, "z", profile_bins,
                                               dist_to_anode_low, dist_to_anode_up,
                                               pset.SkewLimitZ)

    # use rr_h2 and ratio_h2 to compute hypo_x
    for e in nuslice_tree:
        if not quality_checks(e): continue
        qX = e.charge_x
        corr_flash_y = e.flash_yb - polinomial_correction(e.y_skew, e.new_hypo_x,
                                                          y_pol_coefs)
        corr_flash_z = e.flash_zb - polinomial_correction(e.z_skew, e.new_hypo_x,
                                                          z_pol_coefs)
        dy_h2.Fill(qX, corr_flash_y - e.charge_y)
        dy_prof.Fill(qX, corr_flash_y - e.charge_y)
        dz_h2.Fill(qX, corr_flash_z - e.charge_z)
        dz_prof.Fill(qX, corr_flash_z - e.charge_z)

        slope_h2.Fill(qX, e.flash_slope - e.charge_slope)
        slope_prof.Fill(qX, e.flash_slope - e.charge_slope)
        petoq_h2.Fill(qX, e.petoq)
        petoq_prof.Fill(qX, e.petoq)

    # fill histograms for match score calculation from profile histograms
    for ib in list(range(0, profile_bins)):
        ibp = ib + 1
        dy_h1.SetBinContent(ibp, dy_prof.GetBinContent(ibp))
        dy_h1.SetBinError(ibp, dy_prof.GetBinError(ibp))
        dy_means[int(ib)] = dy_prof.GetBinContent(ibp)
        dy_spreads[int(ib)] = dy_prof.GetBinError(ibp)
        dz_h1.SetBinContent(ibp, dz_prof.GetBinContent(ibp))
        dz_h1.SetBinError(ibp, dz_prof.GetBinError(ibp))
        dz_means[int(ib)] = dz_prof.GetBinContent(ibp)
        dz_spreads[int(ib)] = dz_prof.GetBinError(ibp)
        rr_h1.SetBinContent(ibp, rr_prof.GetBinContent(ibp))
        rr_h1.SetBinError(ibp, rr_prof.GetBinError(ibp))
        rr_means[int(ib)] = rr_prof.GetBinContent(ibp)
        rr_spreads[int(ib)] = rr_prof.GetBinError(ibp)
        ratio_h1.SetBinContent(ibp, ratio_prof.GetBinContent(ibp))
        ratio_h1.SetBinError(ibp, ratio_prof.GetBinError(ibp))
        ratio_means[int(ib)] = ratio_prof.GetBinContent(ibp)
        ratio_spreads[int(ib)] = ratio_prof.GetBinError(ibp)
        slope_h1.SetBinContent(ibp, slope_prof.GetBinContent(ibp))
        slope_h1.SetBinError(ibp, slope_prof.GetBinError(ibp))
        slope_means[int(ib)] = slope_prof.GetBinContent(ibp)
        slope_spreads[int(ib)] = slope_prof.GetBinError(ibp)
        petoq_h1.SetBinContent(ibp, petoq_prof.GetBinContent(ibp))
        petoq_h1.SetBinError(ibp, petoq_prof.GetBinError(ibp))
        petoq_means[int(ib)] = petoq_prof.GetBinContent(ibp)
        petoq_spreads[int(ib)] = petoq_prof.GetBinError(ibp)

    for e in nuslice_tree:
        if not quality_checks(e): continue
        qX = e.charge_x
        qXGl = e.charge_x_gl
        # calculate match score
        isl = int(qX/xbin_width)
        score = 0.
        if dy_spreads[isl] <= 1.e-8:
            print("Warning zero spread.\n",
                  f"qX: {qX}. isl: {isl}. dy_spreads[isl]: {dy_spreads[isl]} ")
            dy_spreads[isl] = dy_spreads[isl+1]
        if dz_spreads[isl] <= 1.e-8:
            print("Warning zero spread.\n",
                  f"qX: {qX}. isl: {isl}. dz_spreads[isl]: {dz_spreads[isl]} ")
            dz_spreads[isl] = dz_spreads[isl+1]
        if rr_spreads[isl] <= 1.e-8:
            print("Warning zero spread.\n",
                  f"qX: {qX}. isl: {isl}. rr_spreads[isl]: {rr_spreads[isl]} ")
            rr_spreads[isl] = rr_spreads[isl+1]
        if ratio_spreads[isl] <= 1.e-8:
            print("Warning zero spread.\n",
                  f"qX: {qX}. isl: {isl}. ratio_spreads[isl]: {ratio_spreads[isl]} ")
            ratio_spreads[isl] = ratio_spreads[isl+1]
        if slope_spreads[isl] <= 1.e-8:
            print("Warning zero spread.\n",
                  f"qX: {qX}. isl: {isl}. slope_spreads[isl]: {slope_spreads[isl]} ")
            slope_spreads[isl] = slope_spreads[isl+1]
        if petoq_spreads[isl] <= 1.e-8:
            print("Warning zero spread.\n",
                  f"qX: {qX}. isl: {isl}. petoq_spreads[isl]: {petoq_spreads[isl]} ")
            petoq_spreads[isl] = petoq_spreads[isl+1]
        corr_flash_y = e.flash_yb - polinomial_correction(e.y_skew, e.new_hypo_x,
                                                          y_pol_coefs)
        corr_flash_z = e.flash_zb - polinomial_correction(e.z_skew, e.new_hypo_x,
                                                          z_pol_coefs)

        score += abs((corr_flash_y-e.charge_y) - dy_means[isl])/dy_spreads[isl]
        score += abs((corr_flash_z-e.charge_z) - dz_means[isl])/dz_spreads[isl]
        score += abs(e.flash_rr-rr_means[isl])/rr_spreads[isl]
        if (detector == "sbnd" and pset.UseUncoatedPMT) or \
           (detector == "icarus" and pset.UseOppVolMetric) :
            score += abs(e.flash_ratio-ratio_means[isl])/ratio_spreads[isl]
        score += abs((e.flash_slope - e.charge_slope) - slope_means[isl])/slope_spreads[isl]
        score += abs(e.petoq-petoq_means[isl])/petoq_spreads[isl]

        oldunfolded_score_scatter.Fill(qXGl, e.score)
        unfolded_score_scatter.Fill(qXGl, score)
        match_score_scatter.Fill(qX, score)
        match_score_h1.Fill(score)

    dy_h2.Write()
    dy_prof.Write()
    dy_h1.Write()
    dz_h2.Write()
    dz_prof.Write()
    dz_h1.Write()
    rr_h2.Write()
    rr_prof.Write()
    rr_h1.Write()

    errors = [1, 0, -1]
    fitname_suffix = ["_h", "_m", "_l"]
    rr_fit_funcs = []
    for e,suf in zip(errors, fitname_suffix):
        yvals = [a + e*b for a, b in zip(rr_means, rr_spreads)]
        graph = TGraph(x_bins,
                       array('f', xvals), array('f', yvals))
        name = "rr_fit" + suf
        print("Fitting: ", name)
        f = TF1(name, pset.rr_TF1_fit)
        graph.Fit(f)
        f.Write()
        rr_fit_funcs.append(f)
    ratio_h2.Write()
    ratio_prof.Write()
    ratio_h1.Write()
    ratio_fit_funcs = []
    for e,suf in zip(errors, fitname_suffix):
        yvals = [a + e*b for a, b in zip(ratio_means, ratio_spreads)]
        graph = TGraph(x_bins,
                       array('f', xvals), array('f', yvals))
        name = "ratio_fit" + suf
        print("Fitting: ", name)
        f = TF1(name, pset.ratio_TF1_fit)
        graph.Fit(f)
        f.Write()
        ratio_fit_funcs.append(f)
    slope_h2.Write()
    slope_prof.Write()
    slope_h1.Write()
    petoq_h2.Write()
    petoq_prof.Write()
    petoq_h1.Write()
    match_score_scatter.Write()
    oldunfolded_score_scatter.Write()
    unfolded_score_scatter.Write()
    match_score_h1.Write()
    hfile.Close()

    canv = TCanvas("canv")

    dy_h2.Draw()
    crosses = TGraphErrors(x_bins,
                           array('f', xvals), array('f', dy_means),
                           array('f', xerrs), array('f', dy_spreads))
    crosses.SetLineColor(ROOT.kAzure+9)
    crosses.SetLineWidth(3)
    crosses.Draw("Psame")
    canv.Print("dy.pdf")
    canv.Update()

    dz_h2.Draw()
    crosses = TGraphErrors(x_bins,
                           array('f', xvals), array('f', dz_means),
                           array('f', xerrs), array('f', dz_spreads))
    crosses.SetLineColor(ROOT.kAzure+9)
    crosses.SetLineWidth(3)
    crosses.Draw("Psame")
    canv.Print("dz.pdf")
    canv.Update()

    rr_h2.Draw()
    crosses = TGraphErrors(x_bins,
                           array('f', xvals), array('f', rr_means),
                           array('f', xerrs), array('f', rr_spreads))
    crosses.SetLineColor(ROOT.kAzure+9)
    crosses.SetLineWidth(3)
    crosses.Draw("Psame")
    for f in rr_fit_funcs:
        f.SetLineColor(ROOT.kOrange+7)
        f.DrawF1(0., drift_distance, "lsame")
    canv.Print("rr.pdf")
    canv.Update()

    ratio_h2.Draw()
    crosses = TGraphErrors(x_bins,
                           array('f', xvals), array('f', ratio_means),
                           array('f', xerrs), array('f', ratio_spreads))
    crosses.SetLineColor(ROOT.kAzure+9)
    crosses.SetLineWidth(3)
    crosses.Draw("Psame")
    for f in ratio_fit_funcs:
        f.SetLineColor(ROOT.kOrange+7)
        f.DrawF1(0., drift_distance, "lsame")
    canv.Print("ratio.pdf")
    canv.Update()

    slope_h2.Draw()
    crosses = TGraphErrors(x_bins,
                           array('f', xvals), array('f', slope_means),
                           array('f', xerrs), array('f', slope_spreads))
    crosses.SetLineColor(ROOT.kAzure+9)
    crosses.SetLineWidth(3)
    crosses.Draw("Psame")
    canv.Print("slope.pdf")
    canv.Update()

    petoq_h2.Draw()
    crosses = TGraphErrors(x_bins,
                           array('f', xvals), array('f', petoq_means),
                           array('f', xerrs), array('f', petoq_spreads))
    crosses.SetLineColor(ROOT.kAzure+9)
    crosses.SetLineWidth(3)
    crosses.Draw("Psame")
    canv.Print("petoq.pdf")
    canv.Update()

    oldunfolded_score_scatter.Draw()
    canv.Print("oldunfolded_score_scatter.pdf")
    canv.Update()

    unfolded_score_scatter.Draw()
    canv.Print("unfolded_score_scatter.pdf")
    canv.Update()

    match_score_scatter.Draw()
    canv.Print("match_score_scatter.pdf")
    canv.Update()

    match_score_h1.Draw()
    canv.Print("match_score.pdf")
    canv.Update()
    sleep(20)

# Main program.
def main():

    # Parse arguments.
    parser = argparse.ArgumentParser(prog='generate_simple_weighted_template.py')
    parser.add_argument('file')
    # parser.add_argument('--help', '-h',
    #                     action='store_true',
    #                     help='help flag' )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--sbnd', action='store_true', help='Generate metrics for SBND')
    group.add_argument('--icarus', action='store_true', help='Generate metrics for ICARUS')
    args = parser.parse_args()

    # if args.help:
    #     print("To run do:\n"/
    #           "generate_simple_weighted_template.py file.root\n"/
    #           "where file.root has a fmatch/nuslicetree")
    #     return(0)
    if args.sbnd :
        print("Generate metrics for SBND")
    elif args.icarus :
        print("Generate metrics for ICARUS")

    if not larbatch_posix.exists(args.file):
        print('Input file %s does not exist.' % args.file)
        return 1

    # TODO: better not modify the original file: open and read it, make a copy and then modify the copy
    print('\nOpening %s' % args.file)
    rootfile = TFile.Open(args.file, 'update')
    if not rootfile.IsOpen() or rootfile.IsZombie():
        print('Failed to open %s' % args.file)
        return 1
    global detector
    if args.sbnd:
        fcl_params = fhicl.make_pset('flashmatch_sbnd.fcl')
        pset = dotDict(fcl_params['sbnd_simple_flashmatch'])
        detector = "sbnd"
        dir = rootfile.Get(args.file+":/fmatch")
        nuslice_tree = dir.Get("nuslicetree")  # , nuslice_tree)
        # nuslice_tree.Print()
    elif args.icarus:
        fcl_params = fhicl.make_pset('flashmatch_simple_icarus.fcl')
        # TODO: add option to use cryo 0 and cryo 1
        pset = dotDict(fcl_params['icarus_simple_flashmatch_0'])
        detector = "icarus"
        dir = rootfile.Get(args.file+":/fmatchCryo0")
        nuslice_tree = dir.Get("nuslicetree")  # , nuslice_tree)
        # nuslice_tree.Print()

    generator(nuslice_tree, rootfile, pset)


if __name__ == '__main__':
    sys.exit(main())
