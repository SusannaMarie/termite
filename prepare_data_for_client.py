#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import ConfigParser
import logging

from api_utils import ModelAPI, SaliencyAPI, SeriationAPI, ClientAPI

class PrepareDataForClient( object ):
	"""
	Reformats data necessary for client to run. 
	
	Extracts a subset of the complete term list and term-topic matrix and writes
	the subset to a separate file. Also, generates JSON file that merges/packages term
	information with the actual term.
	
	Input is term-topic probability distribution and term information, stored in 4 files:
	    'term-topic-matrix.txt' contains the entries of the matrix.
	    'term-index.txt' contains the terms corresponding to the rows of the matrix.
	    'topic-index.txt' contains the topic labels corresponding to the columns of the matrix.
	    'term-info.txt' contains information about individual terms.
	
	Output is a subset of terms and matrix, as well as the term subset's information.
	Number of files created or copied: 5
		'submatrix-term-index.txt'
	    'submatrix-topic-index.txt'
	    'submatrix-term-topic.txt'
	    'term-info.json'
	    'term-info.txt'
	"""
	
	def __init__( self, logging_level ):
		self.logger = logging.getLogger( 'PrepareDataForClient' )
		self.logger.setLevel( logging_level )
		handler = logging.StreamHandler( sys.stderr )
		handler.setLevel( logging_level )
		self.logger.addHandler( handler )
	
	def execute( self, data_path ):
		
		assert data_path is not None
		
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Preparing data for client...'                                                     )
		self.logger.info( '    data_path = %s', data_path                                                    )
		
		self.logger.info( 'Connecting to data...' )
		self.model = ModelAPI( data_path )
		self.saliency = SaliencyAPI( data_path )
		self.seriation = SeriationAPI( data_path )
		self.client = ClientAPI( data_path )
		
		self.logger.info( 'Reading data from disk...' )
		self.model.read()
		self.saliency.read()
		self.seriation.read()
		
		self.logger.info( 'Merging term information...' )
		self.mergeTermInfo()
		
		self.logger.info( 'Extracting term-topic submatrix...' )
		self.extractTermTopicSubmatrix()
		
		self.logger.info( 'Writing data to disk...' )
		self.client.write()
	
	def mergeTermInfo( self ):
		# Build lookup tables
		term_orderings = { term: value for value, term in enumerate( self.seriation.term_ordering ) }
		term_iter_indexes = { term: value for value, term in enumerate( self.seriation.term_iter_index ) }
		term_freqs = { d['term']: d['frequency'] for d in self.saliency.term_info }
		term_saliencies = { d['term']: d['saliency'] for d in self.saliency.term_info }
		
		# Merge into a single object
		term_info = []
		for term in term_orderings:
			ordering = term_orderings[ term ]
			ranking = term_iter_indexes[ term ]
			frequency = term_freqs[ term ]
			saliency = term_saliencies[ term ]
			term_info.append( {
				"term" : term,
				"ranking" : ranking,
				"ordering" : ordering,
				"frequency" : frequency,
				"saliency" : saliency
			} )
			
		# Write to client API
		self.client.term_info = term_info
			
	def extractTermTopicSubmatrix( self ):
		topic_index = self.model.topic_index
		term_index = self.model.term_index
		term_topic_matrix = self.model.term_topic_matrix
		term_ordering = self.seriation.term_ordering
		
		term_topic_submatrix = []
		term_subindex = []
		for term in term_ordering:
			if term in term_index:
				index = term_index.index( term )
				term_topic_submatrix.append( term_topic_matrix[ index ] )
				term_subindex.append( term )
			else:
				self.logger.info( 'ERROR: Term (%s) does not appear in the list of seriated terms', term )
		
		self.client.term_index = term_subindex
		self.client.topic_index = topic_index
		self.client.term_topic_matrix = term_topic_submatrix

def main():
	parser = argparse.ArgumentParser( description = 'Prepare data for client.' )
	parser.add_argument( 'config_file', type = str, default = None    , help = 'Path of Termite configuration file.' )
	parser.add_argument( '--data-path', type = str, dest = 'data_path', help = 'Override data path.'                 )
	parser.add_argument( '--logging'  , type = int, dest = 'logging'  , help = 'Override logging level.'             )
	args = parser.parse_args()
	
	args = parser.parse_args()
	
	data_path = None
	logging_level = 20
	
	# Read in default values from the configuration file
	if args.config_file is not None:
		config = ConfigParser.RawConfigParser()
		config.read( args.config_file )
		if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'path' ):
			data_path = config.get( 'Termite', 'path' )
		if config.has_section( 'Misc' ) and config.has_option( 'Misc', 'logging' ):
			logging_level = config.getint( 'Misc', 'logging' )
	
	# Read in user-specifiec values from the program arguments
	if args.data_path is not None:
		data_path = args.data_path
	if args.logging is not None:
		logging_level = args.logging
	
	PrepareDataForClient( logging_level ).execute( data_path )

if __name__ == '__main__':
	main()
