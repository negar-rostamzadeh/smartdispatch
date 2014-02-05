#!/usr/bin/env python
import os, sys
import argparse
import datetime
import numpy as np
from subprocess import check_output

def main():
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--queue', required=False, default='qwork@mp2', help='Queue used (ex: qwork@mp2, qfat256@mp2, qfat512@mp2)')
    parser.add_argument('-t', '--time', required=False, default='5:00:00:00', help='Time we need for the jobs')
    parser.add_argument('-n', '--nbCore', required=False, help='Set the number of core by nodes')
    parser.add_argument('-c', '--cuda', action='store_true', help='Loading cuda module')
    parser.add_argument('-x', '--doNotLaunchJobs', action='store_true', help='Create the QSUB files but dont launch them')
    parser.add_argument("commandAndOptions", help="Options for the command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    
    # Define the number of core by nodes for a specific cluster
    if args.nbCore != None:
        nbCoreByNode = int(args.nbCore)
    elif args.queue == 'qfat256@mp2' or  args.queue == 'qfat512@mp2':
        nbCoreByNode = 48
    else:
        nbCoreByNode = 24
    
    # list_commandAndOptions must be a list of lists
    list_commandAndOptions = []
    for opt in args.commandAndOptions:
        list_commandAndOptions += [opt.split()]
    
    # Creating the LOGS folder
    currentDir = os.getcwd()
    pathLogs = os.path.join(currentDir, 'LOGS_QSUB')
    if not os.path.exists(pathLogs):
        os.makedirs(pathLogs)
    
    # Creating the folder in 'LOGS_QSUB' where the info will be saved
    nameFolderSavingLogs = ''
    for argument in list_commandAndOptions:
        str_tmp = argument[0][-30:] + ('' if len(argument) == 1 else ('-' + argument[-1][-30:]))
        str_tmp = str_tmp.split('/')[-1] # Deal with path as parameter
        nameFolderSavingLogs += str_tmp if nameFolderSavingLogs == '' else ('__' + str_tmp)
    current_time = datetime.datetime.now()
    nameFolderSavingLogs = current_time.isoformat() + '___' + nameFolderSavingLogs[:227] #No more than 256 character
    subPathLogs = os.path.join(pathLogs, nameFolderSavingLogs)
    if not os.path.exists(subPathLogs):
        os.makedirs(subPathLogs)
    
    # Creating the folder where the QSUB files will be saved
    pathQsubFolder = os.path.join(subPathLogs, 'QSUB_commands')
    if not os.path.exists(pathQsubFolder):
        os.makedirs(pathQsubFolder)
    
    # Generate the list of jobs with all the possible combination of the given values
    list_jobs_str = ['#cd $SRC ;']
    list_jobsOutput_folderName = ['']
    for argument in list_commandAndOptions:
        list_jobs_tmp = []
        list_folderName_tmp = []
        for valueForArg in argument:
            for job_str, folderName in zip(list_jobs_str, list_jobsOutput_folderName):
                list_jobs_tmp += [job_str + ' ' + valueForArg]
                list_folderName_tmp += [valueForArg[-30:]] if folderName == '' else [folderName + '-' + valueForArg[-30:]]
        list_jobs_str = list_jobs_tmp
        list_jobsOutput_folderName = list_folderName_tmp
          
    # Distribute equally the jobs among the QSUB files and generate those files
    nbJobsTotal = len(list_jobs_str)
    nbQsubFiles = int(np.ceil(nbJobsTotal/float(nbCoreByNode)))
    nbJobPerFile =  int(np.ceil(nbJobsTotal/float(nbQsubFiles)))
    list_qsubFiles = []
    for i in range(nbQsubFiles):
        start = i*nbJobPerFile
        end = (i+1)*nbJobPerFile
        if end > nbJobsTotal:
            end = nbJobsTotal
        qsubFile = os.path.join(pathQsubFolder, 'jobCommands_' + str(i) + '.sh')
        writeQsubFile(list_jobs_str[start:end], list_jobsOutput_folderName[start:end], qsubFile, subPathLogs, args.queue, args.time, currentDir, args.cuda)
        list_qsubFiles += [qsubFile]

    # Launch the jobs with QSUB
    if not args.doNotLaunchJobs:
        for qsubFile in list_qsubFiles:
            check_output('qsub' + qsubFile, shell=True)


def writeQsubFile(list_jobs_str, list_jobsOutput_folderName, qsubFile, subPathLogs, queue, walltime, currentDir, useCuda):
    # Creating the file that will be launch by QSUB
    f = open(qsubFile, 'w')
    f.write('#!/bin/bash\n')
    f.write('#PBS -q ' + queue + '\n')
    f.write('#PBS -l nodes=1:ppn=1\n')
    f.write('#--Exporting environment variables from the submission shell to the job shell\n')
    f.write('#PBS -V\n')
    f.write('#PBS -l walltime=' + walltime + '\n')
    f.write('#module load cuda\n')
    f.write('#SRC=' + currentDir + '\n')
    f.write('\n\n\n')

    ## Example of a line for one job for QSUB
    #f.write('#cd $SRC ; python -u trainAutoEnc2.py 10 80 sigmoid 0.1 vocKL_sarath_german True True > trainAutoEnc2.py-10-80-sigmoid-0.1-vocKL_sarath_german-True-True &\n')

    for job, folderName in zip(list_jobs_str, list_jobsOutput_folderName):
        f.write(job + ' > ' + os.path.join(subPathLogs, folderName) + ' &\n')

    f.write('\n\n\n')
    f.write('#wait\n')
    f.close()

    



if __name__ == "__main__":
    main()
