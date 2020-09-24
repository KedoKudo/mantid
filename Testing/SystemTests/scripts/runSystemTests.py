#!/usr/bin/env python
# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
import argparse
import os
import sys
import time
from multiprocessing import Process, Array, Manager, Value, Lock

# Prevents erros in systemtests that use matplotlib directly
os.environ['MPLBACKEND'] = 'Agg'

#########################################################################
# Set up the command line options
#########################################################################

start_time = time.time()

THIS_MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_FRAMEWORK_LOC = os.path.realpath(os.path.join(THIS_MODULE_DIR, "..", "lib", "systemtests"))
DATA_DIRS_LIST_PATH = os.path.join(THIS_MODULE_DIR, "datasearch-directories.txt")
SAVE_DIR_LIST_PATH = os.path.join(THIS_MODULE_DIR, "defaultsave-directory.txt")


def kill_children(processes):
    for process in processes:
        process.terminate()
    # Exit with status 1 - NOT OK
    sys.exit(1)


def generate_list_of_tests(mtdconf, options):
    import systemtesting
    runner = systemtesting.TestRunner(executable=options.executable,
                                      # see InstallerTests.py for why lstrip is required
                                      exec_args=options.execargs.lstrip(),
                                      escape_quotes=True)

    test_manager = systemtesting.TestManager(test_loc=mtdconf.testDir,
                                             runner=runner,
                                             quiet=options.quiet,
                                             testsInclude=options.testsInclude,
                                             testsExclude=options.testsExclude,
                                             exclude_in_pr_builds=options.exclude_in_pr_builds,
                                             ignore_failed_imports=options.ignore_failed_imports)

    return test_manager.generateMasterTestList()


def run_tests(mtdconf, options, number_of_test_modules, files_required_by_test_module, data_file_lock_status,
              test_counts, test_list, test_stats, total_number_of_tests, maximum_name_length):
    import systemtesting
    if not options.dry_run:
        # Multi-core processes --------------
        # An array to hold the processes
        processes = []
        # A shared array to hold skipped and failed tests + status
        results_array = Array('i', [0] * (3 * options.ncores))
        # A manager to create a shared dict to store names of skipped and failed tests
        manager = Manager()
        # A shared dict to store names of skipped and failed tests
        status_dict = manager.dict()
        # A shared dict to store the global list of tests
        tests_dict = manager.dict()
        # A shared array with 0s and 1s to keep track of completed tests
        tests_lock = Array('i', [0] * number_of_test_modules)
        # A shared value to count the number of remaining test modules
        tests_left = Value('i', number_of_test_modules)
        # A shared value to count the number of completed tests
        tests_done = Value('i', 0)
        # A shared dict to store which data files are required by each test module
        required_files_dict = manager.dict()
        for key in files_required_by_test_module.keys():
            required_files_dict[key] = files_required_by_test_module[key]
        # A shared dict to store the locked status of each data file
        locked_files_dict = manager.dict()
        for key in data_file_lock_status.keys():
            locked_files_dict[key] = data_file_lock_status[key]

        # Store in reverse number of number of tests in each module into the shared dictionary
        reverse_sorted_dict = [(k, test_counts[k])
                               for k in sorted(test_counts, key=test_counts.get, reverse=True)]
        counter = 0
        for key, value in reverse_sorted_dict:
            tests_dict[str(counter)] = test_list[key]
            counter += 1
            if not options.quiet:
                print("Test module {} has {} tests:".format(key, value))
                for t in test_list[key]:
                    print(" - {}".format(t._fqtestname))
                print()

        # Define a lock
        lock = Lock()

        # Prepare ncores processes
        for ip in range(options.ncores):
            processes.append(
                Process(target=systemtesting.testThreadsLoop,
                        args=(mtdconf.testDir, mtdconf.saveDir, mtdconf.dataDir, options,
                              tests_dict, tests_lock, tests_left, results_array, status_dict,
                              total_number_of_tests, maximum_name_length, tests_done, ip, lock,
                              required_files_dict, locked_files_dict)))
        # Start and join processes
        exitcodes = []
        try:
            for p in processes:
                p.start()

            for p in processes:
                p.join()
                exitcodes.append(p.exitcode)

        except KeyboardInterrupt:
            print("Killed via KeyboardInterrupt")
            kill_children(processes)
        except Exception as e:
            print("Unexpected exception occured: {}".format(e))
            kill_children(processes)

        # test processes could have failed to even start the tests. In this case skip printing the results
        if systemtesting.TESTING_PROC_FAILURE_CODE in exitcodes:
            sys.exit("\nFailed to execute tests. See traceback for more details.")

        # Gather results
        skipped_tests = sum(results_array[:options.ncores]) + (test_stats[2] - test_stats[0])
        failed_tests = sum(results_array[options.ncores:2 * options.ncores])
        total_tests = test_stats[2]
        # Find minimum of status: if min == 0, then success is False
        success = bool(min(results_array[2 * options.ncores:3 * options.ncores]))
    else:
        print("Dry run requested. Skipping execution")

    return status_dict, skipped_tests, failed_tests, total_tests, success


def generate_and_run_tests(mtdconf, options):
    test_counts, test_list, test_stats, files_required_by_test_module, data_file_lock_status = \
        generate_list_of_tests(mtdconf, options)

    number_of_test_modules = len(test_list.keys())
    total_number_of_tests = test_stats[0]
    maximum_name_length = test_stats[1]

    status_dict, skipped_tests, failed_tests, total_tests, success = run_tests(mtdconf, options, number_of_test_modules,
                                                                               files_required_by_test_module,
                                                                               data_file_lock_status, test_counts,
                                                                               test_list, test_stats,
                                                                               total_number_of_tests,
                                                                               maximum_name_length)

    return test_list, status_dict, skipped_tests, failed_tests, total_tests, success


def run_all_tests(mtdconf, options, test_sub_directories):
    all_success = True
    all_tests = dict()
    all_statuses = dict()
    skipped_count = 0
    failed_count = 0
    total_test_count = 0

    # Generate and run system tests in all system test sub directories
    for sub_directory in test_sub_directories:
        # Set the sub directory of the next system tests to run
        mtdconf.setTestDirectory(sub_directory)

        # Generate a list of tests in the sub directory and run them
        test_list, status_dict, skipped_tests, failed_tests, total_tests, success = generate_and_run_tests(mtdconf,
                                                                                                           options)

        # Gather cumulative test statistics
        all_success = all_success and success
        all_tests.update(test_list)
        all_statuses.update(status_dict)
        skipped_count += skipped_tests
        failed_count += failed_tests
        total_test_count += total_tests

    return all_success, all_tests, all_statuses, skipped_count, failed_count, total_test_count


def main():
    info = [
        "This program will configure mantid run all of the system tests located in",
        "the 'tests/<sub_dir>' directory.",
        "This program will create a temporary 'Mantid.user.properties' file which",
        "it will rename to 'Mantid.user.properties.systest' upon completion. The",
        "current version of the code does not print to stdout while the test is",
        "running, so the impatient user may ^C to kill the process. In this case",
        "all of the tests that haven't been run will be marked as skipped in the", "full logs."
    ]

    parser = argparse.ArgumentParser(description=' '.join(info))
    parser.add_argument("--email", action="store_true", help="send an email with test status.")
    parser.add_argument(
        "-x",
        "--executable",
        dest="executable",
        help="The executable path used to run each test. Default is the sys.executable")
    parser.add_argument("-a",
                        "--exec-args",
                        dest="execargs",
                        help="Arguments passed to executable for each test Default=[]")
    parser.add_argument("--frameworkLoc",
                        help="location of the system test framework (default=%s)" %
                        DEFAULT_FRAMEWORK_LOC)
    parser.add_argument("--disablepropmake",
                        action="store_false",
                        dest="makeprop",
                        help="By default this will move your properties file out of the " +
                        "way and create a new one. This option turns off this behavior.")
    parser.add_argument(
        "-R",
        "--tests-regex",
        dest="testsInclude",
        help="String specifying which tests to run. Simply uses 'string in testname'.")
    parser.add_argument(
        "-E",
        "--excluderegex",
        dest="testsExclude",
        help="String specifying which tests to not run. Simply uses 'string in testname'.")
    loglevelChoices = ["error", "warning", "notice", "information", "debug"]
    parser.add_argument("-l",
                        "--loglevel",
                        dest="loglevel",
                        choices=loglevelChoices,
                        help="Set the log level for test running: [" + ', '.join(loglevelChoices) +
                        "]")
    parser.add_argument(
        "-j",
        "--parallel",
        dest="ncores",
        action="store",
        type=int,
        help="The number of instances to run in parallel, like the -j option in ctest. Default is 1."
    )
    parser.add_argument("-q",
                        "--quiet",
                        dest="quiet",
                        action="store_true",
                        help="Prints detailed log to terminal.")
    parser.add_argument(
        "-c",
        "--clean",
        dest="clean",
        action="store_true",
        help="Performs a cleanup of the data generated by the test suite (does not run the tests).")
    parser.add_argument("--output-on-failure",
                        dest="output_on_failure",
                        action="store_true",
                        help="Print full log for failed tests.")
    parser.add_argument('-N',
                        '--dry-run',
                        dest='dry_run',
                        action='store_true',
                        help='Do not run tests just print what would be run.')
    parser.add_argument("--showskipped",
                        dest="showskipped",
                        action="store_true",
                        help="List the skipped tests.")
    parser.add_argument("-d",
                        "--datapaths",
                        dest="datapaths",
                        help="A semicolon-separated list of directories to search for data")
    parser.add_argument("-s",
                        "--savedir",
                        dest="savedir",
                        help="A directory to use for the Mantid save path")
    parser.add_argument("--archivesearch",
                        dest="archivesearch",
                        action="store_true",
                        help="Turn on archive search for file finder.")
    parser.add_argument("--exclude-in-pull-requests",
                        dest="exclude_in_pr_builds",
                        action="store_true",
                        help="Skip tests that are not run in pull request builds")
    parser.add_argument("--ignore-failed-imports",
                        dest="ignore_failed_imports",
                        action="store_true",
                        help="Skip tests that do not import correctly rather raising an error.")
    parser.set_defaults(frameworkLoc=DEFAULT_FRAMEWORK_LOC,
                        executable=sys.executable,
                        makeprop=True,
                        loglevel="information",
                        ncores=1,
                        quiet=False,
                        output_on_failure=False,
                        clean=False)
    options = parser.parse_args()

    # import the system testing framework
    sys.path.append(options.frameworkLoc)
    import systemtesting

    # allow PythonInterface/test to be discoverable
    sys.path.append(systemtesting.FRAMEWORK_PYTHONINTERFACE_TEST_DIR)

    #########################################################################
    # Configure mantid
    #########################################################################

    # Parse files containing the search and save directories, unless otherwise given
    data_paths = options.datapaths
    if data_paths is None or data_paths == "":
        with open(DATA_DIRS_LIST_PATH, 'r') as f_handle:
            data_paths = f_handle.read().strip()

    save_dir = options.savedir
    if save_dir is None or save_dir == "":
        with open(SAVE_DIR_LIST_PATH, 'r') as f_handle:
            save_dir = f_handle.read().strip()

    # Configure properties file
    mtdconf = systemtesting.MantidFrameworkConfig(loglevel=options.loglevel,
                                                  data_dirs=data_paths,
                                                  save_dir=save_dir,
                                                  archivesearch=options.archivesearch)
    if options.makeprop:
        mtdconf.config()

    #########################################################################
    # Generate and run system tests in framework and qt sub directories
    #########################################################################

    # Print message if this is a cleanup run instead of a normal test run
    if options.clean:
        print("Performing cleanup run")

    # Cleanup any pre-existing XML reporter files
    entries = os.listdir(mtdconf.saveDir)
    for file in entries:
        if file.startswith('TEST-systemtests-') and file.endswith('.xml'):
            os.remove(os.path.join(mtdconf.saveDir, file))

    success, all_tests, status_dict, skipped_tests, failed_tests, total_tests = run_all_tests(mtdconf, options,
                                                                                              ["framework", "qt"])

    #########################################################################
    # Cleanup
    #########################################################################

    # Put the configuration back to its original state
    if options.makeprop:
        mtdconf.restoreconfig()

    end_time = time.time()
    total_runtime = time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))

    #########################################################################
    # Output summary to terminal
    #########################################################################
    if options.dry_run:
        print()
        print("Tests that would be executed:")
        for suites in all_tests.values():
            for suite in suites:
                print('  ' + suite.name)
    elif not options.clean:
        nwidth = 80
        banner = "#" * nwidth
        print('\n' + banner)
        print("Total runtime: " + total_runtime)

        if (skipped_tests > 0) and options.showskipped:
            print("\nSKIPPED:")
            for key in status_dict.keys():
                if status_dict[key] == 'skipped':
                    print(key)
        if failed_tests > 0:
            print("\nFAILED:")
            for key in status_dict.keys():
                if status_dict[key] == 'failed':
                    print(key)

        # Report global statistics on tests
        print()
        if skipped_tests == total_tests:
            print("All tests were skipped")
            success = False  # fail if everything was skipped
        else:
            percent = 1. - float(failed_tests) / float(total_tests - skipped_tests)
            percent = int(100. * percent)
            print("%d%s tests passed, %d tests failed out of %d (%d skipped)" %
                  (percent, '%', failed_tests, (total_tests - skipped_tests), skipped_tests))
        print('All tests passed? ' + str(success))
        print(banner)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
