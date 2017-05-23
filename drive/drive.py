'''
What:
  This file can be used to drive a Sparrow automatically.
  It runs forever, with the option of alternating, visiting all the sites in a site list between sparrow and chromiumlike modes

How:
  You will need to pip install the libraries below
  And put Chromedriver (https://sites.google.com/a/chromium.org/chromedriver/downloads) on your PATH

  The json config file contains all information for the drive.py

  Usage: python drive.py -c json_config_file

  config.json ex:

  {
    "sparrow_location": "/Applications/Sparrow.app/Contents/MacOS/Sparrow",               # If present all other configs ignored
    "sitelist_file": "http://bizzybyster.github.io/drive/configs/ear/sitelist.txt",       # If local file, path relative to drive.py location
    "log_file": "drive_log",
    "log_level": "info",
    "alternate_sparrow_chromiumlike": "true",
    "test_label_prefix": "ear_drive_remote_config_test",
    "sparrow_switches": [
        "--enable-crash-upload",
        "--request-beer-ack",
        "--omaha-server-url=https://omaha.overnight.ihs.viasat.io"
        ],
    "chromium_version": "56.0.2924.11689",
    "save_screenshots": "true"
   }

  Default sparrow paths:
      OSX: "/Applications/Sparrow.app/Contents/MacOS/Sparrow"
      WIN: "C:\Users\Me\AppData\Local\ViaSat\Sparrow\Application\Sparrow.exe"
'''

import time
import urllib2
import datetime
import os, sys, shutil
from selenium import webdriver
from selenium.webdriver.chrome import service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
import argparse
import logging
import json
import subprocess

try:
    import selenium_methods
except:
    # building pythonpath
    sep = os.sep
    path = sep.join(os.path.realpath(__file__).split(sep)[0:-2])
    print(path)
    sys.path.append(path)
    from lift_acceptance_tests.steps import selenium_methods

USR_AGENT_OSX = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36"
USR_AGENT_WIN = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36"
USR_AGENT_LINUX = "??"

class SparrowDriver(object):

    def __init__(self):
        self.stats = {}
        self.get_command_line()
        
        if os.path.exists(self.json_config_file) is False:
            print("Error, json config file not found")
            sys.exit(1)

        with open(self.json_config_file) as fl:
            json_data = json.load(fl)

        # Check for a remote config file
        self.remote_config_file = json_data.get('remote_config_file_location')
        if self.remote_config_file:
            print "Using remote config file at: %s\n" % self.remote_config_file
            json_data = json.load(urllib2.urlopen(self.remote_config_file))

        self.service = service.Service('chromedriver')
        
        # Read the config file; set attributes
        self.json_config_parser(json_data)
        
        logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename=self.logging_file, level=self.logging_level)

    def get_command_line(self):
        parser = argparse.ArgumentParser()            
        parser.add_argument('-c', '--config', required=True, help='path to the configuration directory, which contains json config')
        
        args = parser.parse_args()
            
        self.json_config_file = args.config

    def json_config_parser(self, json_data):
        '''Parses the config.json file and sets attributes that will eventually be cmd switches and options passed to selenium'''
            
        sparrow_location = json_data.get('sparrow_location')
        if (sparrow_location is not None) and \
            (os.path.exists(sparrow_location) is True):
            self.binary_location = sparrow_location
        else:
            print "Sparrow not found at the location: %s" % sparrow_location
            sys.exit(1)

        # Discover chromium version and set user agent for use in chromiumlike mode
        self.platform = sys.platform
        if 'darwin' in self.platform:
            p = subprocess.Popen([self.binary_location, '--version'], stdout=subprocess.PIPE)
            out, err = p.communicate()
            self.chromium_version = out.strip().split()[1]
            self.user_agent = USR_AGENT_OSX % self.chromium_version

        elif 'win' in self.platform:
            cmd = ['wmic datafile where name=%s get Version /value' % self.binary_location]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            out, err = p.communicate()
            self.chromium_version = out.split('=')[1]
            self.user_agent = USR_AGENT_WIN % self.chromium_version

        print "Running chromium_version: %s" % self.chromium_version

        self.sitelist_file = json_data.get('sitelist_file')
        if self.sitelist_file.lower().startswith('http'):
            self.sitelist = urllib2.urlopen(self.sitelist_file).read().split("\n")

        elif os.path.exists(self.sitelist_file):
            self.sitelist = open(self.sitelist_file).read().split('\n')

        else:
            print("sitelist: %s not found, exiting" % self.sitelist_file)
            print("Please modify the sitelist entry in %s" % self.json_config_file)
            sys.exit(1)
        print "Using sitelist: %s" % self.sitelist_file

        self.test_label_prefix = json_data.get('test_label_prefix')
        self.sparrow_switches = json_data.get('sparrow_switches')

        self.alternate_sparrow_chromium = True if json_data.get('alternate_sparrow_chromiumlike', 'false').lower() == 'true' else False
        self.alternate_warm_cold_cache = True if json_data.get('alternate_warm_cold_cache', 'false').lower() == 'true' else False

        if self.alternate_sparrow_chromium:
            self.chromiumlike_user_data_dir = os.path.dirname(os.path.realpath(__file__)) + '/chromiumlike_user_data'
        self.sparrow_user_data_dir = os.path.dirname(os.path.realpath(__file__)) + '/sparrow_user_data'

        self.save_screenshots = True if json_data.get('save_screenshots', 'false').lower() == 'true' else False
            
        self.logging_file = json_data.get('log_file', 'drive_log')
        log_level = json_data.get('log_level', 'info')

        if log_level.lower() == 'debug':
            self.logging_level = logging.DEBUG
        if log_level.lower() == 'warning':
            self.logging_level = logging.WARNING
        if log_level.lower() == 'info':
            self.logging_level = logging.INFO
        if log_level.lower() == 'error':
            self.logging_level = logging.ERROR

    def add_options(self, chromiumlike, cache_state):
        ''' Sets a bunch of cmd switches and options passed to selenium'''

        mode = "chromiumlike" if chromiumlike else "sparrow"

        driver_options = Options()

        # Field Trial
        if chromiumlike:
            logging.info("Starting a pass through the list in chromiumlike mode")
            driver_options.add_argument('--sparrow-force-fieldtrial=chromiumlike')
            driver_options.add_argument('--user-agent=%s' % self.user_agent)
            driver_options.add_argument('--user-data-dir=%s' % self.chromiumlike_user_data_dir)

        else:
            logging.info("Starting a pass through the list in sparrow mode")
            driver_options.add_argument('--sparrow-force-fieldtrial')
            driver_options.add_argument('--user-data-dir=%s' % self.sparrow_user_data_dir)

        # Passed from config file
        for switch in self.sparrow_switches:
            driver_options.add_argument(switch)
            logging.debug("Adding sparrow switch: %s" % switch)

        # Test label
        test_start_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        test_label_entry = "--beer-test-label=%s-%s-%s-%s-%s-%s" % (self.test_label_prefix, self.chromium_version, 
                                                                    self.platform, mode, cache_state, test_start_time)
        driver_options.add_argument(test_label_entry)
        print test_label_entry + "\n"

        driver_options.binary_location = self.binary_location
        driver_options.to_capabilities()['loggingPrefs'] = { 'browser':'ALL' }

        return driver_options

    def visit_sites(self, chromiumlike, cache_state):

        driver_options = self.add_options(chromiumlike, cache_state)

        # launch sparrow and initial tabs
        remote, beerstatus_tab, content_tab = selenium_methods.start_remote(self.service.service_url, driver_options)

        # Used to verify that the current beer is unique and new
        beer_status_dict = {}
        for site in self.sitelist:
            beer_status_dict[site] = None
            
        self.stats['sites'] = 0
        for site in self.sitelist:
            if not site:
                continue

            print '\n'+site,   # comma is intentional here as it suppresses the /n
            logging.info(site)
            
            remote.switch_to_window(content_tab)
            nav_start_time = time.time()
            
            try:
                selenium_methods.load_on_hover(site, remote)
                
                try:
                    title = remote.find_element_by_tag_name('title').get_property('text')
                    title.decode('ascii')
                    
                    # Screenshot handling if configured
                    # Save screenshot only if title present to prevent hang in some cases
                    if self.save_screenshots:
                        if title != 'No title':
                            screenshot_path = './screenshots/' + site.replace(':','_').replace('/', '_') + '.png'
                            remote.save_screenshot(screenshot_path)
                       
                except UnicodeDecodeError:
                    title = 'title is not ascii-encoded'
                    logging.warning(title)
                except UnicodeEncodeError:
                    title = 'title is not ascii-encoded'
                    logging.warning(title)
                except NoSuchElementException:
                    title = 'no title because no such element'
                    logging.warning(title)
                except WebDriverException:
                    title = 'no title b/c of exception'
                    logging.warning(title)

                remote.switch_to_window(beerstatus_tab)

            except TimeoutException as e:
                logging.warning("Selenium exception caught: %s" % str(e))
                if 'timeout_errors' not in self.stats:
                    self.stats['timeout_errors'] = 0
                self.stats['timeout_errors'] += 1
                remote, beerstatus_tab, content_tab = selenium_methods.start_remote(self.service.service_url, driver_options)
                continue
            except Exception as e:
                print("Selenium exception caught: %s" % str(e))
                logging.error("Selenium exception caught: %s" % str(e))
                if 'driver_exceptions' not in self.stats:
                    self.stats['driver_exceptions'] = 0
                self.stats['driver_exceptions'] += 1
                remote, beerstatus_tab, content_tab = selenium_methods.start_remote(self.service.service_url, driver_options)
                continue

            self.stats['sites'] += 1
            if 'total' not in self.stats:
                self.stats['total'] = 0
            self.stats['total'] += 1
            nav_done_time = time.time()
            self.stats['time'] = nav_done_time-nav_start_time

            # Wait up to 40 seconds for beer ack
            num_tries = 40
            trys = 0
            while (trys < num_tries):
                remote.get("sparrow://beerstatus")
                if selenium_methods.check_beer_status(site, beer_status_dict, remote):
                    break

                trys += 1
                time.sleep(1)

            self.stats['waiting_for_ack'] = time.time()-nav_done_time
            logging.info('\'%s\', stats: %s' % (title, str(self.stats)))

            if trys == num_tries:
                print("No beer ack recieved for %s" % site)

        remote.quit()

    def run_service(self):
        
        self.service.start()
        
        self.stats['total'] = 0

        if self.save_screenshots:
            if not os.path.exists('./screenshots'):
                os.mkdir( './screenshots', 0755 );

        # Loop forever togging between sparrow and chromiumlike modes if alternate_sparrow_chromium = True
        # Alternate cold and warm cache between runs through the list
        clear_cache = True
        chromiumlike_mode = False
        mode = 'sparrow'
        while True:
            if clear_cache:
                user_data = self.chromiumlike_user_data_dir if chromiumlike_mode else self.sparrow_user_data_dir
                print "Removing user data dir: %s now.." % user_data
                shutil.rmtree(user_data, ignore_errors=True)

                print "Starting cold cache run with %s now.." % mode
                self.visit_sites(chromiumlike_mode, "cold")

                if self.alternate_sparrow_chromium:
                    chromiumlike_mode = not chromiumlike_mode
                    mode = "chromiumlike" if chromiumlike_mode else "sparrow"

                    user_data = self.chromiumlike_user_data_dir if chromiumlike_mode else self.sparrow_user_data_dir
                    print "Removing user data dir: %s now.." % user_data
                    shutil.rmtree(user_data, ignore_errors=True)

                    print "Starting cold cache run with %s now.." % mode
                    self.visit_sites(chromiumlike_mode, "cold")

            else:
                print "Starting warm cache run with %s now.." % mode
                self.visit_sites(chromiumlike_mode, "warm")

                if self.alternate_sparrow_chromium:
                    chromiumlike_mode = not chromiumlike_mode
                    mode = "chromiumlike" if chromiumlike_mode else "sparrow"

                    print "Starting warm cache run with %s now.." % mode
                    self.visit_sites(chromiumlike_mode, "warm")

            clear_cache = not clear_cache if self.alternate_warm_cold_cache else False
            if self.alternate_sparrow_chromium:
                chromiumlike_mode = not chromiumlike_mode
                mode = "chromiumlike" if chromiumlike_mode else "sparrow"

    #################################

            # If remote config, check the file for any changes 
            if self.remote_config_file:
                message_str = "Loading remote config file again from %s" % self.remote_config_file
                print message_str
                logging.info(message_str)
                try:
                    json_data = json.load(urllib2.urlopen(self.remote_config_file))
                    # Set new config values to be run till next iteration
                    self.json_config_parser(json_data)
                    if not self.alternate_sparrow_chromium:
                        chromiumlike_mode = False
                        mode = "sparrow"
                except:
                    message_str = "Failed to load remote config at %s." % self.remote_config_file
                    print message_str
                    logging.info(message_str)

        
    def clean_chromedriver_process(self):
        '''
        Will kill chromedriver process if exists
        otherwise running process might cause problems 
        Not supported under cygwin, so need to put it in try /except block
        '''
        
        import psutil
        
        for proc in psutil.process_iter():
            if proc.name() == 'chromedriver.exe':
                proc.kill()

if __name__ == '__main__':
    sdrv = SparrowDriver()
    
    try:
        sdrv.clean_chromedriver_process()
    except:
        pass
    sdrv.run_service()
    
