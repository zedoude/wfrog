## Copyright 2009 Laurent Bovet <laurent.bovet@windmaster.ch>
##                Jordi Puigsegur <jordi.puigsegur@gmail.com>
##
##  This file is part of wfrog
##
##  wfrog is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import yaml
import renderer
import datasource
import optparse
import sys
import os
import time
from threading import Thread
import inspect
import logging

class YamlConfigurer(object):
    """Returns a configuration read from a yaml file (default to wfrender.yaml in cwd)"""

    DEFAULT_CONFIG = "config/wfrender.yaml"

    watcher_running = False
    extensions = {}
    logger=logging.getLogger("config")

    def __init__(self, opt_parser):
        opt_parser.add_option("-f", "--file", dest="config", default=self.DEFAULT_CONFIG,
                  help="Configuration file (in yaml). Defaults to '" + self.DEFAULT_CONFIG + "'", metavar="CONFIG_FILE")
        opt_parser.add_option("-L", action="store_true", dest="help_list", help="Gives the list of possible config !elements in the yaml config file")
        opt_parser.add_option("-H", dest="help_element", metavar="ELEMENT", help="Gives help about a config !element")
        opt_parser.add_option("-e", "--extensions", dest="extension_names", metavar="MODULE1,MODULE2,...", help="Comma-separated list of modules containing custom data sources, renderers or new types of application elements")
        opt_parser.add_option("-r", "--reload-config", action="store_true", dest="reload_config", help="Reloads the yaml configuration if it changes during execution")
        opt_parser.add_option("-R", "--reload-modules", action="store_true", dest="reload_mod", help="Reloads the data source, renderer and extension modules if they change during execution")
        opt_parser.add_option("-q", "--quiet", action="store_true", dest="quiet", help="Issues only errors, nothing else")
        opt_parser.add_option("-d", "--debug", action="store_true", dest="debug", help="Issues all debug messages")

    def configure(self, engine, options, args):
        if not options.quiet:
            if options.debug:
                level=logging.DEBUG
            else:
                level=logging.INFO
            logging.basicConfig(level=level, format="%(levelname)s [%(name)s] %(message)s")

        if options.extension_names:
            for ext in options.extension_names.split(","):
                self.logger.debug("Loading extension module '"+ext+"'")
                self.extensions[ext]=__import__(ext)
        if options.help_list:
            print "\nElements you can use in the yaml config file:\n"
            print "Renderers"
            print "---------\n"
            self.print_help(renderer)
            print "Data Sources"
            print "------------\n"
            self.print_help(data)
            if options.extension_names:
                print "Extensions"
                print "----------\n"
                for ext in self.extensions:
                    print "[" + ext + "]"
                    print
                    self.print_help(self.extensions[ext])
            print "Use option -H ELEMENT for help on a particular element"
            sys.exit()
        if options.help_element:
            element = options.help_element
            if element[0] is not '!':
                element = '!' + element
            desc = self.get_help_desc(renderer)
            if desc.has_key(element):
                print
                print element
                print "    " + desc[element]
                print
            else:
                print "Element "+element+" not found or not documented"
            sys.exit()
        config = yaml.load( file(options.config, "r") )

        engine.root_renderer = config["renderer"]
        engine.initial_context = config["context"]

        if options.reload_config and not self.watcher_running:
            self.watcher_running = True
            engine.daemon = True
            FileWatcher(options.config, self, engine, options, args).start()

    def print_help(self, module):
        desc = self.get_help_desc(module, summary=True)
        sorted = desc.keys()
        sorted.sort()
        for k in sorted:
            print k
            print "    " + desc[k]
            print

    def get_help_desc(self, module, summary=False):
        self.logger.debug("Getting info on module '"+module.__name__+"'")
        elements = inspect.getmembers(module, lambda l : inspect.isclass(l) and yaml.YAMLObject in inspect.getmro(l))
        desc={}
        for element in elements:
            self.logger.debug("Getting doc of "+element[0])
            # Gets the documentation of the first superclass
            fulldoc=inspect.getmro(element[1])[1].__doc__
            firstline=fulldoc.split(".")[0]
            self.logger.debug(firstline)
            if summary:
                desc[element[1].yaml_tag] = firstline
            else:
                desc[element[1].yaml_tag] = fulldoc
        return desc

class FileWatcher(Thread):

    logger = logging.getLogger("config.watcher")

    def __init__(self,filename,configurer,engine,*args,**kwargs):
        Thread.__init__(self)
        self.filename=filename
        self.configurer=configurer
        self.engine=engine
        self.args=args
        self.kwargs=kwargs

    def run(self):
        config_this_modified = config_last_modified = os.stat(self.filename).st_mtime
        renderer_this_modified = renderer_last_modified = last_mod('renderer')
        while self.engine.daemon:
            time.sleep(1)

            config_last_modified = os.stat(self.filename).st_mtime
            if config_last_modified > config_this_modified:
                self.logger.debug("Changed detected on "+self.filename)
                self.reconfigure()
                config_this_modified = config_last_modified

            renderer_last_modified = last_mod('renderer')
            if renderer_last_modified > renderer_this_modified:
                print "Reloading renderers."
                reload_modules('renderer')
                self.reconfigure()
                renderer_this_modified = last_mod('renderer')

    def reconfigure(self):
        self.logger.info("Reconfiguring engine...")
        if self.engine.root_renderer.close:
            self.engine.root_renderer.close()
        self.configurer.configure(self.engine,*self.args, **self.kwargs)

def reload_modules(parent):
    logger = logging.getLogger("config.loader")
    logger.info("Reloading module '"+parent+"' and direct sub-modules...")
    parent = __import__(parent)
    for m in inspect.getmembers(parent, lambda l: inspect.ismodule(l)):
        logger.debug("Reloading module '"+m[0]+"'.")
        reload(m[1])
    logger.debug("Reloading module '"+parent.__name__+"'.")
    reload(parent)

def last_mod(parent):
    logger = logging.getLogger("config.loader")
    max=0
    for fname in os.listdir(parent):
        mod = os.stat(parent+'/'+fname).st_mtime
        if(mod > max):
            max = mod
    return max

