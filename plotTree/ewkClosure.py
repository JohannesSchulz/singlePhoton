#! /usr/bin/env python2
# -*- coding: utf-8 -*-
import ROOT
import re
import argparse
from math import sqrt
from multiplot import *
from treeFunctions import *
import ratios
import Styles

Styles.tdrStyle()
ROOT.gROOT.SetBatch()
ROOT.gSystem.Load("libTreeObjects.so")

def applyFakeRate( histo, f, e_f ):
	for i in range( histo.GetNbinsX() +1 ):
		binContent = histo.GetBinContent(i)
		histo.SetBinContent( i, histo.GetBinContent(i)*f)
		# sigma_{ef} = sqrt( ( e*e_f )**2 + ( e_e*f )**2 )
		histo.SetBinError( i, sqrt((binContent*e_f)**2 + (histo.GetBinError(i)*f)**2 ) )
	return histo

def closure( fileName, opts, scale ):
	##################################
	fakeRate = 0.0084
	fakeRateError = 0.0006 # stat

	# correct fake rate, if it is estimated with yutaros method
	fakeRateError = fakeRateError / (1-fakeRate)**2
	fakeRate = fakeRate / ( 1 - fakeRate )

	##################################

	# dataset name is from beginning till first '_'
	datasetAffix = re.match(".*slim([^_]*)_.*", fileName ).groups()[0]

	label, unit, binning = readAxisConf( opts.plot )

	commonCut = "photon[0].pt>80 && @photon.size() && met>100"

	gTree = readTree( fileName, "photonTree" ).CopyTree( commonCut )
	eTree = readTree( fileName, "photonElectronTree" ).CopyTree( commonCut )

	if opts.plot == "nVertex":
		nBins = 6
		firstBin = 3
		lastBin = 35
	else:
		nBins = 20
		firstBin = None
		lastBin = None

	recE = getHisto( eTree, opts.plot, color=2, weight="1", nBins=nBins, firstBin=firstBin, lastBin=lastBin )
	recE.SetFillColor( recE.GetLineColor() )
	recE.SetFillStyle(3254)
	recE = applyFakeRate( recE, fakeRate, fakeRateError )

	gamma = getHisto( gTree, opts.plot, color=1, weight="1", cut="!photon[0].isGenPhoton()", nBins=nBins, firstBin=firstBin, lastBin=lastBin )

	for h in [gamma, recE ]:
		h.SetMarkerSize(0)
		h.Scale( scale )

	if opts.alternativeStatistics:
		#error_hist = extractHisto( Dataset( fileName, "photonTree", "weight*(1)","name", 1), opts.plot )
		scale_for_points = 3.66 # mean weight for w-jets photonTree
		for bin in range(gamma.GetNbinsX()+1):
			#gamma.SetBinError( bin, error_hist.GetBinError( bin ) )
			if not gamma.GetBinContent(bin) and bin>10:
				gamma.SetBinError(bin,1.14*scale_for_points/gamma.GetBinWidth(bin))

	multihisto = Multihisto()
	multihisto.leg.SetHeader( datasetAffix )
	multihisto.addHisto( recE, "e#upoint#tildef_{e#rightarrow#gamma}", draw="e2" )
	multihisto.addHisto( gamma, "#gamma", draw="e0 hist" )

	can = ROOT.TCanvas()

	hPad = ROOT.TPad("hPad", "Histogram", 0, 0.2, 1, 1)
	hPad.cd()
	multihisto.Draw()

	ratioPad = ROOT.TPad("ratioPad", "Ratio", 0, 0, 1, 0.2)
	ratioPad.cd()
	ratioPad.SetLogy(0)
	ratioGraph = ratios.RatioGraph(gamma, recE)
	ratioGraph.draw(ROOT.gPad, yMin=0.5, yMax=1.5, adaptiveBinning=False, errors="yx")
	ratioGraph.hAxis.SetYTitle( "#gamma/(e#upoint#tilde{f})")

	if opts.alternativeStatistics:
		for point in range( ratioGraph.graph.GetN() ):
			if not ratioGraph.graph.GetErrorY(point):
				# read out point+1, since histograms start with bin 1
				ratioGraph.graph.SetPointEYhigh( point, ratioGraph.numerator.GetBinError(point+11) / ratioGraph.denominator.GetBinContent(point+11) )

	ratioGraph.graph.Draw("same p e1")

	# draw systematic uncertanty in ratio:
	syst = recE.Clone( "hist_ratio_syst" )
	for bin in range( syst.GetNbinsX()+1 ):
		if syst.GetBinContent(bin):
			syst.SetBinError( bin, syst.GetBinError(bin) / syst.GetBinContent(bin) )
		syst.SetBinContent( bin, 1 )
	syst.Draw("same e2")

	can.cd()
	hPad.Draw()
	ratioPad.Draw()
	can.SaveAs("plots/%s_%s_%s.pdf"%(datasetAffix,opts.plot.replace(".",""),opts.save))

	# avoid segmentation violation due to python garbage collector
	ROOT.SetOwnership(hPad, False)
	ROOT.SetOwnership(ratioPad, False)


if __name__ == "__main__":
	arguments = argparse.ArgumentParser( description="Simple EWK" )
	arguments.add_argument( "--plot", default="met" )
	arguments.add_argument( "--alternativeStatistics", action='store_true')
	arguments.add_argument( "--input", default=["EWK_V01.12_tree.root"], nargs="+" )
	arguments.add_argument( "--save", default="new" )
	opts = arguments.parse_args()

	integratedLumi = 19300 #pb

	datasetConfigName = "dataset.cfg"
	datasetConf = ConfigParser.SafeConfigParser()
	datasetConf.read( datasetConfigName )

	for inName in opts.input:
		shortName = None
		for configName in datasetConf.sections():
			if inName.count( configName ):
				shortName = configName
				crosssection = datasetConf.getfloat( configName, "crosssection" )
		if not shortName:
			print "No configuration for input file {} defined in '{}'".format(
					inName, datasetConfigName )
			continue
		eventHisto = readHisto( inName )
		nGen = eventHisto.GetBinContent(1)



		closure( inName, opts, integratedLumi*crosssection/nGen )

