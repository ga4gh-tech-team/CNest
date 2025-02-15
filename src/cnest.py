#!/usr/bin/env python3.8

"""Command-line interface for CNest
Author: Shimin Shuai (EMBL)
Contact: shimin.shuai@embl.de
Date: Jan 4, 2021
"""

import argparse
import os
import subprocess
import logging
import sys
import shutil

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s | %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S')
logger = logging.getLogger('CNest')


def get_args():
    parser = argparse.ArgumentParser(description='CNest wrapper')
    parser.add_argument('--debug', dest='debug', default=False,
                        action='store_true', help='Show debug messages')
    subparsers = parser.add_subparsers(help='Steps of CNest', dest='step')
    # step 1
    parser_1 = subparsers.add_parser('step1', help='Create project directory')
    parser_1.add_argument('--project', dest='project', required=True, type=str, help='Project name')
    parser_1.add_argument('--bed', dest='bed_file', required=True, type=str, help='Input sorted BED3 file name')
    # step 2
    parser_2 = subparsers.add_parser('step2', help='BAM/CRAM to binary')
    parser_2.add_argument('--project', dest='project', required=True, type=str, help='Poject name')
    parser_2.add_argument('--sample', dest='sample_id', required=True, type=str, help='Sample name')
    parser_2.add_argument('--input', dest='input_file', required=True, type=str, help='Input BAM/CRAM file name')
    parser_2.add_argument('--fast', dest='fast_mode', default=False,  action='store_true', help='Use fast mode')
    parser_2.add_argument('--fasta', dest='fasta_file',  default=False, help='Reference FASTA for fast mode')
    # step 3
    parser_3 = subparsers.add_parser('step3', help='Gender QC')
    parser_3.add_argument('--indextab', dest='index_tab', required=True, type=str, help='Index tab file from step1')
    parser_3.add_argument('--bindir', dest='bin_dir', required=True,  type=str, help='Directory for all bin files from step2')
    parser_3.add_argument('--qc', dest='qc_file', required=True, type=str, help='Gender QC file path [output]')
    parser_3.add_argument('--gender', dest='gender_file', required=True, type=str, help='Gender classification file path [output]')
    parser_3.add_argument('--cov', dest='cov_file', required=True, type=str, help='Coverage file path [output]')
    # step 4
    parser_4 = subparsers.add_parser('step4', help='Sample Correlation & Rbin generation')
    parser_4.add_argument('--indextab', dest='index_tab', required=True, type=str, help='Index tab file from step1')
    parser_4.add_argument('--bindir', dest='bin_dir', required=True, type=str, help='Directory for all bin files from step2')
    parser_4.add_argument('--cordir', dest='cor_dir', required=True,  type=str, help='Directory for cor file [output]')
    parser_4.add_argument('--logrdir', dest='logr_dir', required=True, type=str, help='Directory for logr file [output]')
    parser_4.add_argument('--rbindir', dest='rbin_dir', required=True, type=str, help='Directory for rbin file [output]')
    parser_4.add_argument('--gender', dest='gender_file', required=True, type=str, help='Gender classification file from step3')
    parser_4.add_argument('--sample', dest='sample_id', type=str, help='Sample name')
    parser_4.add_argument('--splix', dest='sample_ix', type=int, help='Sample index (alternative to --sample; deprecated)')
    parser_4.add_argument('--batch', dest='batch_size', required=True, type=int, help='Maximum number of samples used as references')
    parser_4.add_argument('--cor', dest='cor_cut', default="0.9", type=str, help='Minimum similarity measure for defining references')
    parser_4.add_argument('--skipem', dest='skip_em', default=False, action='store_true', help='Whether or not to use the EM algorithm during reference search')
    # step 5
    parser_5 = subparsers.add_parser('step5', help='HMM Call')
    parser_5.add_argument('--indextab', dest='index_tab', required=True, type=str, help='Index tab file from step1')
    parser_5.add_argument('--cnvdir', dest='cnv_dir', required=True, type=str, help='Directory for CNV files [output]')
    parser_5.add_argument('--cordir', dest='cor_dir', required=True, type=str, help='Directory for cor file from step4')
    parser_5.add_argument('--rbindir', dest='rbin_dir', required=True, type=str, help='Directory for rbin file from step4')
    parser_5.add_argument('--gender', dest='gender_file', type=str, help='Gender classification file from step3')
    parser_5.add_argument('--cov', dest='cov_file', type=str, help='Coverage file from step3')
    parser_5.add_argument('--sample', dest='sample_id', type=str, help='Sample name')
    parser_5.add_argument('--splix', dest='sample_ix', type=int, help='Sample index (alternative to --sample; deprecated)')
    parser_5.add_argument('--batch', dest='batch_size', type=int, help='Maximum number of samples used as references')
    parser_5.add_argument('--covc', dest='cov_cut', default=20, type=int, help='Minimum mean coverage of targets to include in HMM calls')
    parser_5.add_argument('--cor', dest='cor_cut', default="0.9", type=str, help='Minimum similarity measure for defining references')
    parser_5.add_argument('--skipem', dest='skip_em', default=False, action='store_true', help='Whether or not to use the EM algorithm during reference search')
    args = parser.parse_args()
    return args

def run_cmd(cmd):
    """ Run a bash command
    """
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as err:
        cmd_str = " ".join(err.cmd)
        logger.error(f'#{cmd_str}# failed with exit code {err.returncode}.\n{err.stderr}')
        sys.exit(1)


def step1(project, bed_path, debug):
    accepted_chr = [str(i) for i in range(1, 23)] + ['X', 'Y']
    # make project (sub-)directories if not existed
    dirs = [f'{project}', f'{project}/txt', f'{project}/bin', f'{project}/tmp']
    for mydir in dirs:
        if not os.path.exists(mydir):
            os.mkdir(mydir)
    # Three index files to be added in to the project directory
    index_bed_path = f'{project}/index.bed'
    index_path = f'{project}/index.txt'
    index_tmp_path = f'{project}/tmp/index_tab.txt'  # unsorted temp file
    with open(bed_path) as fin, open(index_bed_path, 'w') as fbed, open(index_path, 'w') as fix, open(index_tmp_path, 'w') as ftab:
        for line in fin:
            fbed.write(line)
            elements = line.split('\t')
            # index.txt uses the same chrom names as BED (BAM/CRAM)
            # index_tab.txt uses 1-22, 23 for X and 24 for Y
            chrom = elements[0].replace('chr', '')
            assert chrom in accepted_chr, f'Only autosomes and X/Y are allowed. Your chromosome is {chrom}'
            if chrom == 'X':
                chrom = '23'
            elif chrom == 'Y':
                chrom = '24'
            fix.write(f'{elements[0]}:{elements[1]}-{elements[2]}')
            ftab.write(f'{chrom}\t{elements[1]}\t{elements[2]}')
    # Sort the index_tab.txt
    index_tab_path = f'{project}/index_tab.txt'
    with open(index_tab_path, 'w') as ftab:
        cmd = ['sort', '-n', '-k1,1', '-k2,2', '-k3,3', index_tmp_path]
        logger.debug('CMD=' + " ".join(cmd))
        subprocess.run(cmd, stdout=ftab, check=True)
    # clean temp files
    if not debug:
        os.remove(index_tmp_path)
    logger.info('Step1 done!')


def step2(project_root, sample_id, input_file, debug):
    """
        project_root=/output_location/${project_name}
                echo $project_name $input_file_name $sample_id
                /software/applications/ngscnv/ngs ${project_root} bam-to-rd /input_location/$input_file_name $sample_id
                /software/applications/ngscnv/ngs ${project_root} rd-dump $sample_id > ${project_root}/txt/$sample_id
                Rscript /resources/run.R processtobin ${project_root} $sample_id
                rm ${project_root}/$sample_id
                rm ${project_root}/txt/$sample_id

        TODO:
        1. Add BAM/CRAM index file check [Done]
        2. Add chromosome name check
    """
    logger.info(f'Start step2 for sample {sample_id}')
    # Check bai or crai file
    if input_file.endswith(".bam"):
        assert os.path.exists(
            f"{input_file}.bai"), f"{input_file}.bai not found."
    elif input_file.endswith(".cram"):
        assert os.path.exists(
            f"{input_file}.crai"), f"{input_file}.crai not found."
    # Check chromosome name
    cmd1 = ['/software/applications/ngscnv/ngs',
            project_root, 'bam-to-rd', input_file, sample_id]
    cmd2 = ['/software/applications/ngscnv/ngs',
            project_root, 'rd-dump', sample_id]
    cmd3 = ['Rscript', '/resources/run.R',
            'processtobin', project_root, sample_id]
    logger.debug('CMD=' + " ".join(cmd1))
    process1 = subprocess.run(cmd1, capture_output=True)
    if process1.returncode == 0:
        logger.info('bam-to-rd done.')
        logger.debug('CMD=' + " ".join(cmd2))
        outpath = os.path.join(project_root, 'txt', sample_id)
        logger.debug('OUT=' + outpath)
        with open(outpath, 'w') as f:
            process2 = subprocess.run(cmd2, stdout=f)
    else:
        logger.error(
            f'bam-to-rd failed with exit code {process1.returncode}.\n{process1.stderr}')
    if process2.returncode == 0:
        logger.info('rd-dump done.')
        logger.debug('CMD=' + " ".join(cmd3))
        process3 = subprocess.run(cmd3, capture_output=True)
    else:
        logger.error(
            f'rd-dump failed with exit code {process2.returncode}.\n{process2.stderr}')
    if process3.returncode == 0:
        logger.info('processtobin done.')
    else:
        logger.error(
            f'processtobin failed with exit code {process3.returncode}.\n{process3.stderr}')
    # clean temp files
    if not debug:
        os.remove(os.path.join(project_root, sample_id))
        os.remove(os.path.join(project_root, 'txt', sample_id))
    logger.info('Step2 done!')


def step2_fast(project, sample_id, input_file, fasta_file, debug):
    accepted_chr = [str(i) for i in range(1, 23)] + ['X', 'Y']
    logger.info(f'Start step2-fast for sample {sample_id}')
    # Check bai or crai file
    if input_file.endswith(".bam"):
        assert os.path.exists(
            f"{input_file}.bai"), f"{input_file}.bai not found."
    elif input_file.endswith(".cram"):
        assert os.path.exists(
            f"{input_file}.crai"), f"{input_file}.crai not found."
    # Run hts_nim_tools to obtain read counts
    # Save the read count into temp file [chrom start end count depth extraCol1 extraCol2]
    cmd1 = ['hts_nim_tools', 'count-reads', '-f', fasta_file,
            '--threads', '1', '--mapq', '1', f'{project}/index.bed', input_file]
    logger.debug('CMD=' + " ".join(cmd1))
    process1 = subprocess.Popen(
        cmd1, stdout=subprocess.PIPE, bufsize=64, text=True)
    it1 = iter(process1.stdout.readline, '')
    tmp_path1 = f'{project}/tmp/{sample_id}.unsorted'
    with open(tmp_path1, 'w') as ftmp:
        for line in it1:
            elements = line.strip().split('\t')
            # Chromosome name no chr
            chrom = elements[0].replace('chr', '')
            assert chrom in accepted_chr, f'Only autosomes and X/Y are allowed. Your chromosome is {chrom}'
            if chrom == 'X':
                chrom = '23'
            elif chrom == 'Y':
                chrom = '24'
            ftmp.write(
                f'{chrom}\t{elements[1]}\t{elements[2]}\t{elements[3]}\t1\t1\t1\n')
    # Sort the temp file
    tmp_path2 = f'{project}/tmp/{sample_id}'
    with open(tmp_path2, 'w') as ftmp:
        cmd2 = ['sort', '-n', '-k1,1', '-k2,2', '-k3,3', tmp_path1]
        logger.debug('CMD=' + " ".join(cmd2))
        subprocess.run(cmd2, stdout=ftmp, check=True)
    # Convert table to binary with Rbin
    cmd3 = ['Rscript', '/resources/run.R',
            'processtobin_fast', project, sample_id]
    logger.debug('CMD=' + " ".join(cmd3))
    run_cmd(cmd3)
    # clean temp files
    if not debug:
        os.remove(tmp_path1)
        os.remove(tmp_path2)
    logger.info('Step2-fast done')


def step3(bin_dir, index_tab, qc_file, gender_file, cov_file):
    """Gender QC & Coverage Generation

        # Original code
        project_root=/output_location/${project_name}
        index_file=${project_root}/index_tab.txt
        qc_file=${project_root}/gender_qc.txt
        gender_file=${project_root}/gender_classification.txt
        Rscript /resources/run.R classify_gender ${project_root} ${index_file} ${qc_file} ${gender_file}

    Note:
        # Current code
        Rscript /resources/run.R classify_gender ${bin_dir} ${index_tab} ${qc_file} ${gender_file}
        Rscript /resources/run.R generate_coverage ${bin_dir} ${index_tab} ${cov_file}
    """
    logger.info('Starting step3')
    # Classify gender
    cmd3_1 = ['Rscript', '/resources/run.R', 'classify_gender',
           bin_dir, index_tab, qc_file, gender_file]
    logger.debug('CMD | ' + " ".join(cmd3_1))
    run_cmd(cmd3_1)
    logger.info('classify_gender done')
    # generate_coverage
    cmd3_2 = ['Rscript', '/resources/run.R', 'generate_coverage',
           bin_dir, index_tab, cov_file]
    logger.debug('CMD | ' + " ".join(cmd3_2))
    run_cmd(cmd3_2)
    logger.info('generate_coverage done')
    logger.info('Step3 done')


def step4(bin_dir, cor_dir, logr_dir, rbin_dir, sample_name, index_tab, gender_file, batch_size, cor_cut, skip_em, debug):
    """Sample correlation
        project_root=/output_location/${project_name}
        index_file=${project_root}/index_tab.txt
        # Step4
        Rscript /resources/run.R generate_correlation ${project_root} ${sample_index} ${index_file}
        # Step5
        Rscript /resources/run.R get_references ${project_root} ${sample_index} ${index_file} ${gender_file} ${batch_size}
        # Step6
        Rscript /resources/run.R processLogRtoBin ${project_root} ${sample_index}

    Note:
        The orginial function uses a [sample_index]. Here, we change this and use [sample_name] instead.
        ## updated version
        # Step 4
        Rscript /resources/run.R generate_correlation ${bin_dir} ${cor_dir} ${sample_name} ${index_tab}
        # Step 5
        Rscript /resources/run.R get_references ${bin_dir} ${cor_dir} ${logr_dir} ${sample_name} ${index_file} ${gender_file} ${batch_size}
        # Step 6
        Rscript /resources/run.R processLogRtoBin ${logr_dir} ${rbin_dir} ${sample_name}
    """
    logger.info('Start step4')
    # Original Step4 - generate_correlation
    cmd4 = ['Rscript', '/resources/run.R', 'generate_correlation',
            bin_dir, cor_dir, sample_name, index_tab]
    logger.debug('CMD=' + " ".join(cmd4))
    run_cmd(cmd4)
    logger.info('generate_correlation done')
    # Original Step5 - get_references
    cmd5 = ['Rscript', '/resources/run.R', 'get_references', bin_dir,
            cor_dir, logr_dir, sample_name, index_tab, gender_file, str(batch_size), str(cor_cut), str(skip_em)]
    logger.debug('CMD=' + " ".join(cmd5))
    run_cmd(cmd5)
    logger.info('get_references done')
    # Original Step6 - processLogRtoBin
    cmd6 = ['Rscript', '/resources/run.R',
            'processLogRtoBin', logr_dir, rbin_dir, sample_name]
    logger.debug('CMD=' + " ".join(cmd6))
    run_cmd(cmd6)
    logger.info('processLogRtoBin done')
    # Clean
    if not debug:
        os.remove(f"{rbin_dir}/{sample_name}.tmp")
    logger.info('Step4 done')


def step5(rbin_dir, cor_dir, cnv_dir, sample_name, index_tab, cov_file, gender_file, batch_size, cov_cut, cor_cut, skip_em, debug):
    """HMM Call
        # Original Step7
        Rscript /resources/run.R run_hmm_rbin ${project_root} ${sample_index} \
            ${index_file} ${cov_file} ${gender_file} ${output_path} ${batch_size}
        # R function
        run_hmm_rbin(rbin_dir, sample_name, index_file, cov_file, cor_dir, gender_file, outpath, batch_size)

    Note:
        The orginial function uses a [sample_index]. Here, we change this and use [sample_name] instead.
        ## updated version
        Rscript /resources/run.R run_hmm_rbin ${rbin_dir} ${cor_dir} ${cnv_dir} ${sample_name} \
            ${index_tab} ${cov_file} ${gender_file} ${batch_size}
    """
    logger.info('Start step5')
    cmd7 = ['Rscript', '/resources/run.R',
            'run_hmm_rbin', rbin_dir, cor_dir, cnv_dir, sample_name, index_tab,
            cov_file, gender_file, str(batch_size), str(cov_cut), str(cor_cut), str(skip_em)]
    print(cmd7)
    logger.debug('CMD | ' + " ".join(cmd7))
    run_cmd(cmd7)
    logger.info('Step5 done')


def ix2id(sample_index, gender_file):
    """Convert an integer to a sample name based on the gender file.
    """
    with open(gender_file) as f:
        for i, line in enumerate(f):
            if i == sample_index:
                return(line.split('\t')[0])


if __name__ == '__main__':
    args = get_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    if args.step == 'step1':
        # step 1
        step1(args.project, args.bed_file, args.debug)
    elif args.step == 'step2':
        # step 2
        if args.fast_mode:
            step2_fast(args.project, args.sample_id,
                       args.input_file, args.fasta_file, args.debug)
        else:
            step2(args.project, args.sample_id, args.input_file, args.debug)
    elif args.step == 'step3':
        # step 3
        step3(args.bin_dir, args.index_tab, args.qc_file, args.gender_file, args.cov_file)
    elif args.step == 'step4':
        # step 4
        sample_id = ix2id(
            args.sample_ix, args.gender_file) if args.sample_ix else args.sample_id
        step4(args.bin_dir, args.cor_dir, args.logr_dir, args.rbin_dir, sample_id,
              args.index_tab, args.gender_file, args.batch_size, args.cor_cut, args.skip_em, args.debug)
    elif args.step == 'step5':
        # step 5
        sample_id = ix2id(
            args.sample_ix, args.gender_file) if args.sample_ix else args.sample_id
        step5(args.rbin_dir, args.cor_dir, args.cnv_dir, sample_id,
              args.index_tab, args.cov_file, args.gender_file, args.batch_size, args.cov_cut, args.cor_cut, args.skip_em, args.debug)
