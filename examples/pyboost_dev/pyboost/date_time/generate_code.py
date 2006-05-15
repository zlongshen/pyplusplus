#! /usr/bin/python
# Copyright 2004 Roman Yakovenko.
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)


import os
import sys
import time
import shutil
import date_time_settings
import customization_data
from pygccxml import parser
from pygccxml import declarations
from pyplusplus import module_builder

class code_generator_t(object):    
    def __init__(self):
        self.__file = os.path.join( date_time_settings.date_time_pypp_include, 'date_time.pypp.hpp' )                        

    def _create_xml_file( self ):
        #On windows I have some problems to compile boost.date_time
        #library, so I use xml files generated on linux
        config = parser.config_t( gccxml_path=date_time_settings.gccxml.executable
                                  , include_paths=[date_time_settings.boost.include]
                                  , define_symbols=date_time_settings.defined_symbols
                                  , undefine_symbols=date_time_settings.undefined_symbols )

        reader = parser.source_reader_t( config )
        destination = os.path.join( date_time_settings.date_time_pypp_include, 'date_time.pypp.xml' )
        if sys.platform == 'linux2':
            reader.create_xml_file( self.__file, destination )
        return destination
    
    def create_module_builder(self):
        date_time_xml_file = self._create_xml_file()
        mb = module_builder.module_builder_t( [ parser.create_gccxml_fc( date_time_xml_file ) ]
                                              , gccxml_path=date_time_settings.gccxml.executable
                                              , include_paths=[date_time_settings.boost.include]
                                              , define_symbols=date_time_settings.defined_symbols
                                              , undefine_symbols=date_time_settings.undefined_symbols
                                              , optimize_queries=False)
        if sys.platform == 'win32':
            linux_name = "time_duration<boost::posix_time::time_duration,boost::date_time::time_resolution_traits<boost::date_time::time_resolution_traits_adapted64_impl, micro, 1000000, 6, int> >"
            win_name = "time_duration<boost::posix_time::time_duration,boost::date_time::time_resolution_traits<boost::date_time::time_resolution_traits_adapted64_impl, micro, 1000000, 6, long int> >"
            time_duration_impl = mb.class_( linux_name )            
            #small price for generating code from xml and not from sources
            time_duration_impl.name = win_name

        for f_decl in  mb.free_functions():
            f_decl.alias = f_decl.name
            f_decl.name = f_decl.demangled_name
            #f_decl.create_with_signature = True
            
        mb.run_query_optimizer()

        for name, alias in customization_data.name2alias.items():
            decl = mb.class_( name )
            decl.alias = alias
            if isinstance( decl, declarations.class_t ):
                decl.wrapper_alias = alias + '_wrapper'
        
        return mb
    
    def filter_declarations(self, mb ):
        mb.global_ns.exclude()
        mb.global_ns.namespace( 'pyplusplus', recursive=False ).include()
        boost_ns = mb.global_ns.namespace( 'boost', recursive=False )
        boost_ns.namespace( 'posix_time', recursive=False ).include()
        boost_ns.namespace( 'date_time', recursive=False ).include()
        boost_ns.namespace( 'gregorian', recursive=False ).include()
        boost_ns.namespace( 'local_time', recursive=False ).include()
        boost_ns.classes( lambda decl: decl.name.startswith( 'constrained_value<' ) ).include()
                
        for name in [ 'month_str_to_ushort', 'from_stream_type', 'parse_date' ]:
            boost_ns.calldefs( lambda decl: decl.name.startswith( name ) ).exclude()

        to_be_removed = [ 'c_time'
                          , 'duration_traits_long'
                          , 'duration_traits_adapted'
                          , 'posix_time_system_config' #TODO find out link bug
                          , 'millisec_posix_time_system_config' ]
        boost_ns.classes( lambda decl: decl.name in to_be_removed ).exclude()
        
        starts_with = [ 'time_resolution_traits<'
                        , 'counted_time_rep<'
                        , 'date_facet<'
                        , 'period_formatter<'
                        , 'date_generator_formatter<'
                        , 'special_values_formatter<' ]       
        for name in starts_with:
            boost_ns.classes( lambda decl: decl.name.startswith( name ) ).exclude()
                
        ends_with = [ '_impl', '_config' ]
        for name in ends_with:
            boost_ns.classes( lambda decl: decl.name.endswith( name ) ).exclude()        

        boost_ns.classes( lambda decl: decl.alias.endswith( 'formatter' ) ).exclude()        

        #boost.date_time has problem to create local_[micro]sec_clock
        #variable, it has nothing to do with pyplusplus
        empty_classes = ['local_microsec_clock', 'local_sec_clock']
        for alias in empty_classes:
            class_ = boost_ns.class_( lambda decl: decl.alias == alias )
            class_.exclude()
            class_.ignore = False
        
        for alias in [ 'microsec_clock', 'second_clock' ]:
            class_ = boost_ns.class_( lambda decl: decl.alias == alias )
            class_.calldefs().create_with_signature = True
            
        tdi = mb.class_( lambda decl: decl.alias == 'time_duration_impl' )
        tdi_init = tdi.constructor( arg_types=[None, None, None, None], recursive=False)
        tdi_init.ignore=True
        
    def add_code( self, mb ):
        as_number_template = 'def( "as_number", &%(class_def)s::operator %(class_def)s::value_type, bp::default_call_policies() )'
        
        classes = mb.classes()
        classes.always_expose_using_scope = True #better error reporting from compiler

        classes = mb.classes(lambda decl: decl.alias != 'local_date_time' )
        classes.redefine_operators = True #redefine all operators found in base classes
        
        classes = mb.classes(lambda decl: decl.name.startswith('constrained_value<') )
        for cls in classes:
            cls.add_code( as_number_template % { 'class_def' : declarations.full_name( cls ) } )

        classes = mb.classes(lambda decl: decl.alias in [ 'date_duration', 'time_duration' ] )
        for operator in [ '>', '>=', '<=', '<', '+', '-' ]:
            classes.add_code( 'def( bp::self %s  bp::self )' % operator )

        ptime = mb.class_( lambda decl: decl.alias == 'ptime' )
        for operator in [ '>', '>=', '<=', '<', '-' ]:
            ptime.add_code( 'def( bp::self %s  bp::self )' % operator )
                
    def beautify_code( self, mb ):
        extmodule = mb.code_creator
        extmodule.add_namespace_usage( 'boost' )
        extmodule.add_namespace_usage( 'boost::date_time' )
        for full_ns_name, alias in customization_data.ns_aliases.items():
            extmodule.add_namespace_alias( alias, full_ns_name )

    def customize_extmodule( self, mb ):
        extmodule = mb.code_creator
        #beautifying include code generation
        extmodule.license = customization_data.license
        extmodule.user_defined_directories.append( date_time_settings.boost.include )
        extmodule.user_defined_directories.append( date_time_settings.working_dir )
        extmodule.user_defined_directories.append( date_time_settings.generated_files_dir )
        extmodule.license = customization_data.license
        extmodule.precompiled_header = 'boost/python.hpp'
        mb.code_creator.replace_included_headers( customization_data.includes )
        self.beautify_code( mb )
        
    def write_files( self, mb ):
        mb.split_module( date_time_settings.generated_files_dir )
        shutil.copyfile( os.path.join( date_time_settings.date_time_pypp_include, 'date_time_wrapper.hpp' )
                         , os.path.join( date_time_settings.generated_files_dir, 'date_time_wrapper.hpp' ) )

    def create(self):
        start_time = time.clock()      
        mb = self.create_module_builder()
        self.filter_declarations(mb)
        self.add_code( mb )        
        
        mb.build_code_creator( date_time_settings.module_name )
        
        self.customize_extmodule( mb )
        self.write_files( mb )
        print 'time taken : ', time.clock() - start_time, ' seconds'

def export():
    cg = code_generator_t()
    cg.create()

if __name__ == '__main__':
    export()
    print 'done'
    
    
